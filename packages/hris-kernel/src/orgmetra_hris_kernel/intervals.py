"""Half-open effective-date and recorded-time intervals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from orgmetra_hris_kernel.errors import IntervalError


def _require_ordered(start: date | datetime, end: date | datetime | None) -> None:
    """Reject empty or reversed intervals before they become HR history."""
    if end is not None and end <= start:
        raise IntervalError(
            "Interval end must be strictly later than start.",
            next_action="Correct the start and end so the period contains at least one instant.",
        )


def _require_builtin_date(value: date, *, field_name: str) -> None:
    """Require exact built-in dates before business-time comparison."""
    if type(value) is not date:
        raise IntervalError(
            f"{field_name} must be a built-in date.",
            next_action="Convert the value to an exact Python date, then retry.",
        )


def _canonical_datetime(value: datetime, *, field_name: str) -> datetime:
    """Detach one exact datetime from caller-controlled timezone behavior."""
    if type(value) is not datetime:
        raise IntervalError(
            f"{field_name} must be a built-in datetime.",
            next_action="Convert the value to an exact Python datetime, then retry.",
        )
    try:
        offset = value.utcoffset()
    except Exception as exc:
        raise IntervalError(
            f"{field_name} must be timezone-aware.",
            next_action="Convert the knowledge cutoff to UTC before recording or querying.",
        ) from exc
    if offset is None:
        raise IntervalError(
            f"{field_name} must be timezone-aware.",
            next_action="Convert the knowledge cutoff to UTC before recording or querying.",
        )
    if type(offset) is not timedelta:
        raise IntervalError(
            f"{field_name} must resolve to a built-in timedelta offset.",
            next_action="Convert the timezone offset to an exact Python timedelta, then retry.",
        )
    try:
        fixed_zone = timezone.utc if offset == timedelta(0) else timezone(offset)
    except Exception as exc:
        raise IntervalError(
            f"{field_name} must resolve to a valid UTC offset.",
            next_action="Convert the knowledge cutoff to a valid fixed-offset datetime, then retry.",
        ) from exc
    return value.replace(tzinfo=fixed_zone)


@dataclass(frozen=True, slots=True)
class DateInterval:
    """Half-open effective date range: start inclusive, end exclusive."""

    start: date
    end: date | None = None

    def __init_subclass__(cls, **_kwargs: object) -> None:
        """Reject polymorphic interval objects at authoritative HRIS boundaries."""
        raise TypeError("DateInterval must not be subclassed.")

    def __post_init__(self) -> None:
        """Validate the effective period as soon as HR enters it."""
        _require_builtin_date(self.start, field_name="Date interval start")
        if self.end is not None:
            _require_builtin_date(self.end, field_name="Date interval end")
        _require_ordered(self.start, self.end)

    def contains(self, day: date) -> bool:
        """Return whether ``day`` is inside this effective period."""
        _require_builtin_date(day, field_name="Effective-date query coordinate")
        if day < self.start:
            return False
        return self.end is None or day < self.end

    def overlaps(self, other: DateInterval) -> bool:
        """Return whether two effective periods share at least one day."""
        if type(other) is not DateInterval:
            raise IntervalError(
                "Date interval comparison requires an exact DateInterval.",
                next_action="Build a governed DateInterval, then compare the effective periods.",
            )
        self_end = self.end
        other_end = other.end
        if self_end is not None and self_end <= other.start:
            return False
        if other_end is not None and other_end <= self.start:
            return False
        return True


@dataclass(frozen=True, slots=True)
class RecordedInterval:
    """Half-open system-recorded range: start inclusive, end exclusive."""

    start: datetime
    end: datetime | None = None

    def __init_subclass__(cls, **_kwargs: object) -> None:
        """Reject polymorphic interval objects at authoritative HRIS boundaries."""
        raise TypeError("RecordedInterval must not be subclassed.")

    def __post_init__(self) -> None:
        """Require canonical, timezone-aware knowledge bounds before reconstruction."""
        canonical_start = _canonical_datetime(self.start, field_name="Recorded interval start")
        canonical_end = (
            None
            if self.end is None
            else _canonical_datetime(self.end, field_name="Recorded interval end")
        )
        object.__setattr__(self, "start", canonical_start)
        object.__setattr__(self, "end", canonical_end)
        _require_ordered(canonical_start, canonical_end)

    def contains(self, instant: datetime) -> bool:
        """Return whether Orgmetra already knew this fact at ``instant``."""
        canonical_instant = _canonical_datetime(
            instant,
            field_name="Knowledge-cutoff query coordinate",
        )
        if canonical_instant < self.start:
            return False
        return self.end is None or canonical_instant < self.end

    def overlaps(self, other: RecordedInterval) -> bool:
        """Return whether two recorded periods share at least one instant."""
        if type(other) is not RecordedInterval:
            raise IntervalError(
                "Recorded interval comparison requires an exact RecordedInterval.",
                next_action="Build a governed RecordedInterval, then compare the system-time periods.",
            )
        if self.end is not None and self.end <= other.start:
            return False
        if other.end is not None and other.end <= self.start:
            return False
        return True
