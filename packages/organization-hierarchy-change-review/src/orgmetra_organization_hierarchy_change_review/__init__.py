"""Public governed organization-hierarchy change review contract."""

from datetime import date, datetime

from .review import OrganizationHierarchyChangeReviewPacket


def _bind_public_builder(
    packet_type: type[OrganizationHierarchyChangeReviewPacket],
):
    """Bind the package builder to the governed packet type once at import."""

    def build_organization_hierarchy_change_review_packet(
        *,
        tenant_record_id: str,
        organization_hierarchy_change_reference: str,
        organization_unit_reference: str,
        current_parent_organization_unit_reference: str | None,
        proposed_parent_organization_unit_reference: str | None,
        effective_on: date,
        organization_unit_snapshot_digest: str,
        hierarchy_snapshot_digest: str,
        requester_reference: str,
        reviewer_reference: str,
        purpose_code: str,
        reason_code: str,
        recorded_at: datetime,
        evidence_version: int = 1,
    ) -> OrganizationHierarchyChangeReviewPacket:
        """Build governed hierarchy-change review evidence through the bound packet type."""
        return packet_type(
            tenant_record_id=tenant_record_id,
            organization_hierarchy_change_reference=organization_hierarchy_change_reference,
            organization_unit_reference=organization_unit_reference,
            current_parent_organization_unit_reference=current_parent_organization_unit_reference,
            proposed_parent_organization_unit_reference=proposed_parent_organization_unit_reference,
            effective_on=effective_on,
            organization_unit_snapshot_digest=organization_unit_snapshot_digest,
            hierarchy_snapshot_digest=hierarchy_snapshot_digest,
            requester_reference=requester_reference,
            reviewer_reference=reviewer_reference,
            purpose_code=purpose_code,
            reason_code=reason_code,
            recorded_at=recorded_at,
            evidence_version=evidence_version,
        )

    return build_organization_hierarchy_change_review_packet


build_organization_hierarchy_change_review_packet = _bind_public_builder(
    OrganizationHierarchyChangeReviewPacket
)
del _bind_public_builder

__all__ = [
    "OrganizationHierarchyChangeReviewPacket",
    "build_organization_hierarchy_change_review_packet",
]
