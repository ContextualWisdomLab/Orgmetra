"""Retroactive correction tests: close recorded time, then insert a replacement."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

import pytest

from orgmetra_hris_kernel import CorrectionError, RecordedInterval, close_recorded_interval

from .conftest import utc


@dataclass(frozen=True, slots=True)
class _ForeignRecordedFact:
    """Caller-owned dataclass that must never be blessed as an HRIS kernel fact."""

    recorded: RecordedInterval
    shadow_status_code: str = "approved"


class _ForgedDateTime(datetime):
    """Datetime subtype that lies about ordering to bypass chronology checks."""

    def __le__(self, other: object) -> bool:
        """Pretend every candidate close time is later than the recorded start."""
        return False


def test_close_recorded_interval_keeps_business_columns(
    jordan_active_employment,
) -> None:
    """HR closes what the system previously knew; it does not rewrite status in place."""
    closed = close_recorded_interval(
        jordan_active_employment,
        recorded_to=utc(2024, 6, 15, 9),
    )
    assert closed.employment_status_code == "active"
    assert closed.recorded.end == utc(2024, 6, 15, 9)
    assert closed.employment_record_id == jordan_active_employment.employment_record_id
    assert closed.employment_record_version_id == (
        jordan_active_employment.employment_record_version_id
    )


def test_close_recorded_interval_rejects_already_closed_or_invalid_end(
    jordan_active_employment,
) -> None:
    """Ask for a new version row instead of mutating a closed fact."""
    closed = close_recorded_interval(
        jordan_active_employment,
        recorded_to=utc(2024, 6, 15, 9),
    )
    with pytest.raises(CorrectionError, match="already closed"):
        close_recorded_interval(closed, recorded_to=utc(2024, 7, 1))
    with pytest.raises(CorrectionError, match="strictly later"):
        close_recorded_interval(
            jordan_active_employment,
            recorded_to=utc(2024, 3, 1, 15),
        )


def test_close_recorded_interval_rejects_unknown_fact_shape() -> None:
    """Only kernel facts with a recorded interval can be closed."""
    with pytest.raises(CorrectionError, match="recorded"):
        close_recorded_interval(
            UUID("10000000-0000-7000-8000-000000000999"),
            recorded_to=utc(2024, 6, 15),
        )
    with pytest.raises(CorrectionError, match="recorded"):
        close_recorded_interval(
            date(2024, 6, 15),
            recorded_to=utc(2024, 6, 16),
        )


def test_close_recorded_interval_rejects_foreign_dataclass_with_recorded_shape() -> None:
    """A caller-owned dataclass cannot impersonate an authoritative kernel fact."""
    foreign_fact = _ForeignRecordedFact(
        recorded=RecordedInterval(start=utc(2024, 3, 1, 15)),
    )

    with pytest.raises(CorrectionError, match="kernel fact"):
        close_recorded_interval(
            foreign_fact,
            recorded_to=utc(2024, 6, 15, 9),
        )


def test_close_recorded_interval_rejects_datetime_subclass_before_ordering(
    jordan_active_employment,
) -> None:
    """Caller polymorphism cannot forge a reversed system-recorded correction."""
    forged_earlier_end = _ForgedDateTime(
        2024,
        3,
        1,
        14,
        tzinfo=timezone.utc,
    )

    with pytest.raises(CorrectionError, match="built-in datetime"):
        close_recorded_interval(
            jordan_active_employment,
            recorded_to=forged_earlier_end,
        )
