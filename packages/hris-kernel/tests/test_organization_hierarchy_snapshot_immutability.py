"""Organization hierarchy evidence remains immutable after construction."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from orgmetra_hris_kernel import OrganizationHierarchySnapshot

from .conftest import utc

TENANT_ALPHA = UUID("00000000-0000-7000-8000-000000000001")
UNIT_ROOT = UUID("50000000-0000-7000-8000-000000000001")
UNIT_CHILD = UUID("50000000-0000-7000-8000-000000000002")


def test_direct_snapshot_detaches_from_mutable_parent_link_input() -> None:
    """Mutating caller-owned link containers cannot rewrite sealed hierarchy evidence."""
    caller_links = [
        [UNIT_ROOT, None],
        [UNIT_CHILD, UNIT_ROOT],
    ]
    snapshot = OrganizationHierarchySnapshot(
        tenant_record_id=TENANT_ALPHA,
        effective_on=date(2024, 6, 1),
        known_at=utc(2024, 6, 1),
        parent_links=caller_links,  # type: ignore[arg-type]
    )
    original_json = snapshot.canonical_json()
    original_digest = snapshot.content_digest()

    caller_links[1][1] = None
    caller_links.append([UUID("50000000-0000-7000-8000-000000000003"), UNIT_ROOT])

    assert snapshot.parent_links == (
        (UNIT_ROOT, None),
        (UNIT_CHILD, UNIT_ROOT),
    )
    assert snapshot.canonical_json() == original_json
    assert snapshot.content_digest() == original_digest
