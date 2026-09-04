"""Runtime-integrity contracts for generic People durable scalar evidence."""

from datetime import datetime, timedelta, timezone, tzinfo
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from orgmetra_people_api.mutations import PeopleMutationIntegrityError
from orgmetra_people_api.postgres_mutations import (
    _is_aware_datetime,
    _is_operational_uuid,
    _replayed_record_id,
)
from test_people_mutations import employment_command
from test_postgres_people_mutations import employment_authorization


_MAX_UUID_INT = (1 << 128) - 1


class _ExecutableUUID(UUID):
    """Expose UUID attribute inspection performed before an exact-type gate."""

    def __getattribute__(self, name: str) -> object:
        """Fail when untrusted UUID evidence is inspected as if it were inert."""
        if name == "int":
            raise AssertionError("UUID subtype behavior executed before exact-type validation")
        return super().__getattribute__(name)


class _ExecutableTimezone(tzinfo):
    """Record forbidden offset resolution at the generic People durable boundary."""

    def __init__(self) -> None:
        """Initialize the callback counter without resolving an offset."""
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


class _ExecutableDigest(str):
    """Expose digest comparison performed before an exact-type gate."""

    def __new__(cls, value: str) -> _ExecutableDigest:
        """Create one tripwire text value without invoking comparison behavior."""
        instance = super().__new__(cls, value)
        instance.calls = 0
        return instance

    def __eq__(self, other: object) -> bool:
        """Fail if durable replay validation executes subtype equality."""
        del other
        self.calls += 1
        raise AssertionError("digest subtype equality executed before exact-type validation")

    def __ne__(self, other: object) -> bool:
        """Fail if durable replay validation executes subtype inequality."""
        del other
        self.calls += 1
        raise AssertionError("digest subtype inequality executed before exact-type validation")


class _ReplayCursor:
    """Return one scripted exact built-in idempotency row."""

    def __init__(self, row: tuple[object, object]) -> None:
        """Store the row without inspecting its scalar values."""
        self.row = row

    def execute(self, sql: str, parameters: tuple[object, ...] | None = None) -> None:
        """Accept the two replay lookup statements without side effects."""
        del sql, parameters

    def fetchmany(self, size: int) -> list[tuple[object, object]]:
        """Return the scripted exact row within the requested bound."""
        return [self.row][:size]


def test_generic_durable_uuid_rejects_subtype_before_identity_inspection() -> None:
    """DB-returned UUID subtypes fail without executing subtype behavior."""
    value = _ExecutableUUID("0198a412-7100-7000-8000-000000000061")

    assert _is_operational_uuid(value) is False


def test_generic_durable_uuid_accepts_only_operational_exact_uuid_values() -> None:
    """Exact Psycopg-compatible UUIDs remain valid except reserved sentinels."""
    assert _is_operational_uuid(UUID("0198a412-7100-7000-8000-000000000061")) is True
    assert _is_operational_uuid(UUID(int=0)) is False
    assert _is_operational_uuid(UUID(int=_MAX_UUID_INT)) is False


def test_generic_timestamp_rejects_custom_timezone_before_callback() -> None:
    """Exact datetime values cannot delegate offset validation to caller code."""
    provider = _ExecutableTimezone()
    value = datetime(2026, 9, 5, 0, 0, tzinfo=provider)

    assert _is_aware_datetime(value) is False
    assert provider.calls == 0


def test_generic_timestamp_rejects_datetime_subtype_before_callback() -> None:
    """Executable datetime subtypes are not durable generic People evidence."""
    value = _ExecutableDatetime(2026, 9, 5, 0, 0, tzinfo=timezone.utc)

    assert _is_aware_datetime(value) is False


def test_generic_timestamp_accepts_exact_standard_library_timezones() -> None:
    """Psycopg-compatible standard-library timezone materialization stays valid."""
    utc_value = datetime(2026, 9, 5, 0, 0, tzinfo=timezone.utc)
    seoul_value = datetime(2026, 9, 5, 9, 0, tzinfo=ZoneInfo("Asia/Seoul"))

    assert _is_aware_datetime(utc_value) is True
    assert _is_aware_datetime(seoul_value) is True


def test_generic_replay_digest_rejects_subtype_before_comparison() -> None:
    """Persisted digest subtypes fail without executing equality behavior."""
    command = employment_command()
    digest = _ExecutableDigest("persisted-untrusted-digest")
    cursor: Any = _ReplayCursor((command.employment_record_id, digest))

    try:
        _replayed_record_id(
            cursor,
            command=command,
            authorization=employment_authorization(),
        )
    except PeopleMutationIntegrityError as error:
        assert str(error) == "idempotency row is invalid"
    else:
        raise AssertionError("digest subtype was not rejected")

    assert digest.calls == 0
