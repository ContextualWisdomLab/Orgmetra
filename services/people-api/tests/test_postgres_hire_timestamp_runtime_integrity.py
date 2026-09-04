"""Runtime-integrity contracts for durable hire-decision timestamps."""

from datetime import datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo

from orgmetra_people_api.postgres_hire import _is_aware_datetime


class _ExecutableTimezone(tzinfo):
    """Record forbidden offset resolution at the People durable boundary."""

    def __init__(self) -> None:
        self.calls = 0

    def utcoffset(self, dt: datetime | None) -> timedelta:
        """Fail if validation executes caller-defined timezone behavior."""
        del dt
        self.calls += 1
        raise AssertionError("caller-defined timezone callback executed")


class _ExecutableDatetime(datetime):
    """Fail if validation executes behavior from a datetime subtype."""

    def utcoffset(self) -> timedelta:
        """Expose subtype execution if the exact-type gate is missing."""
        raise AssertionError("datetime subtype callback executed")


def test_hire_timestamp_rejects_custom_timezone_before_callback() -> None:
    """Exact datetime values cannot delegate offset validation to caller code."""
    provider = _ExecutableTimezone()
    value = datetime(2026, 8, 18, 0, 0, tzinfo=provider)

    assert _is_aware_datetime(value) is False
    assert provider.calls == 0


def test_hire_timestamp_rejects_datetime_subtype_before_callback() -> None:
    """Executable datetime subtypes are not durable selection-decision evidence."""
    value = _ExecutableDatetime(2026, 8, 18, 0, 0, tzinfo=timezone.utc)

    assert _is_aware_datetime(value) is False


def test_hire_timestamp_accepts_exact_standard_library_timezones() -> None:
    """Psycopg-compatible standard-library timezone materialization stays valid."""
    utc_value = datetime(2026, 8, 18, 0, 0, tzinfo=timezone.utc)
    seoul_value = datetime(2026, 8, 18, 9, 0, tzinfo=ZoneInfo("Asia/Seoul"))

    assert _is_aware_datetime(utc_value) is True
    assert _is_aware_datetime(seoul_value) is True
