"""Regression contract for the PostgreSQL Assignment-history read adapter."""

from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import date, datetime, timedelta, timezone, tzinfo
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest

from orgmetra_people_api.assignment_history import AssignmentHistoryIntegrityError
from orgmetra_people_api.postgres_assignment_history import PostgresAssignmentHistoryReadPort


TENANT_ID = UUID("018d51d2-9ab1-7ac0-8eb1-0a5dc487b9c1")
PERSON_ID = UUID("018d51d2-9ab1-7ac0-8eb1-0a5dc487b9c2")
ASSIGNMENT_ID = UUID("018d51d2-9ab1-7ac0-8eb1-0a5dc487b9c3")
EMPLOYMENT_ID = UUID("018d51d2-9ab1-7ac0-8eb1-0a5dc487b9c4")
POSITION_ID = UUID("018d51d2-9ab1-7ac0-8eb1-0a5dc487b9c5")
KNOWN_AT = datetime(2026, 8, 29, 0, 0, tzinfo=timezone.utc)


def assignment_row(
    *,
    tenant_record_id: object = TENANT_ID,
    person_record_id: object = PERSON_ID,
    allocation_ratio: object = Decimal("0.6000"),
    recorded_from: object = datetime(2026, 8, 1, 0, 0),
    recorded_to: object = None,
) -> tuple[object, ...]:
    """Return one default DB row as projected by the governed SQL query."""
    return (
        tenant_record_id,
        ASSIGNMENT_ID,
        EMPLOYMENT_ID,
        person_record_id,
        POSITION_ID,
        allocation_ratio,
        date(2026, 8, 1),
        None,
        recorded_from,
        recorded_to,
    )


class FakeCursor(AbstractContextManager["FakeCursor"]):
    """Minimal DB-API cursor that records SQL and returns configured rows."""

    def __init__(self, rows: object) -> None:
        self.rows = rows
        self.executions: list[tuple[str, object | None]] = []

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def execute(self, statement: str, parameters: object | None = None) -> None:
        self.executions.append((statement, parameters))

    def fetchall(self) -> object:
        return self.rows


class FakeConnection(AbstractContextManager["FakeConnection"]):
    """Minimal connection exposing one stable cursor."""

    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return self._cursor


class ConnectionFactory:
    """Count connection acquisition so invalid request inputs can prove zero DB access."""

    def __init__(self, rows: object) -> None:
        self.calls = 0
        self.cursor = FakeCursor(rows)

    def __call__(self) -> FakeConnection:
        self.calls += 1
        return FakeConnection(self.cursor)


class ZeroOffsetProvider(tzinfo):
    """Caller-controlled timezone provider that must not cross the DB trust boundary."""

    def utcoffset(self, dt: datetime | None) -> timedelta:
        return timedelta(0)

    def dst(self, dt: datetime | None) -> timedelta:
        return timedelta(0)


@pytest.mark.parametrize("invalid_factory", [None, 7, "connection"])
def test_rejects_non_callable_connection_factory(invalid_factory: object) -> None:
    with pytest.raises(TypeError, match="connection_factory must be callable"):
        PostgresAssignmentHistoryReadPort(invalid_factory)  # type: ignore[arg-type]


def test_read_is_tenant_scoped_read_only_half_open_and_returns_canonical_rows() -> None:
    factory = ConnectionFactory(
        [
            assignment_row(
                recorded_to=datetime(2026, 9, 1, 0, 0),
            )
        ]
    )
    port = PostgresAssignmentHistoryReadPort(factory)

    records = port.read_assignment_history(
        tenant_record_id=TENANT_ID,
        person_record_id=PERSON_ID,
        known_at=KNOWN_AT,
    )

    assert len(records) == 1
    record = records[0]
    assert record.tenant_record_id == TENANT_ID
    assert record.person_record_id == PERSON_ID
    assert record.assignment_record_id == ASSIGNMENT_ID
    assert record.recorded_from == datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
    assert record.recorded_to == datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc)
    assert record.allocation_ratio == Decimal("0.6000")

    assert factory.calls == 1
    assert len(factory.cursor.executions) == 3
    transaction_sql, transaction_parameters = factory.cursor.executions[0]
    tenant_sql, tenant_parameters = factory.cursor.executions[1]
    history_sql, history_parameters = factory.cursor.executions[2]
    assert transaction_sql == "SET TRANSACTION ISOLATION LEVEL READ COMMITTED, READ ONLY"
    assert transaction_parameters is None
    assert "pg_catalog.set_config('orgmetra.tenant_record_id', %s, true)" in tenant_sql
    assert tenant_parameters == (str(TENANT_ID),)
    assert "FROM public.assignment_record AS assignment" in history_sql
    assert "assignment.tenant_record_id = %s" in history_sql
    assert "assignment.person_record_id = %s" in history_sql
    assert "assignment.recorded_from <= %s" in history_sql
    assert "%s < assignment.recorded_to" in history_sql
    assert "AT TIME ZONE 'UTC'" in history_sql
    assert "ORDER BY assignment.effective_from, assignment.assignment_record_id" in history_sql
    assert "SELECT *" not in history_sql.upper()
    assert history_parameters == (TENANT_ID, PERSON_ID, KNOWN_AT, KNOWN_AT)


def test_empty_database_result_returns_immutable_empty_tuple() -> None:
    factory = ConnectionFactory([])
    port = PostgresAssignmentHistoryReadPort(factory)

    assert port.read_assignment_history(
        tenant_record_id=TENANT_ID,
        person_record_id=PERSON_ID,
        known_at=KNOWN_AT,
    ) == ()


@pytest.mark.parametrize(
    ("tenant_record_id", "person_record_id", "known_at", "message"),
    [
        (UUID(int=0), PERSON_ID, KNOWN_AT, "tenant_record_id must be an operational UUID"),
        (TENANT_ID, UUID(int=(1 << 128) - 1), KNOWN_AT, "person_record_id must be an operational UUID"),
        (TENANT_ID, PERSON_ID, "2026-08-29", "known_at must be a timezone-aware UTC datetime"),
        (TENANT_ID, PERSON_ID, datetime(2026, 8, 29), "known_at must be a timezone-aware UTC datetime"),
        (
            TENANT_ID,
            PERSON_ID,
            datetime(2026, 8, 29, tzinfo=timezone(timedelta(hours=9))),
            "known_at must be a timezone-aware UTC datetime",
        ),
        (
            TENANT_ID,
            PERSON_ID,
            datetime(2026, 8, 29, tzinfo=ZeroOffsetProvider()),
            "known_at must be a timezone-aware UTC datetime",
        ),
    ],
)
def test_invalid_request_identity_or_time_fails_before_database_access(
    tenant_record_id: object,
    person_record_id: object,
    known_at: object,
    message: str,
) -> None:
    factory = ConnectionFactory([])
    port = PostgresAssignmentHistoryReadPort(factory)

    with pytest.raises(ValueError, match=message):
        port.read_assignment_history(  # type: ignore[arg-type]
            tenant_record_id=tenant_record_id,
            person_record_id=person_record_id,
            known_at=known_at,
        )

    assert factory.calls == 0


def test_rejects_non_list_fetchall_result() -> None:
    factory = ConnectionFactory((assignment_row(),))
    port = PostgresAssignmentHistoryReadPort(factory)

    with pytest.raises(AssignmentHistoryIntegrityError, match="immutable row list"):
        port.read_assignment_history(
            tenant_record_id=TENANT_ID,
            person_record_id=PERSON_ID,
            known_at=KNOWN_AT,
        )


@pytest.mark.parametrize("row", [[1] * 10, (1, 2)])
def test_rejects_unsupported_row_container_or_shape(row: object) -> None:
    factory = ConnectionFactory([row])
    port = PostgresAssignmentHistoryReadPort(factory)

    with pytest.raises(AssignmentHistoryIntegrityError, match="row has an invalid shape"):
        port.read_assignment_history(
            tenant_record_id=TENANT_ID,
            person_record_id=PERSON_ID,
            known_at=KNOWN_AT,
        )


@pytest.mark.parametrize(
    ("recorded_from", "recorded_to"),
    [
        ("2026-08-01", None),
        (datetime(2026, 8, 1, tzinfo=timezone.utc), None),
        (datetime(2026, 8, 1), "2026-09-01"),
        (datetime(2026, 8, 1), datetime(2026, 9, 1, tzinfo=timezone.utc)),
    ],
)
def test_rejects_noncanonical_database_timestamp_projection(
    recorded_from: object,
    recorded_to: object,
) -> None:
    factory = ConnectionFactory([assignment_row(recorded_from=recorded_from, recorded_to=recorded_to)])
    port = PostgresAssignmentHistoryReadPort(factory)

    with pytest.raises(AssignmentHistoryIntegrityError, match="database recorded time must be a naive UTC projection"):
        port.read_assignment_history(
            tenant_record_id=TENANT_ID,
            person_record_id=PERSON_ID,
            known_at=KNOWN_AT,
        )


def test_rejects_database_row_that_fails_assignment_record_integrity() -> None:
    factory = ConnectionFactory([assignment_row(allocation_ratio=Decimal("NaN"))])
    port = PostgresAssignmentHistoryReadPort(factory)

    with pytest.raises(AssignmentHistoryIntegrityError, match="database assignment-history row failed integrity"):
        port.read_assignment_history(
            tenant_record_id=TENANT_ID,
            person_record_id=PERSON_ID,
            known_at=KNOWN_AT,
        )


@pytest.mark.parametrize(
    "row",
    [
        assignment_row(tenant_record_id=UUID("018d51d2-9ab1-7ac0-8eb1-0a5dc487b9d1")),
        assignment_row(person_record_id=UUID("018d51d2-9ab1-7ac0-8eb1-0a5dc487b9d2")),
    ],
)
def test_rejects_row_outside_requested_tenant_or_person(row: tuple[object, ...]) -> None:
    factory = ConnectionFactory([row])
    port = PostgresAssignmentHistoryReadPort(factory)

    with pytest.raises(AssignmentHistoryIntegrityError, match="does not match the requested target"):
        port.read_assignment_history(
            tenant_record_id=TENANT_ID,
            person_record_id=PERSON_ID,
            known_at=KNOWN_AT,
        )


@pytest.mark.parametrize(
    "row",
    [
        assignment_row(recorded_from=datetime(2026, 8, 30, 0, 0)),
        assignment_row(recorded_to=datetime(2026, 8, 29, 0, 0)),
    ],
)
def test_rejects_row_outside_requested_system_knowledge_cutoff(row: tuple[object, ...]) -> None:
    factory = ConnectionFactory([row])
    port = PostgresAssignmentHistoryReadPort(factory)

    with pytest.raises(AssignmentHistoryIntegrityError, match="not visible at the requested knowledge cutoff"):
        port.read_assignment_history(
            tenant_record_id=TENANT_ID,
            person_record_id=PERSON_ID,
            known_at=KNOWN_AT,
        )


def test_open_recorded_interval_is_visible_at_known_at() -> None:
    factory = ConnectionFactory([assignment_row()])
    port = PostgresAssignmentHistoryReadPort(factory)

    records = port.read_assignment_history(
        tenant_record_id=TENANT_ID,
        person_record_id=PERSON_ID,
        known_at=KNOWN_AT,
    )

    assert records[0].recorded_to is None
