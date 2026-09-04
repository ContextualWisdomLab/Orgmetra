"""Tenant identity interoperability regressions for employment-separation review evidence."""

from datetime import date, datetime, timezone

import pytest

from orgmetra_employment_separation_review import build_employment_separation_review_packet


_AUTHORITATIVE_UUIDV7_TENANT = "10000000-0000-7000-8000-000000000001"


def _build_with_tenant(tenant_record_id: str):
    """Build a valid separation packet around the tenant identity under test."""
    return build_employment_separation_review_packet(
        tenant_record_id=tenant_record_id,
        separation_review_reference="employment_separation_review:22222222-2222-4222-8222-222222222222",
        person_record_reference="person_record:33333333-3333-4333-8333-333333333333",
        employment_record_reference="employment_record:44444444-4444-4444-8444-444444444444",
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
        reviewer_reference="actor:ffffffff-ffff-4fff-8fff-fffffffffff0",
        purpose_code="employment_separation_review",
        reason_code="voluntary_resignation",
        proposed_separation_on=date(2026, 9, 30),
        generated_at=datetime(2026, 8, 20, 8, 5, tzinfo=timezone.utc),
    )


def test_accepts_authoritative_operational_uuidv7_tenant_identity() -> None:
    """Accept the canonical UUIDv7 tenant form already accepted by protected HRIS core."""
    packet = _build_with_tenant(_AUTHORITATIVE_UUIDV7_TENANT)
    assert packet.tenant_record_id == _AUTHORITATIVE_UUIDV7_TENANT


@pytest.mark.parametrize(
    "tenant_record_id",
    [
        "00000000-0000-0000-0000-000000000000",
        "ffffffff-ffff-ffff-ffff-ffffffffffff",
    ],
)
def test_rejects_reserved_sentinel_tenant_identity(tenant_record_id: str) -> None:
    """Reject RFC 9562 Nil/Max sentinels while deferring UUID version policy to HRIS core."""
    with pytest.raises(ValueError, match="tenant_record_id"):
        _build_with_tenant(tenant_record_id)
