"""Regression for packet-level checked-versus-emitted runtime substitution."""

from datetime import date, datetime, timezone

import pytest

from orgmetra_organization_hierarchy_change_review import OrganizationHierarchyChangeReviewPacket


class TenantSwapPacket(OrganizationHierarchyChangeReviewPacket):
    """Return a different tenant value after the first validation read."""

    def __getattribute__(self, name: str) -> object:
        """Swap one trust-bearing field after its first read without mutating slots."""
        if name == "tenant_record_id":
            state = object.__getattribute__(self, "__dict__")
            reads = state.get("_tenant_reads", 0)
            state["_tenant_reads"] = reads + 1
            if reads > 0:
                return "not-a-uuid"
        return super().__getattribute__(name)


def test_rejects_packet_runtime_subclass_before_trust_field_validation() -> None:
    """Do not let packet polymorphism change validated evidence before canonical emission."""
    with pytest.raises(ValueError, match="exact OrganizationHierarchyChangeReviewPacket runtime type"):
        TenantSwapPacket(
            tenant_record_id="0195c23d-9f00-7000-8000-000000000001",
            organization_hierarchy_change_reference=(
                "organization_hierarchy_change:11111111-1111-4111-8111-111111111111"
            ),
            organization_unit_reference="organization_unit:0195c23d-9f00-7000-8000-000000000002",
            current_parent_organization_unit_reference=(
                "organization_unit:0195c23d-9f00-7000-8000-000000000003"
            ),
            proposed_parent_organization_unit_reference=(
                "organization_unit:0195c23d-9f00-7000-8000-000000000004"
            ),
            effective_on=date(2026, 9, 1),
            organization_unit_snapshot_digest="a" * 64,
            hierarchy_snapshot_digest="b" * 64,
            requester_reference="actor:22222222-2222-4222-8222-222222222222",
            reviewer_reference="actor:33333333-3333-4333-8333-333333333333",
            purpose_code="organization_hierarchy_change_review",
            reason_code="organizational_realignment",
            recorded_at=datetime(2026, 8, 23, 7, 0, tzinfo=timezone.utc),
        )
