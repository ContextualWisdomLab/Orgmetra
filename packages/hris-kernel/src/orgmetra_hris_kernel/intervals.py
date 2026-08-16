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


@dataclass(frozen=True, slots=True)
class DateInterval:
    """Half-open effective date range: start inclusive, end exclusive."""

    start: date
    end: date | None = None

    def __post_init__(self) -> None:
        """Validate the effective period as soon as HR enters it."""
        _require_ordered(self.start, self.end)

    def contains(self, day: date) -> bool:
        """Return whether `day` is inside this effective period."""
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
        """Require timezone-aware knowledge cutoffs so reconstructions stay honest."""
        if self.start.tzinfo is None or (self.end is not None and self.end.tzinfo is None):
            raise IntervalError(
                "Recorded timestamps must be timezone-aware.",
                next_action="Convert the knowledge cutoff to UTC before recording or querying.",
            )
        _require_ordered(self.start, self.end)

    def contains(self, instant: datetime) -> bool:
        """Return whether Orgmetra already knew this fact at `instant`."""
        if instant.tzinfo is None:
            raise IntervalError(
                "Recorded timestamps must be timezone-aware.",
                next_action="Convert the knowledge cutoff to UTC before recording or querying.",
            )
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
