"""Interval contract tests for half-open effective and recorded time."""

from datetime import date, datetime, timezone

import pytest

from orgmetra_hris_kernel import DateInterval, IntervalError, RecordedInterval


def test_date_interval_rejects_empty_or_reversed_range() -> None:
    """Operators must correct the dates; a zero-length employment period is not stored."""
    with pytest.raises(IntervalError, match="strictly later"):
        DateInterval(start=date(2024, 3, 1), end=date(2024, 3, 1))
    with pytest.raises(IntervalError, match="strictly later"):
        DateInterval(start=date(2024, 4, 1), end=date(2024, 3, 1))


def test_date_interval_contains_start_and_excludes_end() -> None:
    """Half-open ranges let HR query the first day without double-counting the last day."""
    interval = DateInterval(start=date(2024, 3, 1), end=date(2024, 6, 1))
    assert interval.contains(date(2024, 3, 1)) is True
    assert interval.contains(date(2024, 5, 31)) is True
    assert interval.contains(date(2024, 6, 1)) is False
    assert interval.contains(date(2024, 2, 29)) is False


def test_open_ended_date_interval_contains_later_days() -> None:
    """An open employment remains visible until HR records an end date."""
    interval = DateInterval(start=date(2024, 3, 1), end=None)
    assert interval.contains(date(2026, 8, 16)) is True


def test_date_intervals_overlap_when_ranges_share_a_day() -> None:
    """Overlapping versions of one employment must be rejected before save."""
    first = DateInterval(start=date(2024, 3, 1), end=date(2024, 6, 1))
    second = DateInterval(start=date(2024, 5, 15), end=date(2024, 9, 1))
    adjacent = DateInterval(start=date(2024, 6, 1), end=date(2024, 9, 1))
    assert first.overlaps(second) is True
    assert first.overlaps(adjacent) is False
    assert adjacent.overlaps(first) is False


def test_recorded_interval_requires_timezone_aware_instants() -> None:
    """Naive timestamps hide the knowledge cutoff; convert to UTC before recording."""
    naive = datetime(2024, 6, 15, 12, 0, 0)
    aware = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(IntervalError, match="timezone-aware"):
        RecordedInterval(start=naive, end=None)
    with pytest.raises(IntervalError, match="timezone-aware"):
        RecordedInterval(start=aware, end=naive)


def test_recorded_interval_contains_and_overlaps() -> None:
    """A later correction must not appear in an earlier knowledge cutoff."""
    recorded = RecordedInterval(
        start=datetime(2024, 3, 1, tzinfo=timezone.utc),
        end=datetime(2024, 6, 15, tzinfo=timezone.utc),
    )
    later = RecordedInterval(
        start=datetime(2024, 6, 15, tzinfo=timezone.utc),
        end=None,
    )
    overlapping = RecordedInterval(
        start=datetime(2024, 6, 1, tzinfo=timezone.utc),
        end=datetime(2024, 7, 1, tzinfo=timezone.utc),
    )
    assert recorded.contains(datetime(2024, 6, 14, 23, 0, tzinfo=timezone.utc)) is True
    assert recorded.contains(datetime(2024, 6, 15, tzinfo=timezone.utc)) is False
    assert recorded.contains(datetime(2024, 2, 1, tzinfo=timezone.utc)) is False
    assert later.overlaps(recorded) is False
    assert recorded.overlaps(later) is False
    assert recorded.overlaps(overlapping) is True
    assert overlapping.overlaps(recorded) is True
    with pytest.raises(IntervalError, match="timezone-aware"):
        recorded.contains(datetime(2024, 6, 14, 23, 0, 0))
    with pytest.raises(IntervalError, match="strictly later"):
        RecordedInterval(
            start=datetime(2024, 6, 15, tzinfo=timezone.utc),
            end=datetime(2024, 6, 15, tzinfo=timezone.utc),
        )
