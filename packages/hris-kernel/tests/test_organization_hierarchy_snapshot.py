"""Organization hierarchy snapshots preserve one tenant's bitemporal reporting truth."""

from __future__ import annotations

from datetime import date, datetime
from hashlib import sha256
import json
from uuid import UUID

import pytest

from orgmetra_hris_kernel import (
    IntervalError,
    OrganizationHierarchyError,
    OrganizationHierarchySnapshot,
    OrganizationUnitVersion,
    SingleValuedFactError,
    build_organization_hierarchy_snapshot,
)

from .conftest import effective, recorded, utc

TENANT_ALPHA = UUID("00000000-0000-7000-8000-000000000001")
TENANT_BETA = UUID("00000000-0000-7000-8000-000000000002")
UNIT_ROOT = UUID("50000000-0000-7000-8000-000000000001")
UNIT_CHILD = UUID("50000000-0000-7000-8000-000000000002")
UNIT_DANGLING = UUID("50000000-0000-7000-8000-000000000003")
UNIT_UNKNOWN_PARENT = UUID("50000000-0000-7000-8000-000000000004")
UNIT_FUTURE = UUID("50000000-0000-7000-8000-000000000005")
UNIT_FOREIGN = UUID("50000000-0000-7000-8000-000000000006")


def _unit(
    *,
    version_id: str,
    unit_id: UUID,
    parent_id: UUID | None,
    tenant_id: UUID = TENANT_ALPHA,
    recorded_from_year: int = 2024,
) -> OrganizationUnitVersion:
    """Build one organization parent-link version for snapshot regressions."""
    return OrganizationUnitVersion(
        tenant_record_id=tenant_id,
        organization_unit_id=unit_id,
        organization_unit_version_id=UUID(version_id),
        parent_organization_unit_id=parent_id,
        effective=effective(date(2024, 1, 1)),
        recorded=recorded(utc(recorded_from_year, 1, 1)),
    )


def _visible_versions() -> list[OrganizationUnitVersion]:
    """Return visible, future, and foreign facts used by deterministic examples."""
    return [
        _unit(
            version_id="51000000-0000-7000-8000-000000000001",
            unit_id=UNIT_ROOT,
            parent_id=None,
        ),
        _unit(
            version_id="51000000-0000-7000-8000-000000000002",
            unit_id=UNIT_CHILD,
            parent_id=UNIT_ROOT,
        ),
        _unit(
            version_id="51000000-0000-7000-8000-000000000003",
            unit_id=UNIT_DANGLING,
            parent_id=UNIT_UNKNOWN_PARENT,
        ),
        _unit(
            version_id="51000000-0000-7000-8000-000000000004",
            unit_id=UNIT_FUTURE,
            parent_id=UNIT_ROOT,
            recorded_from_year=2026,
        ),
        _unit(
            version_id="51000000-0000-7000-8000-000000000005",
            unit_id=UNIT_FOREIGN,
            parent_id=None,
            tenant_id=TENANT_BETA,
        ),
    ]


def test_snapshot_exposes_only_visible_tenant_structure_with_deterministic_evidence() -> None:
    """One coordinate yields sorted opaque hierarchy links and stable SHA-256 evidence."""
    snapshot = build_organization_hierarchy_snapshot(
        _visible_versions(),
        tenant_record_id=TENANT_ALPHA,
        effective_on=date(2024, 6, 1),
        known_at=utc(2024, 6, 1),
    )

    assert snapshot.parent_links == (
        (UNIT_ROOT, None),
        (UNIT_CHILD, UNIT_ROOT),
        (UNIT_DANGLING, UNIT_UNKNOWN_PARENT),
    )
    assert snapshot.unit_count == 3
    assert snapshot.root_unit_count == 1
    assert snapshot.reporting_edge_count == 2

    expected_payload = {
        "effective_on": "2024-06-01",
        "known_at": "2024-06-01T00:00:00Z",
        "parent_links": [
            {
                "organization_unit_id": str(UNIT_ROOT),
                "parent_organization_unit_id": None,
            },
            {
                "organization_unit_id": str(UNIT_CHILD),
                "parent_organization_unit_id": str(UNIT_ROOT),
            },
            {
                "organization_unit_id": str(UNIT_DANGLING),
                "parent_organization_unit_id": str(UNIT_UNKNOWN_PARENT),
            },
        ],
        "reporting_edge_count": 2,
        "root_unit_count": 1,
        "schema_version": "orgmetra.organization_hierarchy_snapshot.v1",
        "tenant_record_id": str(TENANT_ALPHA),
        "unit_count": 3,
    }
    expected_json = json.dumps(expected_payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    assert snapshot.canonical_json() == expected_json
    assert snapshot.content_digest() == sha256(expected_json.encode("utf-8")).hexdigest()


def test_snapshot_is_independent_of_input_version_order() -> None:
    """Equivalent source ordering cannot change canonical hierarchy evidence."""
    forward = build_organization_hierarchy_snapshot(
        _visible_versions(),
        tenant_record_id=TENANT_ALPHA,
        effective_on=date(2024, 6, 1),
        known_at=utc(2024, 6, 1),
    )
    reverse = build_organization_hierarchy_snapshot(
        list(reversed(_visible_versions())),
        tenant_record_id=TENANT_ALPHA,
        effective_on=date(2024, 6, 1),
        known_at=utc(2024, 6, 1),
    )

    assert reverse == forward
    assert reverse.content_digest() == forward.content_digest()


def test_builder_rejects_naive_cutoff_even_when_no_units_are_visible() -> None:
    """An empty input cannot bypass the explicit system-time coordinate contract."""
    with pytest.raises(IntervalError, match="timezone-aware"):
        build_organization_hierarchy_snapshot(
            [],
            tenant_record_id=TENANT_ALPHA,
            effective_on=date(2024, 6, 1),
            known_at=datetime(2024, 6, 1),
        )


def test_direct_snapshot_rejects_naive_cutoff() -> None:
    """Forged snapshot values fail closed before deterministic evidence is exported."""
    with pytest.raises(IntervalError, match="timezone-aware"):
        OrganizationHierarchySnapshot(
            tenant_record_id=TENANT_ALPHA,
            effective_on=date(2024, 6, 1),
            known_at=datetime(2024, 6, 1),
            parent_links=(),
        )


def test_direct_snapshot_rejects_duplicate_unit_identity() -> None:
    """One snapshot cannot claim two simultaneous parent links for one durable unit."""
    with pytest.raises(SingleValuedFactError, match="duplicate organization unit"):
        OrganizationHierarchySnapshot(
            tenant_record_id=TENANT_ALPHA,
            effective_on=date(2024, 6, 1),
            known_at=utc(2024, 6, 1),
            parent_links=((UNIT_ROOT, None), (UNIT_ROOT, UNIT_CHILD)),
        )


def test_direct_snapshot_rejects_noncanonical_link_order() -> None:
    """Callers cannot create two byte-distinct snapshots from the same ordered facts."""
    with pytest.raises(SingleValuedFactError, match="canonical organization-unit order"):
        OrganizationHierarchySnapshot(
            tenant_record_id=TENANT_ALPHA,
            effective_on=date(2024, 6, 1),
            known_at=utc(2024, 6, 1),
            parent_links=((UNIT_CHILD, UNIT_ROOT), (UNIT_ROOT, None)),
        )


def test_direct_snapshot_rejects_visible_cycle() -> None:
    """Public snapshot construction preserves the same acyclic hierarchy invariant as validation."""
    with pytest.raises(OrganizationHierarchyError, match="cycle"):
        OrganizationHierarchySnapshot(
            tenant_record_id=TENANT_ALPHA,
            effective_on=date(2024, 6, 1),
            known_at=utc(2024, 6, 1),
            parent_links=((UNIT_ROOT, UNIT_CHILD), (UNIT_CHILD, UNIT_ROOT)),
        )


def test_builder_rejects_two_visible_parent_versions_for_one_unit() -> None:
    """Contradictory bitemporal parent truth cannot be flattened into a plausible snapshot."""
    versions = [
        _unit(
            version_id="52000000-0000-7000-8000-000000000001",
            unit_id=UNIT_ROOT,
            parent_id=None,
        ),
        _unit(
            version_id="52000000-0000-7000-8000-000000000002",
            unit_id=UNIT_ROOT,
            parent_id=UNIT_CHILD,
        ),
    ]

    with pytest.raises(SingleValuedFactError, match="more than one version"):
        build_organization_hierarchy_snapshot(
            versions,
            tenant_record_id=TENANT_ALPHA,
            effective_on=date(2024, 6, 1),
            known_at=utc(2024, 6, 1),
        )
