from dataclasses import replace
from datetime import datetime, tzinfo
from hashlib import sha256
import json

import pytest

from orgmetra_requisition_review import build_requisition_review_packet

TENANT = "2b37b937-c3f1-49aa-8d19-785a7b7a9917"
DIGEST = "0" * 64
NOW = datetime.fromisoformat("2026-08-18T10:30:00+00:00")
REQUISITION = "requisition:11111111-1111-4111-8111-111111111111"
JOB = "job_profile:22222222-2222-4222-8222-222222222222"
JOB_REQUIREMENTS = "job_requirements:33333333-3333-4333-8333-333333333333"
HEADCOUNT = "headcount_authorization:44444444-4444-4444-8444-444444444444"
HIRING_MANAGER = "actor:55555555-5555-4555-8555-555555555555"
APPROVER = "actor:66666666-6666-4666-8666-666666666666"
POSITION = "position_record:77777777-7777-4777-8777-777777777777"


def packet(**overrides):
    values = dict(
        tenant_record_id=TENANT,
        requisition_reference=REQUISITION,
        job_profile_reference=JOB,
        job_requirements_reference=JOB_REQUIREMENTS,
        job_requirements_digest=DIGEST,
        requirements_version_code="requirements_version_1",
        headcount_authorization_reference=HEADCOUNT,
        hiring_manager_actor_reference=HIRING_MANAGER,
        approver_actor_reference=APPROVER,
        requested_opening_count=3,
        purpose_code="requisition_review",
        reason_code="approved_growth_plan",
        generated_at=NOW,
    )
    values.update(overrides)
    return build_requisition_review_packet(**values)


def test_packet_is_deterministic_and_contains_no_candidate_or_employee_values():
    value = packet()
    payload = json.loads(value.canonical_json())
    assert payload["human_confirmation_required"] is True
    assert payload["review_state"] == "requires_human_approval"
    assert payload["generated_at"] == "2026-08-18T10:30:00Z"
    assert payload["requested_opening_count"] == 3
    assert payload["position_record_reference"] is None
    assert not ({"candidate", "person", "email", "name"} & set(payload))
    assert value.sha256_digest() == sha256(value.canonical_json().encode("utf-8")).hexdigest()


def test_exact_position_seat_supports_one_opening():
    value = packet(requested_opening_count=1, position_record_reference=POSITION)
    assert value.position_record_reference == POSITION


@pytest.mark.parametrize(
    "tenant",
    [
        "not-a-uuid",
        "00000000-0000-0000-0000-000000000000",
        "ffffffff-ffff-ffff-ffff-ffffffffffff",
        "2B37B937-C3F1-49AA-8D19-785A7B7A9917",
        123,
    ],
)
def test_tenant_must_be_canonical_operational_uuid(tenant):
    with pytest.raises(ValueError):
        packet(tenant_record_id=tenant)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("requisition_reference", "requisition:"),
        ("requisition_reference", "candidate_profile:wrong"),
        ("job_profile_reference", "job:wrong"),
        ("job_requirements_reference", "job_analysis:wrong"),
        ("headcount_authorization_reference", "budget:wrong"),
        ("hiring_manager_actor_reference", "user:manager"),
        ("approver_actor_reference", "reviewer:approver"),
        ("requisition_reference", "requisition:" + "a" * 150),
        ("requisition_reference", "requisition:00000000-0000-0000-0000-000000000000"),
        ("job_profile_reference", "job_profile:FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF"),
        ("approver_actor_reference", 123),
    ],
)
def test_references_are_bounded_namespaced_canonical_operational_uuids(field, value):
    with pytest.raises(ValueError):
        packet(**{field: value})


def test_position_reference_is_optional_but_must_be_namespaced_when_present():
    with pytest.raises(ValueError):
        packet(requested_opening_count=1, position_record_reference="position:seat-01")


@pytest.mark.parametrize("opening_count", [True, False, 0, 101, 1.0, "1"])
def test_opening_count_is_bounded_exact_integer(opening_count):
    with pytest.raises(ValueError):
        packet(requested_opening_count=opening_count)


def test_exact_position_cannot_claim_multiple_openings():
    with pytest.raises(ValueError, match="exactly one opening"):
        packet(position_record_reference=POSITION, requested_opening_count=2)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("purpose_code", "requisition"),
        ("purpose_code", "Requisition_Review"),
        ("reason_code", "growth"),
        ("reason_code", "approved growth plan"),
        ("requirements_version_code", "v1"),
        ("requirements_version_code", 1),
        ("reason_code", "approved_" + "a" * 64),
    ],
)
def test_governance_codes_require_bounded_governed_forms(field, value):
    with pytest.raises(ValueError):
        packet(**{field: value})


def test_packet_purpose_is_fixed_to_requisition_review():
    with pytest.raises(ValueError):
        packet(purpose_code="selection_review")


@pytest.mark.parametrize("digest", ["A" * 64, "0" * 63, "z" * 64, 123])
def test_requirements_digest_must_be_lowercase_sha256(digest):
    with pytest.raises(ValueError):
        packet(job_requirements_digest=digest)


class UnknownOffset(tzinfo):
    def utcoffset(self, dt):
        return None

    def dst(self, dt):
        return None


@pytest.mark.parametrize(
    "generated_at",
    [
        datetime(2026, 8, 18, 10, 30),
        datetime(2026, 8, 18, 10, 30, tzinfo=UnknownOffset()),
        "2026-08-18T10:30:00Z",
    ],
)
def test_generated_at_requires_real_timezone_offset(generated_at):
    with pytest.raises(ValueError):
        packet(generated_at=generated_at)


def test_non_utc_input_is_canonicalized_to_utc():
    value = packet(generated_at=datetime.fromisoformat("2026-08-18T19:30:00+09:00"))
    assert json.loads(value.canonical_json())["generated_at"] == "2026-08-18T10:30:00Z"


def test_fractional_seconds_are_preserved_in_canonical_evidence():
    first = packet(generated_at=datetime.fromisoformat("2026-08-18T19:30:00.123456+09:00"))
    second = packet(generated_at=datetime.fromisoformat("2026-08-18T19:30:00.123457+09:00"))

    assert json.loads(first.canonical_json())["generated_at"] == "2026-08-18T10:30:00.123456Z"
    assert json.loads(second.canonical_json())["generated_at"] == "2026-08-18T10:30:00.123457Z"
    assert first.canonical_json() != second.canonical_json()
    assert first.sha256_digest() != second.sha256_digest()


def test_hiring_manager_and_approver_require_authoritative_separation():
    with pytest.raises(ValueError, match="hiring manager and approver"):
        packet(approver_actor_reference=HIRING_MANAGER)

    normalized_next_action = packet().next_action.lower()
    assert "hiring_manager_actor_reference and approver_actor_reference" in normalized_next_action
    assert "resolved actor identities are distinct" in normalized_next_action


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("human_confirmation_required", False),
        ("human_confirmation_required", 1),
        ("review_state", "approved"),
        ("next_action", "Open the requisition automatically."),
    ],
)
def test_direct_constructor_cannot_bypass_human_approval(field, value):
    base = packet()
    with pytest.raises(ValueError):
        replace(base, **{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("requisition_reference", "requisition:Jane-Doe"),
        ("job_profile_reference", "job_profile:RN-ICU"),
        ("job_requirements_reference", "job_requirements:salary-120000"),
        ("headcount_authorization_reference", "headcount_authorization:finance-budget"),
        ("hiring_manager_actor_reference", "actor:seonghobae"),
        ("approver_actor_reference", "actor:jane_doe"),
        ("position_record_reference", "position_record:seat-01"),
    ],
)
def test_trust_references_reject_value_bearing_non_uuid_suffixes(field, value):
    """Prevent portable governance evidence from accepting human-readable trust references."""
    overrides = {field: value}
    if field == "position_record_reference":
        overrides["requested_opening_count"] = 1
    with pytest.raises(ValueError):
        packet(**overrides)


@pytest.mark.parametrize("reason_code", ["jane_doe", "salary_120000", "manager_seonghobae"])
def test_reason_code_rejects_personal_or_value_bearing_free_form_codes(reason_code):
    """Keep reason metadata on a reviewed value-free vocabulary."""
    with pytest.raises(ValueError):
        packet(reason_code=reason_code)


def test_requirements_version_rejects_semantic_or_personal_text():
    """Keep requirements version metadata numeric and non-semantic."""
    with pytest.raises(ValueError):
        packet(requirements_version_code="requirements_version_jane_doe")


def test_dataclass_replacement_cannot_reintroduce_value_bearing_metadata():
    """Apply the same privacy invariants to direct dataclass replacement paths."""
    base = packet()
    for field, value in (
        ("job_profile_reference", "job_profile:RN-ICU"),
        ("reason_code", "salary_120000"),
        ("requirements_version_code", "requirements_version_jane_doe"),
    ):
        with pytest.raises(ValueError):
            replace(base, **{field: value})


def test_repr_redacts_correlating_governance_metadata():
    """Prevent routine logging or assertion output from exposing sensitive correlations."""
    value = packet()
    rendered = repr(value)
    assert rendered == "RequisitionReviewPacket(<redacted>)"
    for sensitive in (
        value.requisition_reference,
        value.job_profile_reference,
        value.hiring_manager_actor_reference,
        value.approver_actor_reference,
        value.job_requirements_digest,
    ):
        assert sensitive not in rendered
