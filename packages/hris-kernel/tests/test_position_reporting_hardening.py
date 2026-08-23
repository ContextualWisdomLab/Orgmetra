"""Adversarial runtime-type regressions for position-reporting evidence."""

from datetime import date, datetime, timezone, tzinfo
from uuid import UUID

import pytest

from orgmetra_hris_kernel.facts import PositionVersion
from orgmetra_hris_kernel.intervals import DateInterval, RecordedInterval
from orgmetra_hris_kernel.position_reporting import (
    PositionReportingHierarchyError,
    PositionReportingRelationship,
    build_position_reporting_snapshot,
)

TENANT = UUID("018f0d35-7b1a-7cc2-8d9c-111111111111")
POSITION_A = UUID("018f0d35-7b1a-7cc2-8d9c-aaaaaaaaaaa1")
VERSION_A = UUID("018f0d35-7b1a-7cc2-8d9c-ccccccccccc1")
EFFECTIVE_ON = date(2026, 8, 23)
KNOWN_AT = datetime(2026, 8, 23, 3, 30, tzinfo=timezone.utc)


def test_rejects_non_uuid_identity_before_relationship_validation() -> None:
    """Text that merely looks like an identifier cannot become governed UUID evidence."""
    with pytest.raises(PositionReportingHierarchyError, match="exact non-sentinel UUID"):
        PositionReportingRelationship(
            tenant_record_id="018f0d35-7b1a-7cc2-8d9c-111111111111",  # type: ignore[arg-type]
            position_reporting_relationship_id=UUID("018f0d35-7b1a-4cc2-8d9c-bbbbbbbbbbb1"),
            subordinate_position_record_id=POSITION_A,
            manager_position_record_id=UUID("018f0d35-7b1a-7cc2-8d9c-aaaaaaaaaaa2"),
            relationship_type_code="solid_line",
            effective=DateInterval(date(2026, 1, 1)),
            recorded=RecordedInterval(datetime(2026, 1, 1, tzinfo=timezone.utc)),
        )


def test_rejects_timezone_without_concrete_utc_offset() -> None:
    """A tzinfo object that cannot resolve one offset cannot drive bitemporal reconstruction."""

    class OffsetlessTimezone(tzinfo):
        """Timezone fixture whose offset contract deliberately resolves to None."""

        def utcoffset(self, dt: datetime | None) -> None:
            """Return no usable UTC offset."""
            return None

        def dst(self, dt: datetime | None) -> None:
            """Return no daylight-saving offset."""
            return None

        def tzname(self, dt: datetime | None) -> str:
            """Return a diagnostic fixture name."""
            return "offsetless"

    with pytest.raises(PositionReportingHierarchyError, match="concrete UTC offset"):
        build_position_reporting_snapshot(
            [],
            [],
            tenant_record_id=TENANT,
            effective_on=EFFECTIVE_ON,
            known_at=datetime(2026, 8, 23, 3, 30, tzinfo=OffsetlessTimezone()),
        )


def test_rejects_position_version_subclass_before_field_access() -> None:
    """A validation-bypassing PositionVersion subtype cannot supply endpoint evidence."""

    class ForgedPositionVersion(PositionVersion):
        """Caller-defined position subtype rejected by the exact-type boundary."""

    original = PositionVersion(
        tenant_record_id=TENANT,
        position_record_id=POSITION_A,
        position_record_version_id=VERSION_A,
        position_status_code="active",
        effective=DateInterval(date(2026, 1, 1)),
        recorded=RecordedInterval(datetime(2026, 1, 1, tzinfo=timezone.utc)),
    )
    forged = object.__new__(ForgedPositionVersion)
    for field_name in (
        "tenant_record_id",
        "position_record_id",
        "position_record_version_id",
        "position_status_code",
        "effective",
        "recorded",
    ):
        object.__setattr__(forged, field_name, getattr(original, field_name))

    with pytest.raises(PositionReportingHierarchyError, match="exact PositionVersion"):
        build_position_reporting_snapshot(
            [],
            [forged],
            tenant_record_id=TENANT,
            effective_on=EFFECTIVE_ON,
            known_at=KNOWN_AT,
        )