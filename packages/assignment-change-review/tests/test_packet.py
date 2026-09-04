from dataclasses import replace
from datetime import date, datetime, timedelta, timezone, tzinfo
from hashlib import sha256
import json

import pytest

from orgmetra_assignment_change_review import (
    AssignmentChangeReviewPacket,
    build_assignment_change_review_packet,
)

TENANT = "11111111-1111-4111-8111-111111111111"
REVIEW = "assignment_change_review:22222222-2222-4222-8222-222222222222"
PERSON = "person_record:33333333-3333-4333-8333-333333333333"
EMPLOYMENT = "employment_record:44444444-4444-4444-8444-444444444444"
CURRENT_ASSIGNMENT = "assignment_record:55555555-5555-4555-8555-555555555555"
CURRENT_JOB = "job_profile:66666666-6666-4666-8666-666666666666"
CURRENT_POSITION = "position_record:77777777-7777-4777-8777-777777777777"
PROPOSED_JOB = "job_profile:88888888-8888-4888-8888-888888888888"
PROPOSED_POSITION = "position_record:99999999-9999-4999-8999-999999999999"
SCOPE_SNAPSHOT = "assignment_scope_snapshot:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
ALLOCATION_PLAN = "workforce_allocation_plan:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
ALLOCATION_POLICY = "workforce_allocation_policy:abababab-abab-4bab-8bab-abababababab"
WORKER_IMPACT = "worker_impact_assessment:cccccccc-cccc-4ccc-8ccc-cccccccccccc"
COMMUNICATION_PLAN = "assignment_communication_plan:dddddddd-dddd-4ddd-8ddd-dddddddddddd"
REQUESTER = "actor:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
REVIEWER = "actor:ffffffff-ffff-4fff-8fff-fffffffffff0"
UUID1_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
DIGEST_E = "e" * 64
GENERATED_AT = datetime(2026, 8, 19, 6, 30, 15, 123456, tzinfo=timezone.utc)


class UnknownOffsetTimezone(tzinfo):
    def utcoffset(self, dt: datetime | None) -> None:
        return None

    def dst(self, dt: datetime | None) -> None:
        return None


def build_valid(**overrides: object) -> AssignmentChangeReviewPacket:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "assignment_change_review_reference": REVIEW,
        "person_record_reference": PERSON,
        "employment_record_reference": EMPLOYMENT,
        "current_assignment_reference": CURRENT_ASSIGNMENT,
        "current_job_profile_reference": CURRENT_JOB,
        "current_position_record_reference": CURRENT_POSITION,
        "proposed_job_profile_reference": PROPOSED_JOB,
        "proposed_position_record_reference": PROPOSED_POSITION,
        "current_scope_snapshot_reference": SCOPE_SNAPSHOT,
        "current_scope_snapshot_digest": DIGEST_A,
        "allocation_plan_reference": ALLOCATION_PLAN,
        "allocation_plan_digest": DIGEST_B,
        "allocation_policy_reference": ALLOCATION_POLICY,
        "allocation_policy_digest": DIGEST_C,
        "worker_impact_assessment_reference": WORKER_IMPACT,
        "worker_impact_assessment_digest": DIGEST_D,
        "communication_plan_reference": COMMUNICATION_PLAN,
        "communication_plan_digest": DIGEST_E,
        "requester_reference": REQUESTER,
        "reviewer_reference": REVIEWER,
        "purpose_code": "assignment_change_review",
        "reason_code": "workforce_reallocation",
        "requested_effective_on": date(2026, 9, 1),
        "generated_at": GENERATED_AT,
    }
    values.update(overrides)
    return build_assignment_change_review_packet(**values)


def test_builds_value_free_pre_mutation_review_packet() -> None:
    packet = build_valid()
    assert packet.contains_person_pii is False
    assert packet.contains_compensation_values is False
    assert packet.contains_free_form_model_output is False
    assert packet.human_confirmation_required is True
    assert packet.decision_authority == "human_review_only"
    assert packet.review_state == "requires_human_review"
    assert packet.scope_verification_state == "requires_authoritative_resolution"
    assert packet.mutation_state == "not_authorized_to_apply"
    assert "authoritative People mutation boundary" in packet.next_action


def test_next_action_requires_tenant_scoped_worker_binding_resolution() -> None:
    next_action = build_valid().next_action
    assert "re-resolve every packet reference within tenant_record_id" in next_action
    assert "Person-to-Employment-to-current-Assignment binding" in next_action
    assert "current Assignment/Job/Position worker scope" in next_action


def test_packet_correlates_policy_and_evidence_without_copying_worker_values() -> None:
    payload = json.loads(build_valid().canonical_json())
    assert payload["person_record_reference"] == PERSON
    assert payload["current_assignment_reference"] == CURRENT_ASSIGNMENT
    assert payload["proposed_position_record_reference"] == PROPOSED_POSITION
    assert payload["allocation_policy_reference"] == ALLOCATION_POLICY
    assert payload["allocation_policy_digest"] == DIGEST_C
    assert "person_name" not in payload
    assert "salary" not in payload
    assert "allocation_ratio" not in payload
    assert "model_output" not in payload


def test_canonical_json_and_digest_are_deterministic() -> None:
    packet = build_valid()
    canonical = packet.canonical_json()
    payload = json.loads(canonical)
    assert payload["generated_at"] == "2026-08-19T06:30:15.123456Z"
    assert payload["requested_effective_on"] == "2026-09-01"
    assert packet.sha256_digest() == sha256(canonical.encode("utf-8")).hexdigest()
    assert canonical == build_valid().canonical_json()


def test_timestamp_normalizes_to_utc_without_losing_precision() -> None:
    shifted = GENERATED_AT.astimezone(timezone(timedelta(hours=9)))
    assert build_valid(generated_at=shifted).canonical_json() == build_valid().canonical_json()
    later = build_valid(generated_at=GENERATED_AT.replace(microsecond=123457))
    assert later.canonical_json() != build_valid().canonical_json()
    assert later.sha256_digest() != build_valid().sha256_digest()


@pytest.mark.parametrize(
    "tenant",
    [
        "not-a-uuid",
        "00000000-0000-0000-0000-000000000000",
        "ffffffff-ffff-ffff-ffff-ffffffffffff",
        "11111111-1111-4111-8111-11111111111A",
        None,
    ],
)
def test_rejects_noncanonical_tenant_identity(tenant: object) -> None:
    with pytest.raises(ValueError, match="tenant_record_id"):
        build_valid(tenant_record_id=tenant)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("assignment_change_review_reference", "assignment_change_review:employee-42"),
        ("person_record_reference", "candidate_profile:33333333-3333-4333-8333-333333333333"),
        ("employment_record_reference", "employment_record:00000000-0000-0000-0000-000000000000"),
        ("current_assignment_reference", "assignment_record:not-a-uuid"),
        ("current_job_profile_reference", "job_profile:66666666-6666-4666-8666-66666666666A"),
        ("current_position_record_reference", "job_profile:77777777-7777-4777-8777-777777777777"),
        ("proposed_job_profile_reference", "job_profile:salary"),
        ("proposed_position_record_reference", "position_record:seat-12"),
        ("current_scope_snapshot_reference", "assignment_scope_snapshot:current-state"),
        ("allocation_plan_reference", "workforce_allocation_plan:75-percent"),
        ("allocation_policy_reference", "workforce_allocation_policy:manager-name"),
        ("worker_impact_assessment_reference", "worker_impact_assessment:Jane-Doe"),
        ("communication_plan_reference", "assignment_communication_plan:email-manager"),
        ("requester_reference", "actor:requester-name"),
        ("reviewer_reference", "actor:reviewer-name"),
    ],
)
def test_rejects_nonopaque_or_wrong_namespace_references(field: str, value: str) -> None:
    with pytest.raises(ValueError, match=field):
        build_valid(**{field: value})


@pytest.mark.parametrize(
    ("field", "prefix"),
    [
        ("assignment_change_review_reference", "assignment_change_review"),
        ("person_record_reference", "person_record"),
        ("employment_record_reference", "employment_record"),
        ("current_assignment_reference", "assignment_record"),
        ("current_job_profile_reference", "job_profile"),
        ("current_position_record_reference", "position_record"),
        ("proposed_job_profile_reference", "job_profile"),
        ("proposed_position_record_reference", "position_record"),
        ("current_scope_snapshot_reference", "assignment_scope_snapshot"),
        ("allocation_plan_reference", "workforce_allocation_plan"),
        ("allocation_policy_reference", "workforce_allocation_policy"),
        ("worker_impact_assessment_reference", "worker_impact_assessment"),
        ("communication_plan_reference", "assignment_communication_plan"),
        ("requester_reference", "actor"),
        ("reviewer_reference", "actor"),
    ],
)
def test_rejects_uuid1_trust_references_through_builder_and_replace(
    field: str,
    prefix: str,
) -> None:
    value = f"{prefix}:{UUID1_ID}"
    with pytest.raises(ValueError, match=field):
        build_valid(**{field: value})

    with pytest.raises(ValueError, match=field):
        replace(build_valid(), **{field: value})


@pytest.mark.parametrize(
    "field",
    [
        "current_scope_snapshot_digest",
        "allocation_plan_digest",
        "allocation_policy_digest",
        "worker_impact_assessment_digest",
        "communication_plan_digest",
    ],
)
def test_rejects_malformed_evidence_digests(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        build_valid(**{field: "ABC"})


@pytest.mark.parametrize("purpose", ["assignment_review", "assignment", "Assignment_Change_Review"])
def test_purpose_is_fixed(purpose: str) -> None:
    with pytest.raises(ValueError, match="purpose_code must remain assignment_change_review"):
        build_valid(purpose_code=purpose)


@pytest.mark.parametrize("reason", ["singleword", "Upper_case", "a" * 65, 7])
def test_reason_code_must_first_be_bounded_descriptive_snake_case(reason: object) -> None:
    with pytest.raises(ValueError, match="reason_code"):
        build_valid(reason_code=reason)


def test_reason_code_rejects_sensitive_or_unreviewed_free_form_categories() -> None:
    with pytest.raises(ValueError, match="approved assignment-change reason"):
        build_valid(reason_code="sensitive_health_condition")


@pytest.mark.parametrize(
    "reason",
    [
        "internal_reassignment",
        "workforce_reallocation",
        "temporary_detail",
        "position_reclassification",
        "organizational_realignment",
    ],
)
def test_accepts_only_reviewed_assignment_change_reason_categories(reason: str) -> None:
    assert build_valid(reason_code=reason).reason_code == reason


def test_requested_effective_date_must_be_a_business_date() -> None:
    with pytest.raises(ValueError, match="requested_effective_on"):
        build_valid(requested_effective_on="2026-09-01")
    with pytest.raises(ValueError, match="requested_effective_on"):
        build_valid(requested_effective_on=datetime(2026, 9, 1, tzinfo=timezone.utc))


@pytest.mark.parametrize(
    "generated_at",
    [
        datetime(2026, 8, 19, 6, 30),
        datetime(2026, 8, 19, 6, 30, tzinfo=UnknownOffsetTimezone()),
        "2026-08-19T06:30:00Z",
    ],
)
def test_generated_at_must_be_timezone_aware_datetime(generated_at: object) -> None:
    with pytest.raises(ValueError, match="generated_at"):
        build_valid(generated_at=generated_at)


def test_requester_and_reviewer_must_be_separate() -> None:
    with pytest.raises(ValueError, match="requester and reviewer must be different"):
        build_valid(reviewer_reference=REQUESTER)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("contains_person_pii", True, "must not contain person PII"),
        ("contains_compensation_values", True, "must not contain compensation values"),
        ("contains_free_form_model_output", True, "must not contain free-form model output"),
        ("human_confirmation_required", 1, "human confirmation is mandatory"),
        ("decision_authority", "model_decision", "decision_authority"),
        ("review_state", "approved", "review_state"),
        ("scope_verification_state", "verified", "scope_verification_state"),
        ("mutation_state", "applied", "mutation_state"),
        ("next_action", "Apply the reassignment automatically.", "next_action"),
    ],
)
def test_direct_construction_cannot_weaken_governance(field: str, value: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        replace(build_valid(), **{field: value})


def test_direct_construction_revalidates_reference_digest_and_reason() -> None:
    with pytest.raises(ValueError, match="person_record_reference"):
        replace(build_valid(), person_record_reference="person_record:Jane-Doe")
    with pytest.raises(ValueError, match="allocation_plan_digest"):
        replace(build_valid(), allocation_plan_digest="0" * 63)
    with pytest.raises(ValueError, match="approved assignment-change reason"):
        replace(build_valid(), reason_code="sensitive_health_condition")


def test_builder_returns_same_public_type_as_direct_contract() -> None:
    assert isinstance(build_valid(), AssignmentChangeReviewPacket)
