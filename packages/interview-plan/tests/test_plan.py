"""Regression tests for governed, candidate-neutral structured-interview plans."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone, tzinfo
from hashlib import sha256
import json
import pytest

from orgmetra_interview_plan import StructuredInterviewPlan, build_structured_interview_plan

TENANT = "12345678-1234-4234-8234-123456789abc"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
INTERVIEW_PLAN = "interview_plan:11111111-1111-4111-8111-111111111111"
REQUISITION = "requisition:22222222-2222-4222-8222-222222222222"
JOB_PROFILE = "job_profile:33333333-3333-4333-8333-333333333333"
JOB_ANALYSIS = "job_analysis:44444444-4444-4444-8444-444444444444"
QUESTION_SET = "question_set:55555555-5555-4555-8555-555555555555"
QUESTION_MAP = "question_competency_map:66666666-6666-4666-8666-666666666666"
RATING_ANCHOR = "rating_anchor:77777777-7777-4777-8777-777777777777"
COMPETENCY_A = "competency:88888888-8888-4888-8888-888888888888"
COMPETENCY_B = "competency:99999999-9999-4999-8999-999999999999"
COMPETENCY_C = "competency:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
PANEL_A = "actor:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
PANEL_B = "actor:cccccccc-cccc-4ccc-8ccc-cccccccccccc"


def values():
    """Return one valid plan input mapping for focused mutation-based regressions."""
    return dict(
        tenant_record_id=TENANT,
        interview_plan_reference=INTERVIEW_PLAN,
        requisition_reference=REQUISITION,
        job_profile_reference=JOB_PROFILE,
        job_analysis_reference=JOB_ANALYSIS,
        job_analysis_digest=DIGEST_A,
        question_set_reference=QUESTION_SET,
        question_set_digest=DIGEST_B,
        question_competency_map_reference=QUESTION_MAP,
        question_competency_map_digest=DIGEST_D,
        rating_anchor_reference=RATING_ANCHOR,
        rating_anchor_digest=DIGEST_C,
        competency_references=(COMPETENCY_A, COMPETENCY_B),
        panel_actor_references=(PANEL_A, PANEL_B),
        question_count=4,
        purpose_code="structured_interview_plan",
        reason_code="approved_requisition_interview",
        generated_at=datetime(2026, 8, 18, 12, 34, 56, 123456, tzinfo=timezone.utc),
    )


def test_builds_candidate_neutral_deterministic_plan():
    """Build deterministic evidence without candidate values or autonomous authority."""
    plan = build_structured_interview_plan(**values())
    payload = json.loads(plan.canonical_json())
    assert payload["review_state"] == "requires_human_approval"
    assert payload["human_confirmation_required"] is True
    assert payload["generated_at"].endswith(".123456Z")
    assert payload["question_competency_map_reference"] == QUESTION_MAP
    assert "candidate" not in plan.canonical_json()
    assert plan.sha256_digest() == sha256(plan.canonical_json().encode("utf-8")).hexdigest()
    assert plan == StructuredInterviewPlan(**values())


@pytest.mark.parametrize("field,bad", [
    ("tenant_record_id", "not-a-uuid"),
    ("tenant_record_id", "00000000-0000-0000-0000-000000000000"),
    ("tenant_record_id", "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF"),
    ("interview_plan_reference", "wrong:si-1"),
    ("requisition_reference", "wrong:req-1"),
    ("job_profile_reference", "wrong:job-1"),
    ("job_analysis_reference", "wrong:analysis-1"),
    ("question_set_reference", "wrong:q-1"),
    ("question_competency_map_reference", "wrong:map-1"),
    ("rating_anchor_reference", "wrong:a-1"),
    ("interview_plan_reference", "interview_plan:00000000-0000-0000-0000-000000000000"),
    ("job_profile_reference", "job_profile:FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF"),
    ("rating_anchor_reference", 7),
    ("job_analysis_digest", "A" * 64),
    ("question_set_digest", "b" * 63),
    ("question_competency_map_digest", "D" * 64),
    ("rating_anchor_digest", 7),
    ("purpose_code", "wrong_purpose"),
    ("purpose_code", "bad"),
    ("reason_code", "Bad Reason"),
    ("reason_code", "a_" + "b" * 64),
    ("generated_at", datetime(2026, 8, 18, 1, 2, 3)),
    ("human_confirmation_required", False),
    ("human_confirmation_required", 1),
    ("review_state", "approved"),
    ("next_action", "Skip human review"),
])
def test_rejects_invalid_scalar_contract(field, bad):
    """Reject malformed scalar identity, digest, governance, time, and state inputs."""
    data = values()
    data[field] = bad
    with pytest.raises((ValueError, TypeError)):
        StructuredInterviewPlan(**data)


@pytest.mark.parametrize("refs", [(), tuple(f"competency:c{i}" for i in range(13)), [COMPETENCY_A]])
def test_rejects_bad_competency_collection_shape(refs):
    """Require competencies to use the governed bounded tuple collection shape."""
    data = values()
    data["competency_references"] = refs
    with pytest.raises(ValueError, match="competency_references"):
        StructuredInterviewPlan(**data)


@pytest.mark.parametrize("refs", [
    (COMPETENCY_B, COMPETENCY_A),
    (COMPETENCY_A, COMPETENCY_A),
    ("wrong:analysis",),
    ("competency:Jane-Doe",),
])
def test_rejects_noncanonical_competencies(refs):
    """Reject unsorted, duplicate, wrong-namespace, or value-bearing competencies."""
    data = values()
    data["competency_references"] = refs
    with pytest.raises(ValueError):
        StructuredInterviewPlan(**data)


@pytest.mark.parametrize("refs", [
    (PANEL_A,),
    tuple(f"actor:p{i}" for i in range(9)),
    [PANEL_A, PANEL_B],
    (PANEL_B, PANEL_A),
    (PANEL_A, PANEL_A),
    ("wrong:a", PANEL_B),
    (PANEL_A, "actor:seonghobae"),
])
def test_rejects_bad_panel_contract(refs):
    """Require a sorted unique bounded panel of opaque accountable actor references."""
    data = values()
    data["panel_actor_references"] = refs
    with pytest.raises(ValueError, match="panel_actor_references|actor"):
        StructuredInterviewPlan(**data)


@pytest.mark.parametrize("count", [True, 0, 21, 1])
def test_rejects_bad_question_count(count):
    """Reject boolean, out-of-range, or competency-underflow question counts."""
    data = values()
    data["question_count"] = count
    with pytest.raises(ValueError, match="question_count"):
        StructuredInterviewPlan(**data)


def test_question_count_error_describes_only_the_cardinality_constraint():
    """Keep the count failure message limited to cardinality rather than coverage claims."""
    data = values()
    data["competency_references"] = (COMPETENCY_A, COMPETENCY_B, COMPETENCY_C)
    data["question_count"] = 2
    with pytest.raises(
        ValueError,
        match="question_count must be at least the number of governed competencies",
    ):
        StructuredInterviewPlan(**data)


def test_accepts_question_count_equal_to_competency_count():
    """Accept the smallest count consistent with the governed competency cardinality."""
    data = values()
    data["question_count"] = 2
    assert StructuredInterviewPlan(**data).question_count == 2


class UnknownOffset(tzinfo):
    """Timezone fixture whose UTC offset is intentionally unknowable."""

    def utcoffset(self, dt):
        """Return no UTC offset so timestamp validation must fail closed."""
        return None

    def dst(self, dt):
        """Return no daylight-saving offset for this deliberately invalid fixture."""
        return None


def test_rejects_timezone_with_unknown_offset():
    """Reject tzinfo objects that cannot resolve an actual UTC offset."""
    data = values()
    data["generated_at"] = datetime(2026, 8, 18, tzinfo=UnknownOffset())
    with pytest.raises(ValueError, match="timezone-aware"):
        StructuredInterviewPlan(**data)


def test_canonicalizes_non_utc_offset_and_preserves_fractional_precision():
    """Normalize valid offsets to UTC without collapsing fractional-second evidence."""
    data = values()
    data["generated_at"] = datetime(
        2026, 8, 18, 21, 34, 56, 123456, tzinfo=timezone(timedelta(hours=9))
    )
    payload = json.loads(StructuredInterviewPlan(**data).canonical_json())
    assert payload["generated_at"] == "2026-08-18T12:34:56.123456Z"


def test_direct_replace_is_revalidated():
    """Re-run all fail-closed invariants when immutable plans are copied with changes."""
    plan = StructuredInterviewPlan(**values())
    with pytest.raises(ValueError, match="question_set_digest"):
        replace(plan, question_set_digest="not-a-digest")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("interview_plan_reference", "interview_plan:Jane-Doe"),
        ("requisition_reference", "requisition:customer-42"),
        ("job_profile_reference", "job_profile:RN-ICU"),
        ("job_analysis_reference", "job_analysis:salary-120000"),
        ("question_set_reference", "question_set:executive-candidates"),
        ("question_competency_map_reference", "question_competency_map:race-gender"),
        ("rating_anchor_reference", "rating_anchor:top-secret"),
    ],
)
def test_scalar_trust_references_reject_value_bearing_non_uuid_suffixes(field, value):
    """Reject semantic or value-bearing scalar trust references before serialization."""
    data = values()
    data[field] = value
    with pytest.raises(ValueError):
        StructuredInterviewPlan(**data)


def test_collection_trust_references_reject_value_bearing_non_uuid_suffixes():
    """Apply opaque-reference requirements to competency and panel collections."""
    for field, refs in (
        ("competency_references", (COMPETENCY_A, "competency:Jane-Doe")),
        ("panel_actor_references", (PANEL_A, "actor:seonghobae")),
    ):
        data = values()
        data[field] = refs
        with pytest.raises(ValueError):
            StructuredInterviewPlan(**data)


@pytest.mark.parametrize("reason", ["jane_doe", "salary_120000", "race_gender_review"])
def test_reason_code_rejects_personal_or_value_bearing_free_form_codes(reason):
    """Keep interview-plan reason metadata on a reviewed value-free vocabulary."""
    data = values()
    data["reason_code"] = reason
    with pytest.raises(ValueError):
        StructuredInterviewPlan(**data)


def test_repr_redacts_interview_plan_correlations():
    """Prevent routine logging from exposing governance references or evidence digests."""
    plan = StructuredInterviewPlan(**values())
    rendered = repr(plan)
    assert rendered == "StructuredInterviewPlan(<redacted>)"
    for sensitive in (
        plan.interview_plan_reference,
        plan.job_profile_reference,
        plan.panel_actor_references[0],
        plan.job_analysis_digest,
    ):
        assert sensitive not in rendered


def test_replace_cannot_reintroduce_value_bearing_metadata():
    """Preserve the privacy boundary under dataclass replacement."""
    plan = StructuredInterviewPlan(**values())
    for field, value in (
        ("job_profile_reference", "job_profile:RN-ICU"),
        ("reason_code", "salary_120000"),
    ):
        with pytest.raises(ValueError):
            replace(plan, **{field: value})
