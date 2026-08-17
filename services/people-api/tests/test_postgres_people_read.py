"""Executable contracts for the tenant-bound PostgreSQL People read adapter."""

from __future__ import annotations

from datetime import date
import unittest
from uuid import UUID

from orgmetra_people_api.postgres import PostgresPeopleReadPort
from orgmetra_people_api.people import PeopleRecordIntegrityError, WorkerPeopleRecord

TENANT = UUID("0198a412-6000-7000-8000-000000000001")
OTHER_TENANT = UUID("0198a412-6000-7000-8000-000000000002")
PERSON = UUID("0198a412-6000-7000-8000-000000000010")
OTHER_PERSON = UUID("0198a412-6000-7000-8000-000000000011")
EMPLOYMENT = UUID("0198a412-6000-7000-8000-000000000020")
CONVERSION = UUID("0198a412-6000-7000-8000-000000000030")
CANDIDATE = UUID("0198a412-6000-7000-8000-000000000040")
EFFECTIVE_ON = date(2026, 8, 17)


def worker_row(
    *,
    tenant_record_id: UUID = TENANT,
    person_record_id: UUID = PERSON,
) -> tuple[UUID, UUID, UUID, UUID, UUID, str, str]:
    """Return one canonical PostgreSQL row for an active converted worker."""
    return (
        tenant_record_id,
        CONVERSION,
        CANDIDATE,
        person_record_id,
        EMPLOYMENT,
        "Ada Lovelace",
        "active",
    )


class FakeCursor:
    """Capture parameterized SQL while serving deterministic database rows."""

    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows
        self.executions: list[tuple[str, tuple[object, ...] | None]] = []
        self.fetch_sizes: list[int] = []

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def execute(self, sql: str, parameters: tuple[object, ...] | None = None) -> None:
        """Record each SQL statement and its bound parameters."""
        self.executions.append((sql, parameters))

    def fetchmany(self, size: int) -> list[tuple[object, ...]]:
        """Return at most the requested rows and record the ambiguity bound."""
        self.fetch_sizes.append(size)
        return self.rows[:size]


class FakeConnection:
    """Provide one transaction-scoped cursor context for the adapter."""

    def __init__(self, cursor: FakeCursor) -> None:
        self.cursor_instance = cursor
        self.enter_count = 0
        self.exit_count = 0

    def __enter__(self) -> FakeConnection:
        self.enter_count += 1
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.exit_count += 1
        return None

    def cursor(self) -> FakeCursor:
        """Return the deterministic cursor used by this transaction."""
        return self.cursor_instance


class PostgresPeopleReadPortTests(unittest.TestCase):
    """Prove tenant RLS binding, bitemporal filtering, and fail-closed reads."""

    def _port(
        self,
        rows: list[tuple[object, ...]],
    ) -> tuple[PostgresPeopleReadPort, FakeConnection, FakeCursor]:
        cursor = FakeCursor(rows)
        connection = FakeConnection(cursor)
        return PostgresPeopleReadPort(lambda: connection), connection, cursor

    def test_reads_one_current_worker_inside_tenant_bound_read_only_transaction(self) -> None:
        port, connection, cursor = self._port([worker_row()])

        record = port.read_worker(
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            effective_on=EFFECTIVE_ON,
        )

        self.assertEqual(
            record,
            WorkerPeopleRecord(
                tenant_record_id=TENANT,
                candidate_worker_conversion_record_id=CONVERSION,
                candidate_profile_id=CANDIDATE,
                person_record_id=PERSON,
                employment_record_id=EMPLOYMENT,
                display_name="Ada Lovelace",
                employment_status_code="active",
            ),
        )
        self.assertEqual((connection.enter_count, connection.exit_count), (1, 1))
        self.assertEqual(cursor.fetch_sizes, [2])
        self.assertEqual(cursor.executions[0], ("SET TRANSACTION READ ONLY", None))
        self.assertEqual(
            cursor.executions[1],
            (
                "SELECT pg_catalog.set_config('orgmetra.tenant_record_id', %s, true)",
                (str(TENANT),),
            ),
        )
        worker_sql, worker_parameters = cursor.executions[2]
        self.assertIn("public.candidate_worker_conversion_record", worker_sql)
        self.assertIn("public.person_name_record", worker_sql)
        self.assertIn("public.employment_record_version", worker_sql)
        self.assertIn("recorded_to IS NULL", worker_sql)
        self.assertNotIn(str(TENANT), worker_sql)
        self.assertEqual(
            worker_parameters,
            (
                TENANT,
                PERSON,
                EFFECTIVE_ON,
                EFFECTIVE_ON,
                EFFECTIVE_ON,
                EFFECTIVE_ON,
                EFFECTIVE_ON,
                EFFECTIVE_ON,
            ),
        )

    def test_missing_current_worker_returns_none(self) -> None:
        port, _, _ = self._port([])

        self.assertIsNone(
            port.read_worker(
                tenant_record_id=TENANT,
                person_record_id=PERSON,
                effective_on=EFFECTIVE_ON,
            )
        )

    def test_ambiguous_current_worker_fails_closed(self) -> None:
        port, _, _ = self._port([worker_row(), worker_row()])

        with self.assertRaisesRegex(PeopleRecordIntegrityError, "multiple current worker records"):
            port.read_worker(
                tenant_record_id=TENANT,
                person_record_id=PERSON,
                effective_on=EFFECTIVE_ON,
            )

    def test_row_identity_mismatch_fails_closed(self) -> None:
        for row in (
            worker_row(tenant_record_id=OTHER_TENANT),
            worker_row(person_record_id=OTHER_PERSON),
        ):
            with self.subTest(row=row):
                port, _, _ = self._port([row])
                with self.assertRaisesRegex(PeopleRecordIntegrityError, "database row escaped requested target"):
                    port.read_worker(
                        tenant_record_id=TENANT,
                        person_record_id=PERSON,
                        effective_on=EFFECTIVE_ON,
                    )

    def test_invalid_direct_port_request_never_opens_database_connection(self) -> None:
        calls = 0

        def connection_factory() -> FakeConnection:
            nonlocal calls
            calls += 1
            return FakeConnection(FakeCursor([]))

        port = PostgresPeopleReadPort(connection_factory)
        invalid_requests = (
            {"tenant_record_id": UUID(int=0), "person_record_id": PERSON, "effective_on": EFFECTIVE_ON},
            {
                "tenant_record_id": TENANT,
                "person_record_id": UUID(int=(1 << 128) - 1),
                "effective_on": EFFECTIVE_ON,
            },
            {"tenant_record_id": TENANT, "person_record_id": PERSON, "effective_on": "2026-08-17"},
        )
        for request in invalid_requests:
            with self.subTest(request=request), self.assertRaises(ValueError):
                port.read_worker(**request)

        self.assertEqual(calls, 0)

    def test_connection_factory_must_be_callable(self) -> None:
        with self.assertRaisesRegex(TypeError, "connection_factory must be callable"):
            PostgresPeopleReadPort(None)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
