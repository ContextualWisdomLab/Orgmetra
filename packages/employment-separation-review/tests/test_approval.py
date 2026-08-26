"""Contract tests for authoritative human approval of reviewed separations."""

from datetime import date, datetime, timezone

from orgmetra_employment_separation_review import build_employment_separation_review_packet
from orgmetra_employment_separation_review.approval import (
    EmploymentSeparationApprovalAuthority,
    EmploymentSeparationApprovalVerification,
    approve_employment_separation,
)

TENANT = "11111111-1111-4111-8111-111111111111"
REVIEW = "employment_separation_review:22222222-2222-4222-8222-222222222222"
PERSON = "person_record:33333333-3333-4333-8333-333333333333"
EMPLOYMENT = "employment_record:44444444-4444-4444-8444-444444444444"
REVIEWER = "actor:ffffffff-ffff-4fff-8fff-fffffffffff0"
APPROVED_AT = datetime(2026, 8, 20, 9, 10, 15, 123456, tzinfo=timezone.utc)


def _packet():
    return build_employment_separation_review_packet(
        tenant_record_id=TENANT,
        separation_review_reference=REVIEW,
        person_record_reference=PERSON,
        employment_record_reference=EMPLOYMENT,
        active_assignment_snapshot_reference="active_assignment_snapshot:55555555-5555-4555-8555-555555555555",
        active_assignment_snapshot_digest="a" * 64,
        separation_policy_reference="employment_separation_policy:66666666-6666-4666-8666-666666666666",
        separation_policy_digest="b" * 64,
        separation_process_reference="employment_separation_process:77777777-7777-4777-8777-777777777777",
        separation_process_digest="c" * 64,
        final_pay_handoff_reference="final_pay_handoff:88888888-8888-4888-8888-888888888888",
        final_pay_handoff_digest="d" * 64,
        benefits_handoff_reference="benefits_handoff:99999999-9999-4999-8999-999999999999",
        benefits_handoff_digest="e" * 64,
        access_deprovisioning_plan_reference="access_deprovisioning_plan:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        access_deprovisioning_plan_digest="f" * 64,
        asset_return_plan_reference="asset_return_plan:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        asset_return_plan_digest="1" * 64,
        knowledge_transfer_plan_reference="knowledge_transfer_plan:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        knowledge_transfer_plan_digest="2" * 64,
        communication_plan_reference="separation_communication_plan:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        communication_plan_digest="3" * 64,
        requester_reference="actor:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
        reviewer_reference=REVIEWER,
        purpose_code="employment_separation_review",
        reason_code="voluntary_resignation",
        proposed_separation_on=date(2026, 9, 30),
        generated_at=datetime(2026, 8, 19, 9, 10, 15, 123456, tzinfo=timezone.utc),
    )


class AllowingAuthority(EmploymentSeparationApprovalAuthority):
    """Return evidence for the exact reviewed packet and accountable reviewer."""

    def verify_approval(self, *, packet, approving_actor_reference, approved_at):
        return EmploymentSeparationApprovalVerification(
            tenant_record_id=packet.tenant_record_id,
            separation_review_reference=packet.separation_review_reference,
            review_digest=packet.sha256_digest(),
            person_record_reference=packet.person_record_reference,
            employment_record_reference=packet.employment_record_reference,
            approving_actor_reference=approving_actor_reference,
            authority_evidence_reference="separation_approval_verification:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            authority_evidence_digest="4" * 64,
        )


def test_approved_receipt_remains_non_authorizing() -> None:
    receipt = approve_employment_separation(
        packet=_packet(),
        authority=AllowingAuthority(),
        approving_actor_reference=REVIEWER,
        approved_at=APPROVED_AT,
    )
    assert receipt.approval_state == "human_approved_for_authoritative_resolution"
    assert receipt.mutation_state == "not_authorized_to_apply"
    assert receipt.external_execution_state == "not_authorized_to_execute"
    assert receipt.review_digest == _packet().sha256_digest()
