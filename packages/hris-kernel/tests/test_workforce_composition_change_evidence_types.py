"""Regression coverage for exact workforce endpoint evidence types."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from orgmetra_hris_kernel.workforce import WorkforceCompositionSnapshot
from orgmetra_hris_kernel.workforce_change import WorkforceCompositionChangeSnapshot


class ForgedSnapshot(WorkforceCompositionSnapshot):
    """Snapshot subclass able to forge canonical endpoint evidence."""

    def canonical_json(self) -> str:
        """Return evidence unrelated to the inherited aggregate fields."""
        return '{"schema_version":"forged"}'

    def content_digest(self) -> str:
        """Return a forged digest unrelated to the inherited aggregate fields."""
        return "f" * 64


def snapshot(snapshot_type: type[WorkforceCompositionSnapshot], effective_on: date) -> WorkforceCompositionSnapshot:
    """Build one internally consistent endpoint using the requested runtime type."""
    return snapshot_type(
        tenant_record_id=UUID("11111111-1111-4111-8111-111111111111"),
        effective_on=effective_on,
        known_at=datetime(2026, 8, 21, 4, 40, tzinfo=timezone.utc),
        person_headcount=1,
        employment_count=1,
        staffed_assignment_count=1,
        staffed_fte=Decimal("1.0000"),
        unassigned_person_count=0,
        employment_status_counts=(("active", 1),),
    )


def test_rejects_opening_snapshot_subclass_that_can_forge_endpoint_evidence() -> None:
    """Opening evidence must be the exact validated workforce snapshot runtime type."""
    opening = snapshot(ForgedSnapshot, date(2026, 8, 1))
    closing = snapshot(WorkforceCompositionSnapshot, date(2026, 8, 21))

    with pytest.raises(TypeError, match="opening_snapshot"):
        WorkforceCompositionChangeSnapshot(opening, closing)


def test_rejects_closing_snapshot_subclass_that_can_forge_endpoint_evidence() -> None:
    """Closing evidence must be the exact validated workforce snapshot runtime type."""
    opening = snapshot(WorkforceCompositionSnapshot, date(2026, 8, 1))
    closing = snapshot(ForgedSnapshot, date(2026, 8, 21))

    with pytest.raises(TypeError, match="closing_snapshot"):
        WorkforceCompositionChangeSnapshot(opening, closing)
