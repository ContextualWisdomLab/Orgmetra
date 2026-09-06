"""Failure-path coverage for position-reporting system-time normalization."""

from datetime import date, datetime, timedelta, timezone, tzinfo
from uuid import UUID

import pytest

from orgmetra_hris_kernel.position_reporting import (
    PositionReportingHierarchyError,
    build_position_reporting_snapshot,
)


class ExplodingTimezone(tzinfo):
    """Timezone fixture that refuses to resolve an offset."""

    def utcoffset(self, dt: datetime | None):
        """Raise to emulate a hostile or broken caller-owned timezone object."""
        raise RuntimeError("untrusted timezone code must not escape")

    def dst(self, dt: datetime | None):
        """Return no daylight-saving offset because it is not needed by the regression."""
        return None

    def tzname(self, dt: datetime | None) -> str:
        """Return a bounded diagnostic fixture name."""
        return "exploding"


def test_timezone_exception_is_normalized_to_governed_error() -> None:
    """Caller-owned timezone exceptions cannot escape the reporting boundary."""
    with pytest.raises(PositionReportingHierarchyError, match="could not be resolved safely"):
        build_position_reporting_snapshot(
            [],
            [],
            tenant_record_id=UUID("018f0d35-7b1a-7cc2-8d9c-111111111111"),
            effective_on=date(2026, 8, 23),
            known_at=datetime(2026, 8, 23, 3, 30, tzinfo=ExplodingTimezone()),
        )


@pytest.mark.parametrize(
    "known_at",
    (
        datetime.min.replace(tzinfo=timezone(timedelta(hours=23, minutes=59))),
        datetime.max.replace(tzinfo=timezone(timedelta(hours=-14))),
    ),
)
def test_timezone_normalization_overflow_is_normalized_to_governed_error(
    known_at: datetime,
) -> None:
    """An unrepresentable UTC conversion cannot escape as a raw arithmetic error."""
    with pytest.raises(PositionReportingHierarchyError, match="outside the supported datetime range"):
        build_position_reporting_snapshot(
            [],
            [],
            tenant_record_id=UUID("018f0d35-7b1a-7cc2-8d9c-111111111111"),
            effective_on=date(2026, 8, 23),
            known_at=known_at,
        )
