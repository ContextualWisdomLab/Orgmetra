"""Regression coverage for organization-hierarchy temporal evidence integrity."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone, tzinfo
from uuid import UUID

import pytest

from orgmetra_hris_kernel.errors import IntervalError
from orgmetra_hris_kernel.organization import (
    OrganizationHierarchySnapshot,
    build_organization_hierarchy_snapshot,
)


class ForgedDate(date):
    """Date subclass able to forge canonical business-time evidence."""

    def isoformat(self) -> str:
        """Return a date different from the underlying hierarchy coordinate."""
        return "2099-12-31"


class ForgedDateTime(datetime):
    """Datetime subclass able to forge canonical recorded-time evidence."""

    def astimezone(self, tz=None):  # type: ignore[no-untyped-def]
        """Keep the hostile subclass alive across UTC normalization."""
        return self

    def isoformat(self, *args, **kwargs) -> str:  # type: ignore[no-untyped-def]
        """Return an instant different from the underlying knowledge cutoff."""
        return "2099-12-31T23:59:59+00:00"


class MutableOffset(tzinfo):
    """Timezone fixture whose offset can change after snapshot construction."""

    def __init__(self) -> None:
        self.hours = 1

    def utcoffset(self, dt: datetime | None) -> timedelta:
        """Return the currently configured offset."""
        return timedelta(hours=self.hours)

    def dst(self, dt: datetime | None) -> timedelta:
        """Return no daylight-saving offset."""
        return timedelta(0)


class UnknownOffset(tzinfo):
    """Timezone fixture whose UTC offset cannot be resolved."""

    def utcoffset(self, dt: datetime | None) -> None:
        """Return no offset to exercise fail-closed validation."""
        return None

    def dst(self, dt: datetime | None) -> None:
        """Return no daylight-saving offset."""
        return None


class ExplodingOffset(tzinfo):
    """Timezone fixture whose provider raises during offset resolution."""

    def utcoffset(self, dt: datetime | None) -> timedelta:
        """Raise an untrusted provider error."""
        raise RuntimeError("offset provider failed")

    def dst(self, dt: datetime | None) -> timedelta:
        """Return no daylight-saving offset when queried separately."""
        return timedelta(0)


TENANT = UUID("11111111-1111-4111-8111-111111111111")
KNOWN_AT = datetime(2026, 8, 21, 4, 35, tzinfo=timezone.utc)
EFFECTIVE_ON = date(2026, 8, 21)


def test_rejects_date_subclass_before_hierarchy_evidence_is_resolved_or_serialized() -> None:
    """Business-time evidence must not invoke caller-overridable date rendering."""
    forged = ForgedDate(2026, 8, 21)

    with pytest.raises(IntervalError, match="effective date"):
        OrganizationHierarchySnapshot(
            tenant_record_id=TENANT,
            effective_on=forged,
            known_at=KNOWN_AT,
            parent_links=(),
        )
    with pytest.raises(IntervalError, match="effective date"):
        build_organization_hierarchy_snapshot(
            [], tenant_record_id=TENANT, effective_on=forged, known_at=KNOWN_AT
        )


def test_rejects_datetime_subclass_before_hierarchy_evidence_is_resolved_or_serialized() -> None:
    """Recorded-time evidence must not invoke caller-overridable datetime rendering."""
    forged = ForgedDateTime(2026, 8, 21, 4, 35, tzinfo=timezone.utc)

    with pytest.raises(IntervalError, match="knowledge cutoff"):
        OrganizationHierarchySnapshot(
            tenant_record_id=TENANT,
            effective_on=EFFECTIVE_ON,
            known_at=forged,
            parent_links=(),
        )
    with pytest.raises(IntervalError, match="knowledge cutoff"):
        build_organization_hierarchy_snapshot(
            [], tenant_record_id=TENANT, effective_on=EFFECTIVE_ON, known_at=forged
        )


def test_snapshot_detaches_mutable_timezone_before_canonicalization() -> None:
    """One hierarchy snapshot must keep one recorded-time instant after timezone mutation."""
    zone = MutableOffset()
    snapshot = OrganizationHierarchySnapshot(
        tenant_record_id=TENANT,
        effective_on=EFFECTIVE_ON,
        known_at=datetime(2026, 8, 21, 4, 35, tzinfo=zone),
        parent_links=(),
    )
    before = snapshot.canonical_json(), snapshot.content_digest()
    zone.hours = 2
    assert (snapshot.canonical_json(), snapshot.content_digest()) == before


@pytest.mark.parametrize(
    "known_at",
    [
        datetime.min.replace(tzinfo=timezone(timedelta(hours=1))),
        datetime.max.replace(tzinfo=timezone(-timedelta(hours=1))),
        datetime(2026, 8, 21, 4, 35, tzinfo=UnknownOffset()),
        datetime(2026, 8, 21, 4, 35, tzinfo=ExplodingOffset()),
    ],
)
def test_rejects_unrepresentable_or_untrusted_recorded_time(known_at: datetime) -> None:
    """Normalize timezone-provider failures and UTC arithmetic overflow as IntervalError."""
    for build in (
        lambda: OrganizationHierarchySnapshot(
            tenant_record_id=TENANT,
            effective_on=EFFECTIVE_ON,
            known_at=known_at,
            parent_links=(),
        ),
        lambda: build_organization_hierarchy_snapshot(
            [], tenant_record_id=TENANT, effective_on=EFFECTIVE_ON, known_at=known_at
        ),
    ):
        with pytest.raises(IntervalError, match="knowledge cutoff"):
            build()


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("effective_on", ForgedDate(2026, 8, 21)),
        ("known_at", ForgedDateTime(2026, 8, 21, 4, 35, tzinfo=timezone.utc)),
        ("known_at", datetime(2026, 8, 21, 4, 35, tzinfo=timezone(timedelta(hours=1)))),
    ],
)
def test_canonicalization_rejects_low_level_temporal_reinjection(
    field_name: str, value: date | datetime
) -> None:
    """Keep canonical hierarchy evidence fail-closed after object-level corruption."""
    snapshot = OrganizationHierarchySnapshot(
        tenant_record_id=TENANT,
        effective_on=EFFECTIVE_ON,
        known_at=KNOWN_AT,
        parent_links=(),
    )
    object.__setattr__(snapshot, field_name, value)
    with pytest.raises(IntervalError, match="detached UTC"):
        snapshot.canonical_json()
