"""Executable-capability and retained-input integrity regressions for PostgreSQL Employment-history reads."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_people_api.postgres_employment_history import PostgresEmploymentHistoryReadPort

TENANT_ID = UUID("0198a415-9ab1-7000-8000-000000000001")
PERSON_ID = UUID("0198a415-9ab1-7000-8000-000000000002")
KNOWN_AT = datetime(2026, 9, 14, tzinfo=timezone.utc)


class _Cursor:
    """Provide the minimal DB-API surface for an empty Employment-history read."""

    def __enter__(self) -> _Cursor:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def execute(self, sql: str, parameters: object | None = None) -> None:
        """Accept parameterized statements without side effects."""
        del sql, parameters

    def fetchall(self) -> list[tuple[object, ...]]:
        """Return no Employment-history rows."""
        return []


class _Connection:
    """Provide one deterministic non-autocommit connection context."""

    autocommit = False

    def __enter__(self) -> _Connection:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def cursor(self) -> _Cursor:
        """Return the deterministic read cursor."""
        return _Cursor()


def test_validated_connection_factory_cannot_be_replaced_after_construction() -> None:
    """The capability accepted at construction must remain the capability used by the read."""
    accepted_calls = 0
    replacement_calls = 0

    def accepted_factory() -> _Connection:
        nonlocal accepted_calls
        accepted_calls += 1
        return _Connection()

    def replacement_factory() -> _Connection:
        nonlocal replacement_calls
        replacement_calls += 1
        raise AssertionError("replacement capability reached Employment-history persistence")

    port = PostgresEmploymentHistoryReadPort(accepted_factory)

    with pytest.raises(AttributeError):
        object.__setattr__(port, "connection_factory", replacement_factory)

    assert port.connection_factory is accepted_factory
    assert port.read_employment_history(
        tenant_record_id=TENANT_ID,
        person_record_id=PERSON_ID,
        known_at=KNOWN_AT,
    ) == ()
    assert accepted_calls == 1
    assert replacement_calls == 0


def test_forged_uuid_payload_fails_before_executable_equality_or_db_access() -> None:
    """An exact UUID wrapper must not make a forged retained payload executable."""
    connection_calls = 0

    class _ExplosivePayload:
        def __eq__(self, other: object) -> bool:
            raise AssertionError(f"forged UUID payload compared with {other!r}")

    forged_tenant_id = UUID("0198a415-9ab1-7000-8000-000000000011")
    object.__setattr__(forged_tenant_id, "int", _ExplosivePayload())

    def connection_factory() -> _Connection:
        nonlocal connection_calls
        connection_calls += 1
        return _Connection()

    port = PostgresEmploymentHistoryReadPort(connection_factory)
    with pytest.raises(ValueError, match="tenant_record_id must be an operational UUID"):
        port.read_employment_history(
            tenant_record_id=forged_tenant_id,
            person_record_id=PERSON_ID,
            known_at=KNOWN_AT,
        )
    assert connection_calls == 0


def test_validated_request_uuid_aliases_are_detached_before_connection_acquisition() -> None:
    """A dependency cannot retarget the query by mutating caller-owned UUID aliases after validation."""
    requested_tenant_id = UUID("0198a415-9ab1-7000-8000-000000000021")
    requested_person_id = UUID("0198a415-9ab1-7000-8000-000000000022")
    original_tenant_id = UUID(int=requested_tenant_id.int)
    original_person_id = UUID(int=requested_person_id.int)
    replacement_tenant_id = UUID("0198a415-9ab1-7000-8000-000000000031")
    replacement_person_id = UUID("0198a415-9ab1-7000-8000-000000000032")
    executions: list[tuple[str, object | None]] = []

    class _RecordingCursor(_Cursor):
        def execute(self, sql: str, parameters: object | None = None) -> None:
            executions.append((sql, parameters))

    class _RecordingConnection(_Connection):
        def cursor(self) -> _RecordingCursor:
            return _RecordingCursor()

    def mutating_factory() -> _RecordingConnection:
        object.__setattr__(requested_tenant_id, "int", replacement_tenant_id.int)
        object.__setattr__(requested_person_id, "int", replacement_person_id.int)
        return _RecordingConnection()

    port = PostgresEmploymentHistoryReadPort(mutating_factory)
    assert port.read_employment_history(
        tenant_record_id=requested_tenant_id,
        person_record_id=requested_person_id,
        known_at=KNOWN_AT,
    ) == ()

    assert executions[1][1] == (str(original_tenant_id),)
    query_parameters = executions[2][1]
    assert type(query_parameters) is tuple
    assert query_parameters[:2] == (original_tenant_id, original_person_id)
