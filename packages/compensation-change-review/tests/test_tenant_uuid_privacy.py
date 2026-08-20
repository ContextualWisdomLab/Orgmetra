"""Tenant identity interoperability regressions for compensation-change review evidence."""

from datetime import date, datetime, timezone

import pytest

from orgmetra_compensation_change_review import build_compensation_change_review_packet


_AUTHORITATIVE_UUIDV7_TENANT = "10000000-0000-7000-8000-000000000001"


def _build_with_tenant(tenant_record_id: str):
    """Build a valid value-minimized compensation packet around one tenant identity."""
    return build_compensation_change_review_packet(
        tenant_record_id=tenant_record_id,
        compensation_review_reference="compensation_change_review:22222222-2222-4222-8222-222222222222",
        person_record_reference="person_record:33333333-3333-4333-8333-333333333333",
        employment_record_reference="employment_record:44444444-4444-4444-8444-444444444444",
        active_assignment_snapshot_reference="active_assignment_snapshot:55555555-5555-4555-8555-555555555555",
        active_assignment_snapshot_digest="a" * 64,
        current_compensation_snapshot_reference="compensation_snapshot:66666666-6666-4666-8666-666666666666",
        current_compensation_snapshot_digest="b" * 64,
        proposed_compensation_plan_reference="compensation_plan:77777777-7777-4777-8777-777777777777",
        proposed_compensation_plan_digest="c" * 64,
        compensation_policy_reference="compensation_policy:88888888-8888-4888-8888-888888888888",
        compensation_policy_digest="d" * 64,
        pay_equity_review_reference="pay_equity_review:99999999-9999-4999-8999-999999999999",
        pay_equity_review_digest="e" * 64,
        budget_authorization_reference="budget_authorization:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        budget_authorization_digest="f" * 64,
        payroll_handoff_plan_reference="payroll_handoff_plan:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        payroll_handoff_plan_digest="1" * 64,
        requester_reference="actor:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        reviewer_reference="actor:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        purpose_code="compensation_change_review",
        reason_code="annual_compensation_review",
        proposed_effective_on=date(2026, 10, 1),
        generated_at=datetime(2026, 8, 20, 8, 15, tzinfo=timezone.utc),
        evidence_version=1,
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
