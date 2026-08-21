"""Regression coverage for organization-hierarchy temporal evidence integrity."""

from __future__ import annotations

from datetime import date, datetime, timezone
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
