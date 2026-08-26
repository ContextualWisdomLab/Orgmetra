"""Contract and adversarial tests for authoritative Employment separation approval."""

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json

import pytest

from orgmetra_employment_separation_review import (
    EmploymentSeparationApprovalReceipt,
    EmploymentSeparationApprovalVerification,
    build_employment_separation_review_packet,
    approve_employment_separation,
)
from orgmetra_employment_separation_review import approval as approval_module

TENANT = "11111111-1111-4111-8111-111111111111"
REVIEW = "employment_separation_review:22222222-2222-4222-8222-222222222222"
PERSON = "person_record:33333333-3333-4333-8333-333333333333"
EMPLOYMENT = "employment_record:44444444-4444-4444-8444-444444444444"
REQUESTER = "actor:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
REVIEWER = "actor:ffffffff-ffff-4fff-8fff-fffffffffff0"
OTHER_ACTOR = "actor:12121212-1212-4212-8212-121212121212"
AUTHORITY_REFERENCE = "separation_approval_verification:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
GENERATED_AT = datetime(2026, 8, 19, 9, 10, 15, 123456, tzinfo=timezone.utc)
APPROVED_AT = datetime(2026, 8, 20, 9, 10, 15, 123456, tzinfo=timezone.utc)


def build_packet(**overrides: object):
    """Build one value-minimized parent review without cross-test fixture coupling."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "separation_review_reference": REVIEW,
        "person_record_reference": PERSON,
        "employment_record_reference": EMPLOYMENT,
        "active_assignment_snapshot_reference": "active_assignment_snapshot:55555555-5555-4555-8555-555555555555",
        "active_assignment_snapshot_digest": "a" * 64,
        "separation_policy_reference": "employment_separation_policy:66666666-6666-4666-8666-666666666666",
        "separation_policy_digest": "b" * 64,
        "separation_process_reference": "employment_separation_process:77777777-7777-4777-8777-777777777777",
        "separation_process_digest": "c" * 64,
        "final_pay_handoff_reference": "final_pay_handoff:88888888-8888-4888-8888-888888888888",
        "final_pay_handoff_digest": "d" * 64,
        "benefits_handoff_reference": "benefits_handoff:99999999-9999-4999-8999-999999999999",
        "benefits_handoff_digest": "e" * 64,
        "access_deprovisioning_plan_reference": "access_deprovisioning_plan:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "access_deprovisioning_plan_digest": "f" * 64,
        "asset_return_plan_reference": "asset_return_plan:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "asset_return_plan_digest": "1" * 64,
        "knowledge_transfer_plan_reference": "knowledge_transfer_plan:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "knowledge_transfer_plan_digest": "2" * 64,
        "communication_plan_reference": "separation_communication_plan:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
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


class RecordingAuthority:
    """Return exact-scope verification while exposing whether authority work ran."""

    def __init__(self, *, overrides: dict[str, object] | None = None) -> None:
        self.calls = 0
        self.approved_at: datetime | None = None
        self.overrides = overrides or {}

    def verify_approval(self, *, packet, approving_actor_reference, approved_at):
        self.calls += 1
        self.approved_at = approved_at
        values: dict[str, object] = {
            "tenant_record_id": packet.tenant_record_id,
            "separation_review_reference": packet.separation_review_reference,
            "review_digest": packet.sha256_digest(),
            "person_record_reference": packet.person_record_reference,
            "employment_record_reference": packet.employment_record_reference,
            "approving_actor_reference": approving_actor_reference,
            "authority_evidence_reference": AUTHORITY_REFERENCE,
            "authority_evidence_digest": "4" * 64,
        }
        values.update(self.overrides)
        return EmploymentSeparationApprovalVerification(**values)


class WrongResultAuthority:
    """Return an ungoverned result to exercise exact result-type enforcement."""

    def verify_approval(self, *, packet, approving_actor_reference, approved_at):
        return object()


class MutatingAuthority:
    """Rewrite the otherwise frozen parent packet while returning self-consistent evidence."""

    def verify_approval(self, *, packet, approving_actor_reference, approved_at):
        object.__setattr__(packet, "reason_code", "retirement_transition")
        return EmploymentSeparationApprovalVerification(
            tenant_record_id=packet.tenant_record_id,
            separation_review_reference=packet.separation_review_reference,
            review_digest=packet.sha256_digest(),
            person_record_reference=packet.person_record_reference,
            employment_record_reference=packet.employment_record_reference,
            approving_actor_reference=approving_actor_reference,
            authority_evidence_reference=AUTHORITY_REFERENCE,
            authority_evidence_digest="4" * 64,
        )


def approve_valid(*, authority=None, approved_at: datetime = APPROVED_AT):
    """Issue one valid receipt for focused integrity assertions."""
    return approve_employment_separation(
        packet=build_packet(),
        authority=authority or RecordingAuthority(),
        approving_actor_reference=REVIEWER,
        approved_at=approved_at,
    )


def test_approved_receipt_is_value_minimized_and_non_authorizing() -> None:
    receipt = approve_valid()
    payload = receipt.canonical_document()
    canonical = receipt.canonical_json()

    assert payload["approval_state"] == "human_approved_for_authoritative_resolution"
    assert payload["mutation_state"] == "not_authorized_to_apply"
    assert payload["external_execution_state"] == "not_authorized_to_execute"
    assert payload["human_confirmation"] is True
    assert payload["review_digest"] == build_packet().sha256_digest()
    assert payload["person_record_reference"] == PERSON
    assert payload["employment_record_reference"] == EMPLOYMENT
    assert "salary" not in canonical
    assert "case_narrative" not in canonical
    assert "medical" not in canonical
    assert receipt.sha256_digest() == sha256(canonical.encode("utf-8")).hexdigest()
    assert repr(receipt) == "EmploymentSeparationApprovalReceipt(<redacted>)"


def test_authority_receives_the_exact_frozen_approval_instant() -> None:
    authority = RecordingAuthority()
    shifted = APPROVED_AT.astimezone(timezone(timedelta(hours=9)))
    receipt = approve_valid(authority=authority, approved_at=shifted)
    assert authority.calls == 1
    assert authority.approved_at == APPROVED_AT
    assert receipt.approved_at == APPROVED_AT
    assert json.loads(receipt.canonical_json())["approved_at"] == "2026-08-20T09:10:15.123456Z"


def test_rejects_non_packet_runtime_type_before_authority() -> None:
    authority = RecordingAuthority()
    with pytest.raises(TypeError, match="EmploymentSeparationReviewPacket"):
        approve_employment_separation(
            packet=object(),
            authority=authority,
            approving_actor_reference=REVIEWER,
            approved_at=APPROVED_AT,
        )
    assert authority.calls == 0


def test_rejects_malformed_approval_time_before_authority() -> None:
    authority = RecordingAuthority()
    with pytest.raises(ValueError, match="approved_at"):
        approve_employment_separation(
            packet=build_packet(),
            authority=authority,
            approving_actor_reference=REVIEWER,
            approved_at=APPROVED_AT.replace(tzinfo=None),
        )
    assert authority.calls == 0


def test_rejects_approval_before_review_generation_before_authority() -> None:
    authority = RecordingAuthority()
    with pytest.raises(ValueError, match="must not precede"):
        approve_employment_separation(
            packet=build_packet(),
            authority=authority,
            approving_actor_reference=REVIEWER,
            approved_at=GENERATED_AT - timedelta(microseconds=1),
        )
    assert authority.calls == 0


def test_rejects_non_reviewer_approval_before_authority() -> None:
    authority = RecordingAuthority()
    with pytest.raises(ValueError, match="accountable reviewer"):
        approve_employment_separation(
            packet=build_packet(),
            authority=authority,
            approving_actor_reference=OTHER_ACTOR,
            approved_at=APPROVED_AT,
        )
    assert authority.calls == 0


def test_rejects_wrong_authority_result_runtime_type() -> None:
    with pytest.raises(TypeError, match="EmploymentSeparationApprovalVerification"):
        approve_valid(authority=WrongResultAuthority())


def test_rejects_authority_evidence_for_different_review_scope() -> None:
    authority = RecordingAuthority(
        overrides={
            "employment_record_reference": "employment_record:56565656-5656-4656-8656-565656565656"
        }
    )
    with pytest.raises(ValueError, match="different reviewed separation"):
        approve_valid(authority=authority)


def test_rejects_malformed_authority_evidence_before_receipt_issuance() -> None:
    authority = RecordingAuthority(overrides={"authority_evidence_digest": "not-a-digest"})
    with pytest.raises(ValueError, match="authority_evidence_digest"):
        approve_valid(authority=authority)


def test_rejects_parent_review_mutation_during_authority_work() -> None:
    with pytest.raises(ValueError, match="changed during authority verification"):
        approve_valid(authority=MutatingAuthority())


def test_verification_repr_is_redacted() -> None:
    verification = RecordingAuthority().verify_approval(
        packet=build_packet(),
        approving_actor_reference=REVIEWER,
        approved_at=APPROVED_AT,
    )
    assert repr(verification) == "EmploymentSeparationApprovalVerification(<redacted>)"
    assert PERSON not in repr(verification)


def test_direct_receipt_construction_is_not_issuance() -> None:
    with pytest.raises(TypeError, match="only be issued"):
        EmploymentSeparationApprovalReceipt(
            tenant_record_id=TENANT,
            separation_review_reference=REVIEW,
            review_digest="5" * 64,
            person_record_reference=PERSON,
            employment_record_reference=EMPLOYMENT,
            approving_actor_reference=REVIEWER,
            authority_evidence_reference=AUTHORITY_REFERENCE,
            authority_evidence_digest="4" * 64,
            approved_at=APPROVED_AT,
        )


def test_receipt_runtime_type_is_final() -> None:
    with pytest.raises(TypeError, match="is final"):
        class ForgedReceipt(EmploymentSeparationApprovalReceipt):
            pass


def test_dataclass_replace_cannot_reissue_a_receipt() -> None:
    receipt = approve_valid()
    with pytest.raises(TypeError, match="only be issued"):
        replace(receipt, approving_actor_reference=OTHER_ACTOR)


def test_post_issuance_valid_scope_rewrite_fails_integrity() -> None:
    receipt = approve_valid()
    object.__setattr__(
        receipt,
        "employment_record_reference",
        "employment_record:56565656-5656-4656-8656-565656565656",
    )
    with pytest.raises(ValueError, match="changed after issuance"):
        receipt.canonical_json()


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("purpose_code", "employment_change_approval", "purpose_code"),
        ("approval_reason_code", "human_approved_other_change", "approval_reason_code"),
        ("evidence_version", 2, "evidence_version"),
        ("human_confirmation", False, "human confirmation"),
        ("approval_state", "approved", "approval_state"),
        ("mutation_state", "authorized_to_apply", "mutation_state"),
        ("external_execution_state", "authorized_to_execute", "external_execution_state"),
    ],
)
def test_post_issuance_governance_rewrite_fails_closed(
    field_name: str,
    value: object,
    message: str,
) -> None:
    receipt = approve_valid()
    object.__setattr__(receipt, field_name, value)
    with pytest.raises(ValueError, match=message):
        receipt.canonical_json()


def test_post_issuance_marker_or_token_rewrite_fails_closed() -> None:
    receipt = approve_valid()
    object.__setattr__(receipt, "_issuance_marker", object())
    with pytest.raises(ValueError, match="changed after issuance"):
        receipt.canonical_json()

    receipt = approve_valid()
    object.__setattr__(receipt, "_issuance_token", object())
    with pytest.raises(ValueError, match="changed after issuance"):
        receipt.canonical_json()


def test_recomputed_packet_owned_seal_cannot_replace_authoritative_seal() -> None:
    receipt = approve_valid()
    object.__setattr__(
        receipt,
        "employment_record_reference",
        "employment_record:56565656-5656-4656-8656-565656565656",
    )
    forged_json = approval_module.json.dumps(
        receipt._payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    object.__setattr__(receipt, "_creation_seal", approval_module._seal(forged_json))
    with pytest.raises(ValueError, match="changed after issuance"):
        receipt.canonical_json()


def test_missing_process_local_issuance_evidence_fails_closed() -> None:
    receipt = approve_valid()
    approval_module._discard_creation_seal(id(receipt))
    with pytest.raises(ValueError, match="changed after issuance"):
        receipt.canonical_json()


def test_receipt_rejects_noncanonical_stored_timestamp() -> None:
    receipt = approve_valid()
    object.__setattr__(receipt, "approved_at", APPROVED_AT.replace(tzinfo=None))
    with pytest.raises(ValueError, match="approved_at"):
        receipt.canonical_json()


def test_caller_cannot_preseed_internal_issuance_state() -> None:
    with pytest.raises(ValueError, match="changed during issuance"):
        EmploymentSeparationApprovalReceipt(
            tenant_record_id=TENANT,
            separation_review_reference=REVIEW,
            review_digest="5" * 64,
            person_record_reference=PERSON,
            employment_record_reference=EMPLOYMENT,
            approving_actor_reference=REVIEWER,
            authority_evidence_reference=AUTHORITY_REFERENCE,
            authority_evidence_digest="4" * 64,
            approved_at=APPROVED_AT,
            _issuance_token=approval_module._RECEIPT_ISSUANCE_TOKEN,
            _creation_seal="6" * 64,
        )
