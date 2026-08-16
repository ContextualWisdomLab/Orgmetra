"""Organization hierarchy validation must reject visible bitemporal cycles."""

from datetime import date
from uuid import UUID

import pytest

from orgmetra_hris_kernel import (
    OrganizationHierarchyError,
    OrganizationUnitVersion,
    validate_organization_hierarchy,
)

from .conftest import effective, recorded, utc

TENANT_ALPHA = UUID("00000000-0000-7000-8000-000000000001")
TENANT_BETA = UUID("00000000-0000-7000-8000-000000000002")
UNIT_A = UUID("50000000-0000-7000-8000-000000000001")
UNIT_B = UUID("50000000-0000-7000-8000-000000000002")
UNIT_C = UUID("50000000-0000-7000-8000-000000000003")


def _unit(
    *,
    version_id: str,
    unit_id: UUID,
    parent_id: UUID | None,
    tenant_id: UUID = TENANT_ALPHA,
    recorded_from_year: int = 2024,
) -> OrganizationUnitVersion:
    return OrganizationUnitVersion(
        tenant_record_id=tenant_id,
        organization_unit_id=unit_id,
        organization_unit_version_id=UUID(version_id),
        parent_organization_unit_id=parent_id,
        effective=effective(date(2024, 1, 1)),
        recorded=recorded(utc(recorded_from_year, 1, 1)),
    )


def test_rejects_indirect_cycle_visible_in_one_tenant() -> None:
    """A→B→C→A cannot become the authoritative organization hierarchy."""
    versions = [
        _unit(version_id="51000000-0000-7000-8000-000000000001", unit_id=UNIT_A, parent_id=UNIT_B),
        _unit(version_id="51000000-0000-7000-8000-000000000002", unit_id=UNIT_B, parent_id=UNIT_C),
        _unit(version_id="51000000-0000-7000-8000-000000000003", unit_id=UNIT_C, parent_id=UNIT_A),
    ]

    with pytest.raises(OrganizationHierarchyError, match="cycle"):
        validate_organization_hierarchy(
            versions,
            tenant_record_id=TENANT_ALPHA,
            effective_on=date(2024, 6, 1),
            known_at=utc(2024, 6, 1),
        )


def test_future_recorded_foreign_tenant_cycle_does_not_poison_current_hierarchy() -> None:
    """Only facts visible at the requested tenant/effective/knowledge coordinate count."""
    versions = [
        _unit(version_id="52000000-0000-7000-8000-000000000001", unit_id=UNIT_A, parent_id=None),
        _unit(version_id="52000000-0000-7000-8000-000000000002", unit_id=UNIT_B, parent_id=UNIT_A),
        _unit(
            version_id="52000000-0000-7000-8000-000000000003",
            unit_id=UNIT_A,
            parent_id=UNIT_B,
            recorded_from_year=2026,
        ),
        _unit(
            version_id="52000000-0000-7000-8000-000000000004",
            unit_id=UNIT_A,
            parent_id=UNIT_B,
            tenant_id=TENANT_BETA,
        ),
        _unit(
            version_id="52000000-0000-7000-8000-000000000005",
            unit_id=UNIT_B,
            parent_id=UNIT_A,
            tenant_id=TENANT_BETA,
        ),
    ]

    validate_organization_hierarchy(
        versions,
        tenant_record_id=TENANT_ALPHA,
        effective_on=date(2024, 6, 1),
        known_at=utc(2024, 6, 1),
    )
