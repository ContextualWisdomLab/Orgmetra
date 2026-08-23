"""Executable contract for the least-privileged PostgreSQL audit reader."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import unittest
from uuid import UUID

from orgmetra_audit_evidence_review import (
    AuditEvidenceQuery,
    PostgresAuditEvidenceRowReader,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
EVENT = UUID("11111111-1111-4111-8111-111111111111")
QUERY = "audit_review:22222222-2222-4222-8222-222222222222"
REQUESTER = "actor:33333333-3333-4333-8333-333333333333"
FROM = datetime(2026, 8, 1, tzinfo=timezone.utc)
BEFORE = datetime(2026, 9, 1, tzinfo=timezone.utc)
RECORDED = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)


def _query() -> AuditEvidenceQuery:
    """Return one bounded tenant-scoped audit query."""
    return AuditEvidenceQuery(
        tenant_record_id=TENANT,
        query_reference=QUERY,
        requester_reference=REQUESTER,
        purpose_code="audit_evidence_review",
        recorded_from=FROM,
        recorded_before=BEFORE,
        limit=50,
    )


def _canonical_event() -> str:
    """Return one canonical PII-minimized persisted audit event."""
    document = {
        "data": {"high_impact": False, "result_code": "updated"},
        "datacontenttype": "application/json",
        "id": str(EVENT),
        "orgmetraactor": REQUESTER,
        "orgmetraevidence": "v1",
        "orgmetrapurpose": "people_record_update",
        "orgmetrareason": "authorized_change",
        "orgmetratenant": str(TENANT),
        "source": "urn:orgmetra:people_api",
        "specversion": "1.0",
        "subject": "person:44444444-4444-4444-8444-444444444444",
        "time": "2026-08-20T11:59:00Z",
        "type": "orgmetra.people.updated",
    }
    return json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _row() -> tuple[object, ...]:
    """Return one driver-shaped persisted audit row."""
    canonical = _canonical_event()
    return (
        TENANT,
        EVENT,
        canonical,
        sha256(canonical.encode("utf-8")).hexdigest(),
        RECORDED,
    )


class _Cursor:
    """Capture SQL while exposing deterministic role and audit rows."""

    def __init__(self, *, role_allowed: bool = True, rows: list[tuple[object, ...]] | None = None) -> None:
        self.role_allowed = role_allowed
        self.rows = list(rows or [])
        self.executions: list[tuple[str, tuple[object, ...] | None]] = []
        self.fetchmany_sizes: list[int] = []

    def __enter__(self) -> _Cursor:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def execute(self, sql: str, parameters: tuple[object, ...] | None = None) -> None:
        """Record one parameterized statement."""
        self.executions.append((sql, parameters))

    def fetchone(self) -> tuple[int] | None:
        """Return a row only for a NOSUPERUSER/NOBYPASSRLS role."""
        return (1,) if self.role_allowed else None

    def fetchmany(self, size: int) -> list[tuple[object, ...]]:
        """Return at most the requested bounded number of audit rows."""
        self.fetchmany_sizes.append(size)
        return self.rows[:size]


class _Connection:
    """Provide one transaction-scoped cursor."""

    def __init__(self, cursor: _Cursor) -> None:
        self.cursor_instance = cursor
        self.enter_count = 0
        self.exit_count = 0

    def __enter__(self) -> _Connection:
        self.enter_count += 1
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.exit_count += 1
        return None

    def cursor(self) -> _Cursor:
        """Return the deterministic cursor."""
        return self.cursor_instance


class PostgresAuditEvidenceRowReaderTests(unittest.TestCase):
    """Prove read-only role enforcement, tenant RLS binding, and bounded reads."""

    def _reader(
        self,
        *,
        role_allowed: bool = True,
        rows: list[tuple[object, ...]] | None = None,
    ) -> tuple[PostgresAuditEvidenceRowReader, _Connection, _Cursor]:
        cursor = _Cursor(role_allowed=role_allowed, rows=rows)
        connection = _Connection(cursor)
        return PostgresAuditEvidenceRowReader(lambda: connection), connection, cursor

    def test_reads_verified_rows_inside_read_only_tenant_bound_transaction(self) -> None:
        reader, connection, cursor = self._reader(rows=[_row()])

        rows = reader.read_rows(_query())

        self.assertEqual((connection.enter_count, connection.exit_count), (1, 1))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].tenant_record_id, TENANT)
        self.assertEqual(rows[0].audit_event_record_id, EVENT)
        self.assertEqual(cursor.executions[0], ("SET TRANSACTION READ ONLY", None))
        self.assertIn("pg_catalog.pg_roles", cursor.executions[1][0])
        self.assertEqual(cursor.executions[1][1], None)
        self.assertEqual(
            cursor.executions[2],
            (
                "SELECT pg_catalog.set_config('orgmetra.tenant_record_id', %s, true)",
                (str(TENANT),),
            ),
        )
        audit_sql, audit_parameters = cursor.executions[3]
        self.assertIn("public.audit_event_record", audit_sql)
        self.assertIn("ORDER BY recorded_at ASC, audit_event_record_id ASC", audit_sql)
        self.assertNotIn(str(TENANT), audit_sql)
        self.assertEqual(audit_parameters, (TENANT, FROM, BEFORE, 50))
        self.assertEqual(cursor.fetchmany_sizes, [50])

    def test_privileged_role_fails_closed_before_tenant_context_or_audit_read(self) -> None:
        reader, _, cursor = self._reader(role_allowed=False, rows=[_row()])

        with self.assertRaisesRegex(PermissionError, "NOSUPERUSER NOBYPASSRLS"):
            reader.read_rows(_query())

        self.assertEqual(len(cursor.executions), 2)
        self.assertEqual(cursor.fetchmany_sizes, [])

    def test_mutated_query_is_revalidated_before_opening_database_connection(self) -> None:
        calls = 0

        def connection_factory() -> _Connection:
            nonlocal calls
            calls += 1
            return _Connection(_Cursor())

        query = _query()
        object.__setattr__(query, "limit", 999)
        reader = PostgresAuditEvidenceRowReader(connection_factory)

        with self.assertRaisesRegex(ValueError, "limit must be an integer"):
            reader.read_rows(query)

        self.assertEqual(calls, 0)

    def test_unexpected_driver_row_shape_fails_closed(self) -> None:
        reader, _, _ = self._reader(rows=[(TENANT, EVENT)])

        with self.assertRaisesRegex(ValueError, "five audit evidence columns"):
            reader.read_rows(_query())

    def test_factory_and_query_runtime_types_are_rejected_before_database_use(self) -> None:
        with self.assertRaisesRegex(TypeError, "connection_factory must be callable"):
            PostgresAuditEvidenceRowReader(None)  # type: ignore[arg-type]

        reader, connection, _ = self._reader()
        with self.assertRaisesRegex(TypeError, "exact AuditEvidenceQuery"):
            reader.read_rows(object())  # type: ignore[arg-type]
        self.assertEqual(connection.enter_count, 0)


if __name__ == "__main__":
    unittest.main()
