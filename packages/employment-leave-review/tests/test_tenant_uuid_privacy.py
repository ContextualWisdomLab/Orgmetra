"""Tenant identity interoperability regressions for leave-review evidence."""

from datetime import date, datetime, timezone

import pytest

from orgmetra_employment_leave_review import build_employment_leave_review_packet


_AUTHORITATIVE_UUIDV7_TENANT = "10000000-0000-7000-8000-000000000001"


def _build_with_tenant(tenant_record_id: str):
    """Build a valid value-minimized leave packet around the tenant identity under test."""
    return build_employment_leave_review_packet(
        tenant_record_id=tenant_record_id,
        leave_review_reference="employment_leave_review:22222222-2222-4222-8222-222222222222",
        person_record_reference="person_record:33333333-3333-4333-8333-333333333333",
        employment_record_reference="employment_record:44444444-4444-4444-8444-444444444444",
        active_assignment_snapshot_reference="active_assignment_snapshot:55555555-5555-4555-8555-555555555555",
        active_assignment_snapshot_digest="a" * 64,
        leave_case_reference="leave_case:66666666-6666-4666-8666-666666666666",
        leave_case_digest="a" * 64,
        leave_policy_reference="leave_policy:77777777-7777-4777-8777-777777777777",
        leave_policy_digest="a" * 64,
        work_continuity_plan_reference="work_continuity_plan:88888888-8888-4888-8888-888888888888",
        work_continuity_plan_digest="a" * 64,
        benefits_continuity_plan_reference="benefits_continuity_plan:99999999-9999-4999-8999-999999999999",
        benefits_continuity_plan_digest="a" * 64,
        return_to_work_plan_reference="return_to_work_plan:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        return_to_work_plan_digest="a" * 64,
        handling_policy_reference="personal_data_handling_policy:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        handling_policy_digest="a" * 64,
        retention_policy_reference="retention_policy:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
        retention_policy_digest="a" * 64,
        requester_reference="actor:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        reviewer_reference="actor:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        purpose_code="employment_leave_review",
        reason_code="policy_entitlement_review",
        requested_leave_start_on=date(2026, 9, 1),
        requested_leave_end_on=date(2026, 9, 30),
        generated_at=datetime(2026, 8, 20, 8, 10, tzinfo=timezone.utc),
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
