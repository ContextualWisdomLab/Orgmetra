"""Unit contracts for the PostgreSQL Employment separation adapter."""

from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import date, datetime, timezone
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDecision
from orgmetra_people_api.mutations import PeopleMutationNotFound
from orgmetra_people_api.postgres_separation import PostgresEmploymentSeparationPort
from orgmetra_people_api.separation import (
    EmploymentSeparationCommand,
    EmploymentSeparationIntegrityError,
)

TENANT = UUID("0198a412-8000-7000-8000-000000000001")
PERSON = UUID("0198a412-8000-7000-8000-000000000020")
EMPLOYMENT = UUID("0198a412-8000-7000-8000-000000000030")
EXPECTED_VERSION = UUID("0198a412-8000-7000-8000-000000000031")
TERMINAL_VERSION = UUID("0198a412-8000-7000-8000-000000000032")
AUDIT_EVENT = UUID("0198a412-8000-7000-8000-000000000080")
OUTBOX = UUID("0198a412-8000-7000-8000-000000000081")
RECORDED_AT = datetime(2026, 9, 12, 15, 0, tzinfo=timezone.utc)


def command() -> EmploymentSeparationCommand:
    """Build one deterministic adapter command."""
    return EmploymentSeparationCommand(
        tenant_record_id=TENANT,
        person_record_id=PERSON,
        employment_record_id=EMPLOYMENT,
        expected_employment_record_version_id=EXPECTED_VERSION,
        separation_effective_on=date(2026, 10, 1),
        separation_reason_code="voluntary_resignation",
        evidence_reference="separation_packet:adapter-case",
        evidence_version_code="v1",
        confirmation_reference="human_confirmation:adapter-case",
        idempotency_key="employment-separation-adapter-case",
        audit_event_record_id=AUDIT_EVENT,
        outbox_delivery_record_id=OUTBOX,
    )


def authorization(**overrides: object) -> AuthorizationDecision:
    """Build exact allow evidence for the requested separation."""
    values: dict[str, object] = {
        "allowed": True,
        "tenant_record_id": TENANT,
        "actor_reference": "keyverse_subject:people-operator-17",
        "resource_reference": f"employment_record:{EMPLOYMENT.hex}",
        "policy_version_code": "employment-separation-v1",
        "purpose_code": "workforce_admin",
        "operation_code": "separate_record",
        "resource_kind": "employment_record",
        "requested_fields": frozenset({"employment_record"}),
        "authorized_fields": frozenset({"employment_record"}),
        "reason_code": "allowed",
        "next_action": "Continue with only the authorized fields.",
    }
    values.update(overrides)
    return AuthorizationDecision(**values)  # type: ignore[arg-type]


class DatabaseFailure(RuntimeError):
    """Provide only the SQLSTATE surface used by the adapter boundary."""

    def __init__(self, sqlstate: str) -> None:
        super().__init__(sqlstate)
        self.sqlstate = sqlstate


class FakeCursor(AbstractContextManager["FakeCursor"]):
    """Record SQL calls and supply one fixed database result or failure."""

    def __init__(self, *, row: object | None = None, failure: Exception | None = None) -> None:
        self.row = row
        self.failure = failure
        self.calls: list[tuple[str, object | None]] = []

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def execute(self, sql: str, parameters: object | None = None) -> None:
        self.calls.append((sql, parameters))
        if "separate_employment_record_once" in sql and self.failure is not None:
            raise self.failure

    def fetchmany(self, size: int) -> object:
        if size != 2 or self.row is None:
            return []
        return [self.row]


class InvalidBatchCursor(FakeCursor):
    """Return a non-container fetch batch to exercise the DB trust boundary."""

    def fetchmany(self, size: int) -> object:
        del size
        return object()


class FakeConnection(AbstractContextManager["FakeConnection"]):
    """Expose one cursor and capture whether the transaction exits with an error."""

    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor
        self.exit_exception_type: object | None = None

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.exit_exception_type = exc_type
        return None

    def cursor(self) -> FakeCursor:
        return self._cursor


class ConnectionFactory:
    """Return the captured connection and count invocations."""

    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection
        self.calls = 0

    def __call__(self) -> FakeConnection:
        self.calls += 1
        return self.connection


class PostgresEmploymentSeparationTests(unittest.TestCase):
    """Prove checked authorization, tenant binding and typed DB evidence."""

    def test_calls_governed_function_in_one_tenant_bound_transaction(self) -> None:
        cursor = FakeCursor(row=(EMPLOYMENT, TERMINAL_VERSION, RECORDED_AT, False))
        connection = FakeConnection(cursor)
        factory = ConnectionFactory(connection)
        port = PostgresEmploymentSeparationPort(factory)

        result = port.separate_employment(command=command(), authorization=authorization())

        self.assertEqual(factory.calls, 1)
        self.assertIsNone(connection.exit_exception_type)
        self.assertEqual(result.employment_record_id, EMPLOYMENT)
        self.assertEqual(result.separated_employment_record_version_id, TERMINAL_VERSION)
        self.assertEqual(result.recorded_at, RECORDED_AT)
        self.assertFalse(result.replayed)
        self.assertEqual(cursor.calls[0][0], "SET TRANSACTION ISOLATION LEVEL READ COMMITTED, READ WRITE")
        self.assertEqual(cursor.calls[1][1], (str(TENANT),))
        function_sql, function_parameters = cursor.calls[2]
        self.assertIn("public.separate_employment_record_once", function_sql)
        self.assertEqual(
            function_parameters,
            (
                TENANT,
                PERSON,
                EMPLOYMENT,
                EXPECTED_VERSION,
                date(2026, 10, 1),
                "voluntary_resignation",
                "separation_packet:adapter-case",
                "v1",
                "keyverse_subject:people-operator-17",
                "workforce_admin",
                "human_confirmation:adapter-case",
                "employment-separation-adapter-case",
                AUDIT_EVENT,
                OUTBOX,
            ),
        )

    def test_rejects_authorization_that_does_not_match_exact_operation(self) -> None:
        port = PostgresEmploymentSeparationPort(ConnectionFactory(FakeConnection(FakeCursor())))
        cases: tuple[object, ...] = (
            object(),
            authorization(allowed=False, authorized_fields=frozenset()),
            authorization(tenant_record_id=UUID("0198a412-8000-7000-8000-000000000099")),
            authorization(resource_reference="employment_record:0198a412800070008000000000000099"),
            authorization(purpose_code="benefits_admin"),
            authorization(operation_code="create_record"),
            authorization(resource_kind="assignment_record"),
            authorization(requested_fields=frozenset({"assignment_record"})),
            authorization(authorized_fields=frozenset({"assignment_record"})),
        )
        for decision in cases:
            with self.subTest(decision=decision), self.assertRaises(EmploymentSeparationIntegrityError):
                port.separate_employment(command=command(), authorization=decision)  # type: ignore[arg-type]

    def test_rejects_malformed_database_result_before_transaction_commit_boundary(self) -> None:
        rows = (
            None,
            "not-a-row",
            (EMPLOYMENT, TERMINAL_VERSION, RECORDED_AT),
            (EMPLOYMENT, TERMINAL_VERSION, RECORDED_AT, False, "extra"),
            (UUID(int=0), TERMINAL_VERSION, RECORDED_AT, False),
            (EMPLOYMENT, TERMINAL_VERSION, datetime(2026, 9, 12, 15, 0), False),
            (EMPLOYMENT, TERMINAL_VERSION, RECORDED_AT, 1),
            (UUID("0198a412-8000-7000-8000-000000000099"), TERMINAL_VERSION, RECORDED_AT, False),
        )
        for row in rows:
            connection = FakeConnection(FakeCursor(row=row))
            with self.subTest(row=row), self.assertRaises(EmploymentSeparationIntegrityError):
                port = PostgresEmploymentSeparationPort(ConnectionFactory(connection))
                port.separate_employment(command=command(), authorization=authorization())
            self.assertIs(connection.exit_exception_type, EmploymentSeparationIntegrityError)

        connection = FakeConnection(InvalidBatchCursor())
        with self.assertRaises(EmploymentSeparationIntegrityError):
            port = PostgresEmploymentSeparationPort(ConnectionFactory(connection))
            port.separate_employment(command=command(), authorization=authorization())
        self.assertIs(connection.exit_exception_type, EmploymentSeparationIntegrityError)

    def test_maps_governed_conflicts_but_not_permission_failures(self) -> None:
        cases = (
            ("23503", PeopleMutationNotFound),
            ("40001", EmploymentSeparationIntegrityError),
            ("23505", EmploymentSeparationIntegrityError),
            ("55000", EmploymentSeparationIntegrityError),
            ("22023", EmploymentSeparationIntegrityError),
        )
        for sqlstate, expected in cases:
            with self.subTest(sqlstate=sqlstate), self.assertRaises(expected):
                port = PostgresEmploymentSeparationPort(
                    ConnectionFactory(FakeConnection(FakeCursor(failure=DatabaseFailure(sqlstate))))
                )
                port.separate_employment(command=command(), authorization=authorization())

        permission_failure = DatabaseFailure("42501")
        with self.assertRaises(DatabaseFailure):
            port = PostgresEmploymentSeparationPort(
                ConnectionFactory(FakeConnection(FakeCursor(failure=permission_failure)))
            )
            port.separate_employment(command=command(), authorization=authorization())

    def test_requires_typed_command_and_callable_factory(self) -> None:
        with self.assertRaisesRegex(TypeError, "connection_factory"):
            PostgresEmploymentSeparationPort(object())  # type: ignore[arg-type]

        port = PostgresEmploymentSeparationPort(ConnectionFactory(FakeConnection(FakeCursor())))
        with self.assertRaisesRegex(TypeError, "EmploymentSeparationCommand"):
            port.separate_employment(command=object(), authorization=authorization())  # type: ignore[arg-type]

    def test_structurally_binds_connection_factory(self) -> None:
        factory = ConnectionFactory(FakeConnection(FakeCursor(row=(EMPLOYMENT, TERMINAL_VERSION, RECORDED_AT, True))))
        port = PostgresEmploymentSeparationPort(factory)
        self.assertIs(tuple.__getitem__(port, 0), factory)
        with self.assertRaises(AttributeError):
            port.connection_factory = object()  # type: ignore[attr-defined]


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
