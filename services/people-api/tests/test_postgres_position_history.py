"""Regression contract for the PostgreSQL Position-history read adapter."""

from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import date, datetime, timedelta, timezone, tzinfo
from uuid import UUID

import pytest

from orgmetra_people_api.position_history import PositionHistoryIntegrityError
from orgmetra_people_api.postgres_position_history import PostgresPositionHistoryReadPort


TENANT_ID = UUID("018d51d2-9ab1-7ac0-8eb1-0a5dc487b9c1")
POSITION_ID = UUID("018d51d2-9ab1-7ac0-8eb1-0a5dc487b9c2")
VERSION_ID = UUID("018d51d2-9ab1-7ac0-8eb1-0a5dc487b9c3")
ORGANIZATION_ID = UUID("018d51d2-9ab1-7ac0-8eb1-0a5dc487b9c4")
JOB_ID = UUID("018d51d2-9ab1-7ac0-8eb1-0a5dc487b9c5")
KNOWN_AT = datetime(2026, 8, 30, 0, 0, tzinfo=timezone.utc)


class ForgedUUID(UUID):
    """Prove caller-controlled UUID subclasses cannot cross the adapter boundary."""


class ZeroOffsetProvider(tzinfo):
    """Prove a caller-controlled zero-offset timezone is not canonical UTC."""

    def utcoffset(self, dt: datetime | None) -> timedelta:
        return timedelta(0)

    def dst(self, dt: datetime | None) -> timedelta:
        return timedelta(0)


def position_row(
    *,
    tenant_record_id: object = TENANT_ID,
    position_record_id: object = POSITION_ID,
    position_record_version_id: object = VERSION_ID,
    organization_unit_id: object = ORGANIZATION_ID,
    job_profile_id: object = JOB_ID,
    position_status_code: object = "active",
    effective_from: object = date(2026, 1, 1),
    effective_to: object = date(2026, 7, 1),
    recorded_from: object = datetime(2026, 8, 1),
    recorded_to: object = None,
) -> tuple[object, ...]:
    """Return one default DB row projected by the governed SQL query."""
    return (
        tenant_record_id,
        position_record_id,
        position_record_version_id,
        organization_unit_id,
        job_profile_id,
        position_status_code,
        effective_from,
        effective_to,
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
    """Count connection acquisition so invalid inputs prove zero database access."""

    def __init__(self, rows: object) -> None:
        self.calls = 0
        self.cursor = FakeCursor(rows)

    def __call__(self) -> FakeConnection:
        self.calls += 1
        return FakeConnection(self.cursor)


@pytest.mark.parametrize("invalid_factory", [None, 7, "connection"])
def test_rejects_non_callable_connection_factory(invalid_factory: object) -> None:
    with pytest.raises(TypeError, match="connection_factory must be callable"):
        PostgresPositionHistoryReadPort(invalid_factory)  # type: ignore[arg-type]


def test_read_is_tenant_scoped_read_only_bitemporal_and_typed() -> None:
    factory = ConnectionFactory(
        [position_row(recorded_to=datetime(2026, 9, 1))]
    )
    port = PostgresPositionHistoryReadPort(factory)

    records = port.read_position_history(
        tenant_record_id=TENANT_ID,
        position_record_id=POSITION_ID,
        known_at=KNOWN_AT,
    )

    assert len(records) == 1
    record = records[0]
    assert record.tenant_record_id == TENANT_ID
    assert record.position_record_id == POSITION_ID
    assert record.position_record_version_id == VERSION_ID
    assert record.organization_unit_id == ORGANIZATION_ID
    assert record.job_profile_id == JOB_ID
    assert record.position_status_code == "active"
    assert record.effective_from == date(2026, 1, 1)
    assert record.effective_to == date(2026, 7, 1)
    assert record.recorded_from == datetime(2026, 8, 1, tzinfo=timezone.utc)
    assert record.recorded_to == datetime(2026, 9, 1, tzinfo=timezone.utc)
    assert factory.calls == 1

    assert len(factory.cursor.executions) == 3
    transaction_sql, transaction_parameters = factory.cursor.executions[0]
    tenant_sql, tenant_parameters = factory.cursor.executions[1]
    history_sql, history_parameters = factory.cursor.executions[2]
    assert transaction_sql == "SET TRANSACTION ISOLATION LEVEL READ COMMITTED, READ ONLY"
    assert transaction_parameters is None
    assert "pg_catalog.set_config('orgmetra.tenant_record_id', %s, true)" in tenant_sql
    assert tenant_parameters == (str(TENANT_ID),)
    assert "FROM public.position_record_version AS position_version" in history_sql
    assert "JOIN public.position_record AS position_anchor" in history_sql
    assert "position_version.tenant_record_id = %s" in history_sql
    assert "position_version.position_record_id = %s" in history_sql
    assert "position_anchor.recorded_from <= %s" in history_sql
    assert "%s < position_anchor.recorded_to" in history_sql
    assert "position_version.recorded_from <= %s" in history_sql
    assert "%s < position_version.recorded_to" in history_sql
    assert "AT TIME ZONE 'UTC'" in history_sql
    assert "ORDER BY position_version.effective_from, position_version.position_record_version_id" in history_sql
    assert "SELECT *" not in history_sql.upper()
    assert history_parameters == (
        TENANT_ID,
        POSITION_ID,
        KNOWN_AT,
        KNOWN_AT,
        KNOWN_AT,
        KNOWN_AT,
    )


def test_empty_database_result_returns_immutable_empty_tuple() -> None:
    factory = ConnectionFactory([])
    port = PostgresPositionHistoryReadPort(factory)

    assert port.read_position_history(
        tenant_record_id=TENANT_ID,
        position_record_id=POSITION_ID,
        known_at=KNOWN_AT,
    ) == ()


@pytest.mark.parametrize(
    ("tenant_record_id", "position_record_id", "known_at"),
    [
        ("not-a-uuid", POSITION_ID, KNOWN_AT),
        (ForgedUUID(str(TENANT_ID)), POSITION_ID, KNOWN_AT),
        (UUID(int=0), POSITION_ID, KNOWN_AT),
        (TENANT_ID, ForgedUUID(str(POSITION_ID)), KNOWN_AT),
        (TENANT_ID, UUID(int=(1 << 128) - 1), KNOWN_AT),
        (TENANT_ID, POSITION_ID, "2026-08-30"),
        (TENANT_ID, POSITION_ID, datetime(2026, 8, 30)),
        (TENANT_ID, POSITION_ID, datetime(2026, 8, 30, tzinfo=timezone(timedelta(hours=9)))),
        (TENANT_ID, POSITION_ID, datetime(2026, 8, 30, tzinfo=ZeroOffsetProvider())),
    ],
)
def test_invalid_request_identity_or_time_fails_before_database_access(
    tenant_record_id: object,
    position_record_id: object,
    known_at: object,
) -> None:
    factory = ConnectionFactory([])
    port = PostgresPositionHistoryReadPort(factory)

    with pytest.raises(ValueError):
        port.read_position_history(  # type: ignore[arg-type]
            tenant_record_id=tenant_record_id,
            position_record_id=position_record_id,
            known_at=known_at,
        )

    assert factory.calls == 0


def test_rejects_non_default_fetchall_collection() -> None:
    factory = ConnectionFactory((position_row(),))
    port = PostgresPositionHistoryReadPort(factory)

    with pytest.raises(PositionHistoryIntegrityError, match="default list row collection"):
        port.read_position_history(
            tenant_record_id=TENANT_ID,
            position_record_id=POSITION_ID,
            known_at=KNOWN_AT,
        )


@pytest.mark.parametrize("row", [[1] * 10, (1, 2)])
def test_rejects_unsupported_row_container_or_shape(row: object) -> None:
    factory = ConnectionFactory([row])
    port = PostgresPositionHistoryReadPort(factory)

    with pytest.raises(PositionHistoryIntegrityError, match="row has an invalid shape"):
        port.read_position_history(
            tenant_record_id=TENANT_ID,
            position_record_id=POSITION_ID,
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
    factory = ConnectionFactory([position_row(recorded_from=recorded_from, recorded_to=recorded_to)])
    port = PostgresPositionHistoryReadPort(factory)

    with pytest.raises(PositionHistoryIntegrityError, match="database recorded time must be a naive UTC projection"):
        port.read_position_history(
            tenant_record_id=TENANT_ID,
            position_record_id=POSITION_ID,
            known_at=KNOWN_AT,
        )


def test_rejects_database_row_that_fails_position_record_integrity() -> None:
    factory = ConnectionFactory([position_row(position_status_code="NOT_CANONICAL")])
    port = PostgresPositionHistoryReadPort(factory)

    with pytest.raises(PositionHistoryIntegrityError, match="database Position-history row failed integrity"):
        port.read_position_history(
            tenant_record_id=TENANT_ID,
            position_record_id=POSITION_ID,
            known_at=KNOWN_AT,
        )


@pytest.mark.parametrize(
    "row",
    [
        position_row(tenant_record_id=UUID("018d51d2-9ab1-7ac0-8eb1-0a5dc487b9d1")),
        position_row(position_record_id=UUID("018d51d2-9ab1-7ac0-8eb1-0a5dc487b9d2")),
    ],
)
def test_rejects_row_outside_requested_tenant_or_position(row: tuple[object, ...]) -> None:
    factory = ConnectionFactory([row])
    port = PostgresPositionHistoryReadPort(factory)

    with pytest.raises(PositionHistoryIntegrityError, match="does not match the requested target"):
        port.read_position_history(
            tenant_record_id=TENANT_ID,
            position_record_id=POSITION_ID,
            known_at=KNOWN_AT,
        )


@pytest.mark.parametrize(
    "row",
    [
        position_row(recorded_from=datetime(2026, 8, 31)),
        position_row(recorded_to=datetime(2026, 8, 30)),
    ],
)
def test_rejects_row_outside_requested_system_knowledge_cutoff(row: tuple[object, ...]) -> None:
    factory = ConnectionFactory([row])
    port = PostgresPositionHistoryReadPort(factory)

    with pytest.raises(PositionHistoryIntegrityError, match="not visible at the requested knowledge cutoff"):
        port.read_position_history(
            tenant_record_id=TENANT_ID,
            position_record_id=POSITION_ID,
            known_at=KNOWN_AT,
        )


def test_open_recorded_interval_is_visible_at_known_at() -> None:
    factory = ConnectionFactory([position_row()])
    port = PostgresPositionHistoryReadPort(factory)

    records = port.read_position_history(
        tenant_record_id=TENANT_ID,
        position_record_id=POSITION_ID,
        known_at=KNOWN_AT,
    )

    assert records[0].recorded_to is None
    assert isinstance(records, tuple)
