"""Regression coverage for workforce snapshot temporal evidence integrity."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone, tzinfo
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


class _MutableOffsetTimezone(tzinfo):
    """Timezone provider whose offset can change after evidence construction."""

    def __init__(self, offset: timedelta) -> None:
        self.offset = offset

    def utcoffset(self, value: datetime | None) -> timedelta:
        """Return the currently configured offset."""
        return self.offset


class _UnknownOffsetTimezone(tzinfo):
    """Timezone provider whose offset is intentionally indeterminate."""

    def utcoffset(self, value: datetime | None) -> None:
        """Return no offset so the datetime is not a usable absolute instant."""
        return None


class _ExplodingOffsetTimezone(tzinfo):
    """Timezone provider that raises while its offset is requested."""

    def utcoffset(self, value: datetime | None) -> timedelta:
        """Raise to verify provider failures become interval errors."""
        raise RuntimeError("offset provider unavailable")


class _WrongOffsetTimezone(tzinfo):
    """Timezone provider that returns a non-timedelta offset."""

    def utcoffset(self, value: datetime | None) -> str:  # type: ignore[override]
        """Return an invalid offset type at the trust boundary."""
        return "not-a-timedelta"


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


def test_snapshot_freezes_mutable_timezone_before_canonical_export() -> None:
    """Changing a caller-owned timezone cannot change stored evidence or its digest."""
    provider = _MutableOffsetTimezone(timedelta(hours=2))
    evidence = snapshot(known_at=datetime(2026, 8, 21, 4, 30, tzinfo=provider))
    canonical = evidence.canonical_json()
    digest = evidence.content_digest()

    provider.offset = timedelta(hours=3)

    assert evidence.known_at == datetime(2026, 8, 21, 2, 30, tzinfo=timezone.utc)
    assert evidence.canonical_json() == canonical
    assert evidence.content_digest() == digest


@pytest.mark.parametrize(
    "known_at",
    [
        datetime.min.replace(tzinfo=timezone(timedelta(hours=1))),
        datetime.max.replace(tzinfo=timezone(-timedelta(hours=1))),
        datetime(2026, 8, 21, 4, 30, tzinfo=_UnknownOffsetTimezone()),
        datetime(2026, 8, 21, 4, 30, tzinfo=_ExplodingOffsetTimezone()),
        datetime(2026, 8, 21, 4, 30, tzinfo=_WrongOffsetTimezone()),
    ],
)
def test_rejects_unusable_recorded_time_provider(known_at: datetime) -> None:
    """Unknown, malformed, failing, and overflowing timezone providers fail closed."""
    with pytest.raises(IntervalError, match="knowledge cutoff"):
        snapshot(known_at=known_at)


def test_canonical_json_rejects_low_level_temporal_reinjection() -> None:
    """Even an unsafe post-construction mutation cannot invoke forged time renderers."""
    effective_time_evidence = snapshot()
    object.__setattr__(effective_time_evidence, "effective_on", ForgedDate(2026, 8, 21))
    with pytest.raises(IntervalError, match="not canonical"):
        effective_time_evidence.canonical_json()

    recorded_time_evidence = snapshot()
    object.__setattr__(
        recorded_time_evidence,
        "known_at",
        ForgedDateTime(2026, 8, 21, 4, 30, tzinfo=timezone.utc),
    )
    with pytest.raises(IntervalError, match="not canonical"):
        recorded_time_evidence.canonical_json()


def test_snapshot_detaches_mutable_status_count_containers() -> None:
    """Caller-owned list mutation cannot alter aggregate evidence after construction."""
    status_counts = [["active", 1]]
    evidence = snapshot(employment_status_counts=status_counts)
    canonical = evidence.canonical_json()
    digest = evidence.content_digest()

    status_counts[0][1] = 99
    status_counts.append(["leave", 0])

    assert evidence.employment_status_counts == (("active", 1),)
    assert evidence.canonical_json() == canonical
    assert evidence.content_digest() == digest


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
