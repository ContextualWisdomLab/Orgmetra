"""Tenant identity interoperability regressions for assignment-change review evidence."""

from datetime import date, datetime, timezone

import pytest

from orgmetra_assignment_change_review import build_assignment_change_review_packet


_AUTHORITATIVE_UUIDV7_TENANT = "10000000-0000-7000-8000-000000000001"


def _build_with_tenant(tenant_record_id: str):
    """Build the smallest valid packet around the tenant identity under test."""
    return build_assignment_change_review_packet(
        tenant_record_id=tenant_record_id,
        assignment_change_review_reference="assignment_change_review:22222222-2222-4222-8222-222222222222",
        person_record_reference="person_record:33333333-3333-4333-8333-333333333333",
        employment_record_reference="employment_record:44444444-4444-4444-8444-444444444444",
        current_assignment_reference="assignment_record:55555555-5555-4555-8555-555555555555",
        current_job_profile_reference="job_profile:66666666-6666-4666-8666-666666666666",
        current_position_record_reference="position_record:77777777-7777-4777-8777-777777777777",
        proposed_job_profile_reference="job_profile:88888888-8888-4888-8888-888888888888",
        proposed_position_record_reference="position_record:99999999-9999-4999-8999-999999999999",
        current_scope_snapshot_reference="assignment_scope_snapshot:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        current_scope_snapshot_digest="a" * 64,
        allocation_plan_reference="workforce_allocation_plan:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        allocation_plan_digest="b" * 64,
        allocation_policy_reference="workforce_allocation_policy:abababab-abab-4bab-8bab-abababababab",
        allocation_policy_digest="c" * 64,
        worker_impact_assessment_reference="worker_impact_assessment:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        worker_impact_assessment_digest="d" * 64,
        communication_plan_reference="assignment_communication_plan:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        communication_plan_digest="e" * 64,
        requester_reference="actor:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
        reviewer_reference="actor:ffffffff-ffff-4fff-8fff-fffffffffff0",
        purpose_code="assignment_change_review",
        reason_code="workforce_reallocation",
        requested_effective_on=date(2026, 9, 1),
        generated_at=datetime(2026, 8, 20, 7, 55, tzinfo=timezone.utc),
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
