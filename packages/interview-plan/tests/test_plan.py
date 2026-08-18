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


def values():
    return dict(
        tenant_record_id=TENANT,
        interview_plan_reference="interview_plan:si-2026-001",
        requisition_reference="requisition:req-2026-001",
        job_profile_reference="job_profile:job-001",
        job_analysis_reference="job_analysis:analysis-001",
        job_analysis_digest=DIGEST_A,
        question_set_reference="question_set:questions-v1",
        question_set_digest=DIGEST_B,
        question_competency_map_reference="question_competency_map:map-v1",
        question_competency_map_digest=DIGEST_D,
        rating_anchor_reference="rating_anchor:anchors-v1",
        rating_anchor_digest=DIGEST_C,
        competency_references=("competency:analysis", "competency:communication"),
        panel_actor_references=("actor:interviewer-a", "actor:interviewer-b"),
        question_count=4,
        purpose_code="structured_interview_plan",
        reason_code="approved_requisition_interview",
        generated_at=datetime(2026, 8, 18, 12, 34, 56, 123456, tzinfo=timezone.utc),
    )


def test_builds_candidate_neutral_deterministic_plan():
    plan = build_structured_interview_plan(**values())
    payload = json.loads(plan.canonical_json())
    assert payload["review_state"] == "requires_human_approval"
    assert payload["human_confirmation_required"] is True
    assert payload["generated_at"].endswith(".123456Z")
    assert payload["question_competency_map_reference"] == "question_competency_map:map-v1"
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
    data = values()
    data[field] = bad
    with pytest.raises((ValueError, TypeError)):
        StructuredInterviewPlan(**data)


@pytest.mark.parametrize("refs", [(), tuple(f"competency:c{i}" for i in range(13)), ["competency:a"]])
def test_rejects_bad_competency_collection_shape(refs):
    data = values()
    data["competency_references"] = refs
    with pytest.raises(ValueError, match="competency_references"):
        StructuredInterviewPlan(**data)


@pytest.mark.parametrize("refs", [
    ("competency:communication", "competency:analysis"),
    ("competency:analysis", "competency:analysis"),
    ("wrong:analysis",),
])
def test_rejects_noncanonical_competencies(refs):
    data = values()
    data["competency_references"] = refs
    with pytest.raises(ValueError):
        StructuredInterviewPlan(**data)


@pytest.mark.parametrize("refs", [
    ("actor:only-one",),
    tuple(f"actor:p{i}" for i in range(9)),
    ["actor:a", "actor:b"],
    ("actor:b", "actor:a"),
    ("actor:a", "actor:a"),
    ("wrong:a", "actor:b"),
])
def test_rejects_bad_panel_contract(refs):
    data = values()
    data["panel_actor_references"] = refs
    with pytest.raises(ValueError, match="panel_actor_references|actor"):
        StructuredInterviewPlan(**data)


@pytest.mark.parametrize("count", [True, 0, 21, 1])
def test_rejects_bad_question_count(count):
    data = values()
    data["question_count"] = count
    with pytest.raises(ValueError, match="question_count"):
        StructuredInterviewPlan(**data)


def test_question_count_error_describes_only_the_cardinality_constraint():
    data = values()
    data["competency_references"] = (
        "competency:analysis",
        "competency:communication",
        "competency:judgment",
    )
    data["question_count"] = 2
    with pytest.raises(
        ValueError,
        match="question_count must be at least the number of governed competencies",
    ):
        StructuredInterviewPlan(**data)


def test_accepts_question_count_equal_to_competency_count():
    data = values()
    data["question_count"] = 2
    assert StructuredInterviewPlan(**data).question_count == 2


class UnknownOffset(tzinfo):
    def utcoffset(self, dt):
        return None

    def dst(self, dt):
        return None


def test_rejects_timezone_with_unknown_offset():
    data = values()
    data["generated_at"] = datetime(2026, 8, 18, tzinfo=UnknownOffset())
    with pytest.raises(ValueError, match="timezone-aware"):
        StructuredInterviewPlan(**data)


def test_canonicalizes_non_utc_offset_and_preserves_fractional_precision():
    data = values()
    data["generated_at"] = datetime(
        2026, 8, 18, 21, 34, 56, 123456, tzinfo=timezone(timedelta(hours=9))
    )
    payload = json.loads(StructuredInterviewPlan(**data).canonical_json())
    assert payload["generated_at"] == "2026-08-18T12:34:56.123456Z"


def test_direct_replace_is_revalidated():
    plan = StructuredInterviewPlan(**values())
    with pytest.raises(ValueError, match="question_set_digest"):
        replace(plan, question_set_digest="not-a-digest")
