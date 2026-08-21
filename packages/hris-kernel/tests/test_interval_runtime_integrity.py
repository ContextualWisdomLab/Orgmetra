"""Adversarial runtime-type tests for authoritative bitemporal coordinates."""

from datetime import date, datetime, timedelta, timezone, tzinfo

import pytest

from orgmetra_hris_kernel import DateInterval, IntervalError, RecordedInterval


class _ForgedDate(date):
    """A caller-controlled date subtype that must not become business-time evidence."""


class _ForgedDateTime(datetime):
    """A caller-controlled datetime subtype that must not become system-time evidence."""


class _OffsetlessZone(tzinfo):
    """A non-null tzinfo object that still represents no usable UTC offset."""

    def utcoffset(self, _value: datetime | None) -> timedelta | None:
        """Return no offset so Python treats the timestamp as offset-naive."""
        return None

    def dst(self, _value: datetime | None) -> timedelta | None:
        """Return no daylight-saving adjustment."""
        return None

    def tzname(self, _value: datetime | None) -> str:
        """Return a stable diagnostic name for the test-only zone."""
        return "offsetless"


def test_date_interval_rejects_date_subclasses_in_stored_bounds() -> None:
    """Stored business-time bounds must be exact built-in dates, not polymorphic input."""
    forged = _ForgedDate(2026, 8, 22)

    with pytest.raises(IntervalError, match="built-in date"):
        DateInterval(start=forged)
    with pytest.raises(IntervalError, match="built-in date"):
        DateInterval(start=date(2026, 8, 1), end=forged)


def test_date_interval_rejects_date_subclasses_in_query_coordinate() -> None:
    """A caller-controlled query date cannot decide whether an HR fact is visible."""
    interval = DateInterval(start=date(2026, 8, 1), end=date(2026, 9, 1))

    with pytest.raises(IntervalError, match="built-in date"):
        interval.contains(_ForgedDate(2026, 8, 22))


def test_recorded_interval_rejects_datetime_subclasses_in_stored_bounds() -> None:
    """System-recorded bounds must be exact built-in datetimes before timezone checks."""
    forged = _ForgedDateTime(2026, 8, 22, 3, 0, tzinfo=timezone.utc)
    normal = datetime(2026, 8, 22, 4, 0, tzinfo=timezone.utc)

    with pytest.raises(IntervalError, match="built-in datetime"):
        RecordedInterval(start=forged)
    with pytest.raises(IntervalError, match="built-in datetime"):
        RecordedInterval(start=normal, end=forged)


def test_recorded_interval_rejects_datetime_subclasses_in_query_coordinate() -> None:
    """A caller-controlled knowledge-cutoff subtype cannot decide historical visibility."""
    interval = RecordedInterval(
        start=datetime(2026, 8, 22, 0, 0, tzinfo=timezone.utc),
        end=None,
    )

    with pytest.raises(IntervalError, match="built-in datetime"):
        interval.contains(_ForgedDateTime(2026, 8, 22, 3, 0, tzinfo=timezone.utc))


def test_recorded_interval_requires_a_real_utc_offset_not_only_tzinfo_presence() -> None:
    """A non-null tzinfo with no UTC offset is still naive system-time evidence."""
    offsetless = datetime(2026, 8, 22, 3, 0, tzinfo=_OffsetlessZone())

    with pytest.raises(IntervalError, match="timezone-aware"):
        RecordedInterval(start=offsetless)

    interval = RecordedInterval(
        start=datetime(2026, 8, 22, 0, 0, tzinfo=timezone.utc),
        end=None,
    )
    with pytest.raises(IntervalError, match="timezone-aware"):
        interval.contains(offsetless)
