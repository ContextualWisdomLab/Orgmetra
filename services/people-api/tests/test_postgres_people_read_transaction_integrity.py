"""Transaction-boundary regressions for governed PostgreSQL People reads."""

from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest

from orgmetra_people_api.postgres import PostgresPeopleReadPort

TENANT = UUID("0198a412-6000-7000-8000-000000000001")
OTHER_TENANT = UUID("0198a412-6000-7000-8000-000000000002")
PERSON = UUID("0198a412-6000-7000-8000-000000000010")
OTHER_PERSON = UUID("0198a412-6000-7000-8000-000000000011")
CONVERSION = UUID("0198a412-6000-7000-8000-000000000030")
CANDIDATE = UUID("0198a412-6000-7000-8000-000000000040")
EMPLOYMENT = UUID("0198a412-6000-7000-8000-000000000020")
EFFECTIVE_ON = date(2026, 9, 14)


class _Cursor:
    """Fail if SQL is reached without a proven transaction contract."""

    def __enter__(self) -> _Cursor:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def execute(self, sql: str, parameters: object | None = None) -> None:
        raise AssertionError(f"SQL executed without a guaranteed transaction: {sql!r} {parameters!r}")


class _Connection:
    """Expose a configurable autocommit contract and record cursor access."""

    def __init__(self, *, autocommit: object) -> None:
        self.autocommit = autocommit
        self.cursor_calls = 0

    def __enter__(self) -> _Connection:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def cursor(self) -> _Cursor:
        self.cursor_calls += 1
        return _Cursor()


class _RecordingCursor:
    """Capture the identity actually used after an external connection call."""

    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows
        self.executions: list[tuple[str, tuple[object, ...] | None]] = []

    def __enter__(self) -> _RecordingCursor:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def execute(self, sql: str, parameters: tuple[object, ...] | None = None) -> None:
        self.executions.append((sql, parameters))

    def fetchmany(self, size: int) -> list[tuple[object, ...]]:
        return self.rows[:size]


class _RecordingConnection:
    """Provide one ordinary non-autocommit connection for alias-mutation coverage."""

    autocommit = False

    def __init__(self, cursor: _RecordingCursor) -> None:
        self.cursor_instance = cursor

    def __enter__(self) -> _RecordingConnection:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def cursor(self) -> _RecordingCursor:
        return self.cursor_instance


@pytest.mark.parametrize("autocommit", [True, None, 0, "false"])
def test_people_read_rejects_unproven_transaction_before_cursor_access(
    autocommit: object,
) -> None:
    """Read-only mode and tenant context must never run outside one transaction."""
    connection = _Connection(autocommit=autocommit)
    port = PostgresPeopleReadPort(lambda: connection)

    with pytest.raises(RuntimeError, match="autocommit disabled"):
        port.read_worker(
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            effective_on=EFFECTIVE_ON,
        )

    assert connection.cursor_calls == 0


def test_people_read_detaches_request_identity_before_connection_factory() -> None:
    """External connection acquisition cannot retarget tenant or Person after validation."""
    tenant_record_id = UUID(int=TENANT.int)
    person_record_id = UUID(int=PERSON.int)
    expected_tenant = UUID(int=tenant_record_id.int)
    expected_person = UUID(int=person_record_id.int)
    cursor = _RecordingCursor(
        [
            (
                expected_tenant,
                CONVERSION,
                CANDIDATE,
                expected_person,
                EMPLOYMENT,
                "Ada Lovelace",
                "active",
            )
        ]
    )
    connection = _RecordingConnection(cursor)

    def connection_factory() -> _RecordingConnection:
        object.__setattr__(tenant_record_id, "int", OTHER_TENANT.int)
        object.__setattr__(person_record_id, "int", OTHER_PERSON.int)
        return connection

    record = PostgresPeopleReadPort(connection_factory).read_worker(
        tenant_record_id=tenant_record_id,
        person_record_id=person_record_id,
        effective_on=EFFECTIVE_ON,
    )

    assert record is not None
    assert record.tenant_record_id == expected_tenant
    assert record.person_record_id == expected_person
    assert cursor.executions[1][1] == (str(expected_tenant),)
    assert cursor.executions[2][1][:2] == (expected_tenant, expected_person)
