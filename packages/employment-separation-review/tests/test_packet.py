from dataclasses import replace
from datetime import date, datetime, timedelta, timezone, tzinfo
from hashlib import sha256
import json

import pytest

from orgmetra_employment_separation_review import (
    EmploymentSeparationReviewPacket,
    build_employment_separation_review_packet,
)

TENANT = "11111111-1111-4111-8111-111111111111"
REVIEW = "employment_separation_review:22222222-2222-4222-8222-222222222222"
PERSON = "person_record:33333333-3333-4333-8333-333333333333"
EMPLOYMENT = "employment_record:44444444-4444-4444-8444-444444444444"
ASSIGNMENT_SCOPE = "active_assignment_snapshot:55555555-5555-4555-8555-555555555555"
SEPARATION_POLICY = "employment_separation_policy:66666666-6666-4666-8666-666666666666"
SEPARATION_PROCESS = "employment_separation_process:77777777-7777-4777-8777-777777777777"
FINAL_PAY = "final_pay_handoff:88888888-8888-4888-8888-888888888888"
BENEFITS = "benefits_handoff:99999999-9999-4999-8999-999999999999"
ACCESS = "access_deprovisioning_plan:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
ASSET_RETURN = "asset_return_plan:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
KNOWLEDGE_TRANSFER = "knowledge_transfer_plan:cccccccc-cccc-4ccc-8ccc-cccccccccccc"
COMMUNICATION = "separation_communication_plan:dddddddd-dddd-4ddd-8ddd-dddddddddddd"
REQUESTER = "actor:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
REVIEWER = "actor:ffffffff-ffff-4fff-8fff-fffffffffff0"
UUID1_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
DIGEST_E = "e" * 64
DIGEST_F = "f" * 64
DIGEST_1 = "1" * 64
DIGEST_2 = "2" * 64
GENERATED_AT = datetime(2026, 8, 19, 9, 10, 15, 123456, tzinfo=timezone.utc)


class UnknownOffsetTimezone(tzinfo):
    def utcoffset(self, dt: datetime | None) -> None:
        return None

    def dst(self, dt: datetime | None) -> None:
        return None


def build_valid(**overrides: object) -> EmploymentSeparationReviewPacket:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "separation_review_reference": REVIEW,
        "person_record_reference": PERSON,
        "employment_record_reference": EMPLOYMENT,
        "active_assignment_snapshot_reference": ASSIGNMENT_SCOPE,
        "active_assignment_snapshot_digest": DIGEST_A,
        "separation_policy_reference": SEPARATION_POLICY,
        "separation_policy_digest": DIGEST_B,
        "separation_process_reference": SEPARATION_PROCESS,
        "separation_process_digest": DIGEST_C,
        "final_pay_handoff_reference": FINAL_PAY,
        "final_pay_handoff_digest": DIGEST_D,
        "benefits_handoff_reference": BENEFITS,
        "benefits_handoff_digest": DIGEST_E,
        "access_deprovisioning_plan_reference": ACCESS,
        "access_deprovisioning_plan_digest": DIGEST_F,
        "asset_return_plan_reference": ASSET_RETURN,
        "asset_return_plan_digest": DIGEST_1,
        "knowledge_transfer_plan_reference": KNOWLEDGE_TRANSFER,
        "knowledge_transfer_plan_digest": DIGEST_2,
        "communication_plan_reference": COMMUNICATION,
        "communication_plan_digest": "3" * 64,
        "requester_reference": REQUESTER,
        "reviewer_reference": REVIEWER,
        "purpose_code": "employment_separation_review",
        "reason_code": "voluntary_resignation",
        "proposed_separation_on": date(2026, 9, 30),
        "generated_at": GENERATED_AT,
    }
    values.update(overrides)
    return build_employment_separation_review_packet(**values)


def test_builds_value_free_pre_mutation_separation_review_packet() -> None:
    packet = build_valid()
    assert packet.contains_person_pii is False
    assert packet.contains_compensation_values is False
    assert packet.contains_free_form_case_narrative is False
    assert packet.contains_free_form_model_output is False
    assert packet.human_confirmation_required is True
    assert packet.decision_authority == "human_review_only"
    assert packet.review_state == "requires_human_review"
    assert packet.scope_verification_state == "requires_authoritative_resolution"
    assert packet.mutation_state == "not_authorized_to_apply"
    assert packet.external_execution_state == "not_authorized_to_execute"
    assert "authoritative People mutation boundary" in packet.next_action
    assert "published owner boundaries" in packet.next_action


def test_packet_correlates_exit_controls_without_copying_worker_values() -> None:
    payload = json.loads(build_valid().canonical_json())
    assert payload["person_record_reference"] == PERSON
    assert payload["employment_record_reference"] == EMPLOYMENT
    assert payload["active_assignment_snapshot_reference"] == ASSIGNMENT_SCOPE
    assert payload["separation_policy_reference"] == SEPARATION_POLICY
    assert payload["final_pay_handoff_reference"] == FINAL_PAY
    assert payload["access_deprovisioning_plan_reference"] == ACCESS
    assert "person_name" not in payload
    assert "salary" not in payload
    assert "benefit_amount" not in payload
    assert "disciplinary_narrative" not in payload
    assert "credential" not in payload
    assert "model_output" not in payload


def test_canonical_json_and_digest_are_deterministic() -> None:
    packet = build_valid()
    canonical = packet.canonical_json()
    payload = json.loads(canonical)
    assert payload["generated_at"] == "2026-08-19T09:10:15.123456Z"
    assert payload["proposed_separation_on"] == "2026-09-30"
    assert packet.sha256_digest() == sha256(canonical.encode("utf-8")).hexdigest()
    assert canonical == build_valid().canonical_json()


def test_post_construction_review_rewrite_cannot_change_canonical_evidence() -> None:
    packet = build_valid()
    object.__setattr__(packet, "reason_code", "retirement_transition")
    with pytest.raises(ValueError, match="changed after review issuance"):
        packet.canonical_json()


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
        ("separation_review_reference", "employment_separation_review:employee-42"),
        ("person_record_reference", "candidate_profile:33333333-3333-4333-8333-333333333333"),
        ("employment_record_reference", "employment_record:00000000-0000-0000-0000-000000000000"),
        ("active_assignment_snapshot_reference", "active_assignment_snapshot:not-a-uuid"),
        ("separation_policy_reference", "employment_separation_policy:medical-condition"),
        ("separation_process_reference", "employment_separation_process:manager-name"),
        ("final_pay_handoff_reference", "final_pay_handoff:120000"),
        ("benefits_handoff_reference", "benefits_handoff:health-plan-name"),
        ("access_deprovisioning_plan_reference", "access_deprovisioning_plan:jsmith"),
        ("asset_return_plan_reference", "asset_return_plan:laptop-serial"),
        ("knowledge_transfer_plan_reference", "knowledge_transfer_plan:project-name"),
        ("communication_plan_reference", "separation_communication_plan:email-manager"),
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
        ("separation_review_reference", "employment_separation_review"),
        ("person_record_reference", "person_record"),
        ("employment_record_reference", "employment_record"),
        ("active_assignment_snapshot_reference", "active_assignment_snapshot"),
        ("separation_policy_reference", "employment_separation_policy"),
        ("separation_process_reference", "employment_separation_process"),
        ("final_pay_handoff_reference", "final_pay_handoff"),
        ("benefits_handoff_reference", "benefits_handoff"),
        ("access_deprovisioning_plan_reference", "access_deprovisioning_plan"),
        ("asset_return_plan_reference", "asset_return_plan"),
        ("knowledge_transfer_plan_reference", "knowledge_transfer_plan"),
        ("communication_plan_reference", "separation_communication_plan"),
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
        "active_assignment_snapshot_digest",
        "separation_policy_digest",
        "separation_process_digest",
        "final_pay_handoff_digest",
        "benefits_handoff_digest",
        "access_deprovisioning_plan_digest",
        "asset_return_plan_digest",
        "knowledge_transfer_plan_digest",
        "communication_plan_digest",
    ],
)
def test_rejects_malformed_evidence_digests(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        build_valid(**{field: "ABC"})


@pytest.mark.parametrize(
    "purpose",
    ["separation_review", "separation", "Employment_Separation_Review"],
)
def test_purpose_is_fixed(purpose: str) -> None:
    with pytest.raises(ValueError, match="purpose_code must remain employment_separation_review"):
        build_valid(purpose_code=purpose)


@pytest.mark.parametrize("reason", ["singleword", "Upper_case", "a" * 65, 7])
def test_reason_code_must_first_be_bounded_descriptive_snake_case(reason: object) -> None:
    with pytest.raises(ValueError, match="reason_code"):
        build_valid(reason_code=reason)


def test_reason_code_rejects_sensitive_or_unreviewed_free_form_categories() -> None:
    with pytest.raises(ValueError, match="approved separation reason"):
        build_valid(reason_code="sensitive_health_condition")


@pytest.mark.parametrize(
    "reason",
    [
        "voluntary_resignation",
        "retirement_transition",
        "fixed_term_completion",
        "position_elimination",
        "employer_initiated_separation",
    ],
)
def test_accepts_only_reviewed_separation_reason_categories(reason: str) -> None:
    assert build_valid(reason_code=reason).reason_code == reason


def test_proposed_separation_date_must_be_a_business_date() -> None:
    with pytest.raises(ValueError, match="proposed_separation_on"):
        build_valid(proposed_separation_on="2026-09-30")
    with pytest.raises(ValueError, match="proposed_separation_on"):
        build_valid(proposed_separation_on=datetime(2026, 9, 30, tzinfo=timezone.utc))


@pytest.mark.parametrize(
    "generated_at",
    [
        datetime(2026, 8, 19, 9, 10),
        datetime(2026, 8, 19, 9, 10, tzinfo=UnknownOffsetTimezone()),
        "2026-08-19T09:10:00Z",
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
        ("contains_free_form_case_narrative", True, "must not contain free-form case narrative"),
        ("contains_free_form_model_output", True, "must not contain free-form model output"),
        ("human_confirmation_required", 1, "human confirmation is mandatory"),
        ("decision_authority", "model_decision", "decision_authority"),
        ("review_state", "approved", "review_state"),
        ("scope_verification_state", "verified", "scope_verification_state"),
        ("mutation_state", "applied", "mutation_state"),
        ("external_execution_state", "executed", "external_execution_state"),
        ("next_action", "Terminate employment and revoke access automatically.", "next_action"),
    ],
)
def test_direct_construction_cannot_weaken_governance(field: str, value: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        replace(build_valid(), **{field: value})


def test_direct_construction_revalidates_reference_digest_and_reason() -> None:
    with pytest.raises(ValueError, match="person_record_reference"):
        replace(build_valid(), person_record_reference="person_record:Jane-Doe")
    with pytest.raises(ValueError, match="separation_policy_digest"):
        replace(build_valid(), separation_policy_digest="0" * 63)
    with pytest.raises(ValueError, match="approved separation reason"):
        replace(build_valid(), reason_code="sensitive_health_condition")


def test_builder_returns_same_public_type_as_direct_contract() -> None:
    assert isinstance(build_valid(), EmploymentSeparationReviewPacket)
