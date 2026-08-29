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


class _ExplodingZone(tzinfo):
    """A hostile timezone implementation that raises during offset resolution."""

    def utcoffset(self, _value: datetime | None) -> timedelta | None:
        """Raise instead of returning a usable offset."""
        raise RuntimeError("hostile timezone")

    def dst(self, _value: datetime | None) -> timedelta | None:
        """Return no daylight-saving adjustment."""
        return None

    def tzname(self, _value: datetime | None) -> str:
        """Return a stable diagnostic name for the test-only zone."""
        return "exploding"


class _OneShotZone(tzinfo):
    """Return one valid offset, then fail if the trusted boundary keeps the object."""

    def __init__(self) -> None:
        """Track UTC-offset reads made by the interval boundary."""
        self.offset_reads = 0

    def utcoffset(self, _value: datetime | None) -> timedelta | None:
        """Return UTC once, then prove later comparisons re-enter hostile code."""
        self.offset_reads += 1
        if self.offset_reads > 1:
            raise RuntimeError("timezone reused after validation")
        return timedelta(0)

    def dst(self, _value: datetime | None) -> timedelta | None:
        """Return no daylight-saving adjustment."""
        return None

    def tzname(self, _value: datetime | None) -> str:
        """Return a stable diagnostic name for the test-only zone."""
        return "one_shot"


def test_interval_runtime_types_cannot_be_subclassed() -> None:
    """Domain facts must not receive interval objects with overridden visibility methods."""
    with pytest.raises(TypeError, match="must not be subclassed"):
        type("ForgedDateInterval", (DateInterval,), {})
    with pytest.raises(TypeError, match="must not be subclassed"):
        type("ForgedRecordedInterval", (RecordedInterval,), {})


def test_date_interval_rejects_date_subclasses_in_stored_bounds() -> None:
    """Stored business-time bounds must be exact built-in dates, not polymorphic input."""
    forged = _ForgedDate(2026, 8, 22)

    with pytest.raises(IntervalError, match="built-in date"):
        DateInterval(start=forged)
    with pytest.raises(IntervalError, match="built-in date"):
        DateInterval(start=date(2026, 8, 1), end=forged)


def test_date_interval_rejects_missing_stored_start() -> None:
    """A required effective-time start cannot be deferred to a later comparison."""
    with pytest.raises(IntervalError, match="built-in date"):
        DateInterval(start=None)  # type: ignore[arg-type]


def test_date_interval_rejects_date_subclasses_in_query_coordinate() -> None:
    """A caller-controlled query date cannot decide whether an HR fact is visible."""
    interval = DateInterval(start=date(2026, 8, 1), end=date(2026, 9, 1))

    with pytest.raises(IntervalError, match="built-in date"):
        interval.contains(_ForgedDate(2026, 8, 22))


def test_date_interval_rejects_non_interval_overlap_operand() -> None:
    """Effective-time overlap never delegates field access to an arbitrary object."""
    interval = DateInterval(start=date(2026, 8, 1), end=date(2026, 9, 1))

    with pytest.raises(IntervalError, match="exact DateInterval"):
        interval.overlaps(object())  # type: ignore[arg-type]


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


def test_recorded_interval_rejects_non_interval_overlap_operand() -> None:
    """System-time overlap never delegates field access to an arbitrary object."""
    interval = RecordedInterval(
        start=datetime(2026, 8, 22, 0, 0, tzinfo=timezone.utc),
        end=None,
    )

    with pytest.raises(IntervalError, match="exact RecordedInterval"):
        interval.overlaps(object())  # type: ignore[arg-type]


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


def test_recorded_interval_normalizes_hostile_timezone_failures() -> None:
    """Unexpected tzinfo execution failures become stable interval errors."""
    hostile = datetime(2026, 8, 22, 3, 0, tzinfo=_ExplodingZone())

    with pytest.raises(IntervalError, match="timezone-aware"):
        RecordedInterval(start=hostile)


def test_recorded_interval_detaches_validated_custom_timezone_code() -> None:
    """A timezone object cannot regain control during later stored/query comparisons."""
    stored_zone = _OneShotZone()
    interval = RecordedInterval(
        start=datetime(2026, 8, 22, 0, 0, tzinfo=stored_zone),
        end=None,
    )
    assert interval.start.tzinfo is timezone.utc
    assert interval.contains(datetime(2026, 8, 22, 1, 0, tzinfo=timezone.utc)) is True
    assert stored_zone.offset_reads == 1

    query_zone = _OneShotZone()
    assert interval.contains(datetime(2026, 8, 22, 2, 0, tzinfo=query_zone)) is True
    assert query_zone.offset_reads == 1


def test_recorded_interval_preserves_nonzero_fixed_offset_without_custom_code() -> None:
    """Canonicalization keeps the supplied offset while replacing timezone implementation code."""
    plus_nine = timezone(timedelta(hours=9))
    interval = RecordedInterval(
        start=datetime(2026, 8, 22, 9, 0, tzinfo=plus_nine),
        end=datetime(2026, 8, 22, 18, 0, tzinfo=plus_nine),
    )

    assert interval.start.utcoffset() == timedelta(hours=9)
    assert interval.end is not None
    assert interval.end.utcoffset() == timedelta(hours=9)
    assert interval.contains(datetime(2026, 8, 22, 12, 0, tzinfo=plus_nine)) is True
