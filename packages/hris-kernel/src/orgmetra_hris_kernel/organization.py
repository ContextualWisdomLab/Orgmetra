"""Tenant-scoped bitemporal organization hierarchy integrity rules."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from orgmetra_hris_kernel.errors import OrganizationHierarchyError
from orgmetra_hris_kernel.facts import OrganizationUnitVersion
from orgmetra_hris_kernel.resolution import resolve_single_valued_fact


def validate_organization_hierarchy(
    organization_versions: list[OrganizationUnitVersion],
    *,
    tenant_record_id: UUID,
    effective_on: date,
    known_at: datetime,
) -> None:
    """Reject a visible parent cycle inside one tenant at one bitemporal coordinate.

    Each durable unit is first resolved through the normal single-valued
    bitemporal rule, so two simultaneously visible versions fail closed before
    graph traversal. Parent anchors without a visible version terminate the
    currently known chain rather than importing facts from another tenant or a
    future knowledge state.

    Args:
        organization_versions: Candidate parent-link versions, including other tenants.
        tenant_record_id: Tenant namespace whose organization chart is reviewed.
        effective_on: Business day represented by the chart.
        known_at: System knowledge cutoff used to reconstruct it.

    Raises:
        SingleValuedFactError: One unit has two visible versions at the coordinate.
        OrganizationHierarchyError: Visible parent links contain a cycle.
    """
    scoped = [
        version
        for version in organization_versions
        if version.tenant_record_id == tenant_record_id
    ]
    unit_ids = {version.organization_unit_id for version in scoped}
    parents: dict[UUID, UUID | None] = {}
    for unit_id in unit_ids:
        visible = resolve_single_valued_fact(
            scoped,
            tenant_record_id=tenant_record_id,
            identity_of="organization_unit_id",
            identity_value=unit_id,
            effective_on=effective_on,
            known_at=known_at,
        )
        if visible is not None:
            parents[unit_id] = visible.parent_organization_unit_id

    for start in parents:
        seen: set[UUID] = set()
        current: UUID | None = start
        while current is not None:
            if current in seen:
                raise OrganizationHierarchyError(
                    "Visible organization parent links form a cycle in this tenant.",
                    next_action=(
                        "Close or correct the outdated parent link, then validate the organization chart again."
                    ),
                )
            seen.add(current)
            current = parents.get(current)
