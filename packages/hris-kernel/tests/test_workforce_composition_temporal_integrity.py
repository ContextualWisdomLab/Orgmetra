"""Regression coverage for workforce snapshot temporal evidence integrity."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from orgmetra_hris_kernel.errors import IdentityScopeError, IntervalError
from orgmetra_hris_kernel.workforce import WorkforceCompositionSnapshot


class ForgedDate(date):
    """Date subclass able to forge canonical business-time evidence."""

    def isoformat(self) -> str:
        """Return a date different from the underlying effective date."""
        return "2099-12-31"


class ForgedDateTime(datetime):
    """Datetime subclass able to forge canonical recorded-time evidence."""

    def astimezone(self, tz=None):  # type: ignore[no-untyped-def]
        """Keep the hostile subclass alive across UTC normalization."""
        return self

    def isoformat(self, *args, **kwargs) -> str:  # type: ignore[no-untyped-def]
        """Return an instant different from the underlying knowledge cutoff."""
        return "2099-12-31T23:59:59+00:00"


def snapshot(**overrides: object) -> WorkforceCompositionSnapshot:
    """Build one internally consistent aggregate snapshot for boundary mutation tests."""
    values: dict[str, object] = {
        "tenant_record_id": UUID("11111111-1111-4111-8111-111111111111"),
        "effective_on": date(2026, 8, 21),
        "known_at": datetime(2026, 8, 21, 4, 30, tzinfo=timezone.utc),
        "person_headcount": 1,
        "employment_count": 1,
        "staffed_assignment_count": 1,
        "staffed_fte": Decimal("1.0000"),
        "unassigned_person_count": 0,
        "employment_status_counts": (("active", 1),),
    }
    values.update(overrides)
    return WorkforceCompositionSnapshot(**values)


def test_rejects_date_subclass_that_can_forge_effective_time_evidence() -> None:
    """Canonical snapshots must not invoke caller-overridable date rendering."""
    with pytest.raises(IntervalError, match="effective date"):
        snapshot(effective_on=ForgedDate(2026, 8, 21))


def test_rejects_datetime_subclass_that_can_forge_recorded_time_evidence() -> None:
    """Canonical snapshots must not invoke caller-overridable datetime rendering."""
    with pytest.raises(IntervalError, match="knowledge cutoff"):
        snapshot(known_at=ForgedDateTime(2026, 8, 21, 4, 30, tzinfo=timezone.utc))


@pytest.mark.parametrize(
    "tenant_record_id",
    [
        "not-a-tenant-uuid",
        UUID(int=0),
        UUID(int=(1 << 128) - 1),
    ],
)
def test_rejects_non_operational_tenant_identity(tenant_record_id: object) -> None:
    """Canonical snapshots must not publish malformed or sentinel tenant evidence."""
    with pytest.raises(IdentityScopeError, match="canonical operational UUID"):
        snapshot(tenant_record_id=tenant_record_id)
