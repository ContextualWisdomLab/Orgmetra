"""Half-open effective-date and recorded-time intervals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from orgmetra_hris_kernel.errors import IntervalError


def _require_ordered(start: date | datetime, end: date | datetime | None) -> None:
    """Reject empty or reversed intervals before they become HR history."""
    if end is not None and end <= start:
        raise IntervalError(
            "Interval end must be strictly later than start.",
            next_action="Correct the start and end so the period contains at least one instant.",
        )


def _require_builtin_date(value: date | None, *, field_name: str) -> None:
    """Require exact built-in dates before business-time comparison."""
    if value is not None and type(value) is not date:
        raise IntervalError(
            f"{field_name} must be a built-in date.",
            next_action="Convert the value to an exact Python date, then retry.",
        )


def _require_builtin_datetime(value: datetime | None, *, field_name: str) -> None:
    """Require exact built-in datetimes before system-time comparison."""
    if value is not None and type(value) is not datetime:
        raise IntervalError(
            f"{field_name} must be a built-in datetime.",
            next_action="Convert the value to an exact Python datetime, then retry.",
        )


def _require_timezone_aware(value: datetime, *, field_name: str) -> None:
    """Require a usable UTC offset instead of trusting non-null ``tzinfo`` alone."""
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


@dataclass(frozen=True, slots=True)
class DateInterval:
    """Half-open effective date range: start inclusive, end exclusive."""

    start: date
    end: date | None = None

    def __post_init__(self) -> None:
        """Validate the effective period as soon as HR enters it."""
        _require_builtin_date(self.start, field_name="Date interval start")
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

    def __post_init__(self) -> None:
        """Require canonical, timezone-aware knowledge bounds before reconstruction."""
        _require_builtin_datetime(self.start, field_name="Recorded interval start")
        _require_builtin_datetime(self.end, field_name="Recorded interval end")
        _require_timezone_aware(self.start, field_name="Recorded interval start")
        if self.end is not None:
            _require_timezone_aware(self.end, field_name="Recorded interval end")
        _require_ordered(self.start, self.end)

    def contains(self, instant: datetime) -> bool:
        """Return whether Orgmetra already knew this fact at ``instant``."""
        _require_builtin_datetime(instant, field_name="Knowledge-cutoff query coordinate")
        _require_timezone_aware(instant, field_name="Knowledge-cutoff query coordinate")
        if instant < self.start:
            return False
        return self.end is None or instant < self.end

    def overlaps(self, other: RecordedInterval) -> bool:
        """Return whether two recorded periods share at least one instant."""
        if self.end is not None and self.end <= other.start:
            return False
        if other.end is not None and other.end <= self.start:
            return False
        return True
