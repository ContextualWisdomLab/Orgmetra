"""Regression contracts for the PostgreSQL Employment-history read adapter."""

from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import date, datetime, timedelta, timezone, tzinfo
from uuid import UUID

import pytest

from orgmetra_people_api.employment_history import EmploymentHistoryIntegrityError
from orgmetra_people_api.postgres_employment_history import PostgresEmploymentHistoryReadPort

TENANT_ID = UUID("0198a415-9ab1-7000-8000-000000000001")
PERSON_ID = UUID("0198a415-9ab1-7000-8000-000000000002")
EMPLOYMENT_ID = UUID("0198a415-9ab1-7000-8000-000000000003")
VERSION_ID = UUID("0198a415-9ab1-7000-8000-000000000004")
KNOWN_AT = datetime(2026, 8, 30, tzinfo=timezone.utc)


class ForgedUUID(UUID):
    """Prove caller-controlled UUID subclasses cannot cross the adapter boundary."""


class ZeroOffsetProvider(tzinfo):
    """Prove a caller-controlled zero-offset timezone is not canonical UTC."""

    def utcoffset(self, dt: datetime | None) -> timedelta:
        """Return zero only to exercise the exact-timezone check."""
        del dt
        return timedelta(0)

    def dst(self, dt: datetime | None) -> timedelta:
        """Return zero daylight-saving offset for the test timezone."""
        del dt
        return timedelta(0)


def employment_row(
    *,
    tenant_record_id: object = TENANT_ID,
    person_record_id: object = PERSON_ID,
    employment_record_id: object = EMPLOYMENT_ID,
    employment_record_version_id: object = VERSION_ID,
    employment_status_code: object = "active",
    employment_concurrency_code: object = "exclusive",
    effective_from: object = date(2026, 1, 1),
    effective_to: object = date(2026, 7, 1),
    recorded_from: object = datetime(2026, 8, 1),
    recorded_to: object = None,
) -> tuple[object, ...]:
    """Return one default DB row projected by the governed SQL query."""
    return (
        tenant_record_id,
        person_record_id,
        employment_record_id,
        employment_record_version_id,
        employment_status_code,
        employment_concurrency_code,
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
        del exc_type, exc, traceback
        return None

    def execute(self, statement: str, parameters: object | None = None) -> None:
        """Record each SQL statement and its bound parameters."""
        self.executions.append((statement, parameters))

    def fetchall(self) -> object:
        """Return the configured DB-API row collection."""
        return self.rows


class FakeConnection(AbstractContextManager["FakeConnection"]):
    """Minimal connection exposing one stable cursor."""

    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del exc_type, exc, traceback
        return None

    def cursor(self) -> FakeCursor:
        """Return the deterministic cursor used by this transaction."""
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
        PostgresEmploymentHistoryReadPort(invalid_factory)  # type: ignore[arg-type]


def test_read_is_tenant_scoped_read_only_bitemporal_and_typed() -> None:
    factory = ConnectionFactory([employment_row(recorded_to=datetime(2026, 9, 1))])
    port = PostgresEmploymentHistoryReadPort(factory)

    records = port.read_employment_history(
        tenant_record_id=TENANT_ID,
        person_record_id=PERSON_ID,
        known_at=KNOWN_AT,
    )

    assert len(records) == 1
    record = records[0]
    assert record.tenant_record_id == TENANT_ID
    assert record.person_record_id == PERSON_ID
    assert record.employment_record_id == EMPLOYMENT_ID
    assert record.employment_record_version_id == VERSION_ID
    assert record.employment_status_code == "active"
    assert record.employment_concurrency_code == "exclusive"
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
    assert "FROM public.employment_record_version AS employment_version" in history_sql
    assert "JOIN public.employment_record AS employment" in history_sql
    assert "employment_version.tenant_record_id = %s" in history_sql
    assert "employment.person_record_id = %s" in history_sql
    assert "employment.recorded_from <= %s" in history_sql
    assert "%s < employment.recorded_to" in history_sql
    assert "employment_version.recorded_from <= %s" in history_sql
    assert "%s < employment_version.recorded_to" in history_sql
    assert "AT TIME ZONE 'UTC'" in history_sql
    assert "ORDER BY employment_version.effective_from" in history_sql
    assert "SELECT *" not in history_sql.upper()
    assert history_parameters == (
        TENANT_ID,
        PERSON_ID,
        KNOWN_AT,
        KNOWN_AT,
        KNOWN_AT,
        KNOWN_AT,
    )


def test_empty_database_result_returns_immutable_empty_tuple() -> None:
    factory = ConnectionFactory([])
    port = PostgresEmploymentHistoryReadPort(factory)

    assert port.read_employment_history(
        tenant_record_id=TENANT_ID,
        person_record_id=PERSON_ID,
        known_at=KNOWN_AT,
    ) == ()


@pytest.mark.parametrize(
    ("tenant_record_id", "person_record_id", "known_at"),
    [
        ("not-a-uuid", PERSON_ID, KNOWN_AT),
        (ForgedUUID(str(TENANT_ID)), PERSON_ID, KNOWN_AT),
        (UUID(int=0), PERSON_ID, KNOWN_AT),
        (TENANT_ID, ForgedUUID(str(PERSON_ID)), KNOWN_AT),
        (TENANT_ID, UUID(int=(1 << 128) - 1), KNOWN_AT),
        (TENANT_ID, PERSON_ID, "2026-08-30"),
        (TENANT_ID, PERSON_ID, datetime(2026, 8, 30)),
        (TENANT_ID, PERSON_ID, datetime(2026, 8, 30, tzinfo=timezone(timedelta(hours=9)))),
        (TENANT_ID, PERSON_ID, datetime(2026, 8, 30, tzinfo=ZeroOffsetProvider())),
    ],
)
def test_invalid_request_identity_or_time_fails_before_database_access(
    tenant_record_id: object,
    person_record_id: object,
    known_at: object,
) -> None:
    factory = ConnectionFactory([])
    port = PostgresEmploymentHistoryReadPort(factory)

    with pytest.raises(ValueError):
        port.read_employment_history(  # type: ignore[arg-type]
            tenant_record_id=tenant_record_id,
            person_record_id=person_record_id,
            known_at=known_at,
        )

    assert factory.calls == 0


def test_rejects_non_default_fetchall_collection() -> None:
    factory = ConnectionFactory((employment_row(),))
    port = PostgresEmploymentHistoryReadPort(factory)

    with pytest.raises(EmploymentHistoryIntegrityError, match="default list row collection"):
        port.read_employment_history(
            tenant_record_id=TENANT_ID,
            person_record_id=PERSON_ID,
            known_at=KNOWN_AT,
        )


@pytest.mark.parametrize("row", [[1] * 10, (1, 2)])
def test_rejects_unsupported_row_container_or_shape(row: object) -> None:
    factory = ConnectionFactory([row])
    port = PostgresEmploymentHistoryReadPort(factory)

    with pytest.raises(EmploymentHistoryIntegrityError, match="row has an invalid shape"):
        port.read_employment_history(
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
    factory = ConnectionFactory([employment_row(recorded_from=recorded_from, recorded_to=recorded_to)])
    port = PostgresEmploymentHistoryReadPort(factory)

    with pytest.raises(EmploymentHistoryIntegrityError, match="database recorded time must be a naive UTC projection"):
        port.read_employment_history(
            tenant_record_id=TENANT_ID,
            person_record_id=PERSON_ID,
            known_at=KNOWN_AT,
        )


def test_rejects_database_row_that_fails_employment_record_integrity() -> None:
    factory = ConnectionFactory([employment_row(employment_status_code="NOT_CANONICAL")])
    port = PostgresEmploymentHistoryReadPort(factory)

    with pytest.raises(EmploymentHistoryIntegrityError, match="database Employment-history row failed integrity"):
        port.read_employment_history(
            tenant_record_id=TENANT_ID,
            person_record_id=PERSON_ID,
            known_at=KNOWN_AT,
        )


@pytest.mark.parametrize(
    "row",
    [
        employment_row(tenant_record_id=UUID("0198a415-9ab1-7000-8000-000000000011")),
        employment_row(person_record_id=UUID("0198a415-9ab1-7000-8000-000000000012")),
    ],
)
def test_rejects_row_outside_requested_tenant_or_person(row: tuple[object, ...]) -> None:
    factory = ConnectionFactory([row])
    port = PostgresEmploymentHistoryReadPort(factory)

    with pytest.raises(EmploymentHistoryIntegrityError, match="does not match the requested target"):
        port.read_employment_history(
            tenant_record_id=TENANT_ID,
            person_record_id=PERSON_ID,
            known_at=KNOWN_AT,
        )


@pytest.mark.parametrize(
    "row",
    [
        employment_row(recorded_from=datetime(2026, 8, 31)),
        employment_row(recorded_to=datetime(2026, 8, 30)),
    ],
)
def test_rejects_row_outside_requested_system_knowledge_cutoff(row: tuple[object, ...]) -> None:
    factory = ConnectionFactory([row])
    port = PostgresEmploymentHistoryReadPort(factory)

    with pytest.raises(EmploymentHistoryIntegrityError, match="not visible at the requested knowledge cutoff"):
        port.read_employment_history(
            tenant_record_id=TENANT_ID,
            person_record_id=PERSON_ID,
            known_at=KNOWN_AT,
        )


def test_open_recorded_interval_is_visible_at_known_at() -> None:
    factory = ConnectionFactory([employment_row()])
    port = PostgresEmploymentHistoryReadPort(factory)

    records = port.read_employment_history(
        tenant_record_id=TENANT_ID,
        person_record_id=PERSON_ID,
        known_at=KNOWN_AT,
    )

    assert records[0].recorded_to is None
    assert isinstance(records, tuple)
