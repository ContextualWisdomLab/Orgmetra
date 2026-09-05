"""Executable contracts for atomic PostgreSQL People mutations."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDecision
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.mutations import (
    PeopleMutationIntegrityError,
    PeopleMutationNotFound,
    create_assignment_record,
    create_employment_record,
    create_position_record,
    mutation_command_digest,
)
from orgmetra_people_api.postgres_mutations import PostgresPeopleMutationPort
from authorization_test_support import issued_authorization
from test_people_mutations import (
    TENANT,
    PERSON,
    EMPLOYMENT,
    EMPLOYMENT_VERSION,
    POSITION,
    POSITION_VERSION,
    ORGANIZATION,
    JOB,
    ASSIGNMENT,
    assignment_command,
    assignment_policy,
    employment_command,
    employment_policy,
    position_command,
    position_policy,
)

CONVERSION = UUID("0198a412-8200-7000-8000-000000000090")
RECORDED_AT = datetime(2026, 8, 18, 0, 1, tzinfo=timezone.utc)
ACTOR = "keyverse_subject:operator-17"
_POST_LOCK_CLOCK_SQL = "SELECT pg_catalog.clock_timestamp()"


class ScriptedCursor:
    """Serve scripted fetch results while capturing SQL and a database clock."""

    def __init__(
        self,
        fetchmany_rows: list[list[tuple[object, ...]]],
        fetchall_rows: list[list[tuple[object, ...]]],
        *,
        clock_timestamp: datetime = RECORDED_AT,
    ) -> None:
        self.fetchmany_rows = list(fetchmany_rows)
        self.fetchall_rows = list(fetchall_rows)
        self.clock_timestamp = clock_timestamp
        self.executions: list[tuple[str, tuple[object, ...] | None]] = []
        self._clock_result_pending = False

    def __enter__(self) -> ScriptedCursor:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def execute(self, sql: str, parameters: tuple[object, ...] | None = None) -> None:
        self.executions.append((sql, parameters))
        self._clock_result_pending = sql == _POST_LOCK_CLOCK_SQL

    def fetchmany(self, size: int) -> list[tuple[object, ...]]:
        if self._clock_result_pending:
            self._clock_result_pending = False
            return [(self.clock_timestamp,)][:size]
        rows = self.fetchmany_rows.pop(0)
        return rows[:size]

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.fetchall_rows.pop(0)


class FakeConnection:
    """Model one transaction context whose exception exit represents rollback."""

    def __init__(self, cursor: ScriptedCursor) -> None:
        self.cursor_instance = cursor
        self.exit_exception: type[BaseException] | None = None

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.exit_exception = exc_type if isinstance(exc_type, type) and issubclass(exc_type, BaseException) else None
        return None

    def cursor(self) -> ScriptedCursor:
        return self.cursor_instance


def employment_authorization() -> AuthorizationDecision:
    """Return the exact allow decision issued by the employment policy evaluator."""
    return issued_authorization(
        tenant_record_id=TENANT,
        actor_reference=ACTOR,
        resource_reference=f"employment_record:{EMPLOYMENT.hex}",
        policy_version_code="people-mutation-v1",
        purpose_code="workforce_admin",
        operation_code="create_record",
        resource_kind="employment_record",
        requested_fields=frozenset({"employment_record"}),
        required_scope_code="orgmetra.people.write",
    )


def position_authorization() -> AuthorizationDecision:
    """Return the exact allow decision issued by the position policy evaluator."""
    return issued_authorization(
        tenant_record_id=TENANT,
        actor_reference=ACTOR,
        resource_reference=f"position_record:{POSITION.hex}",
        policy_version_code="people-mutation-v1",
        purpose_code="job_architecture_admin",
        operation_code="create_record",
        resource_kind="position_record",
        requested_fields=frozenset({"position_record"}),
        required_scope_code="orgmetra.job_architecture.write",
    )


def assignment_authorization() -> AuthorizationDecision:
    """Return the exact allow decision issued by the assignment policy evaluator."""
    return issued_authorization(
        tenant_record_id=TENANT,
        actor_reference=ACTOR,
        resource_reference=f"assignment_record:{ASSIGNMENT.hex}",
        policy_version_code="people-mutation-v1",
        purpose_code="workforce_admin",
        operation_code="create_record",
        resource_kind="assignment_record",
        requested_fields=frozenset({"assignment_record"}),
        required_scope_code="orgmetra.people.write",
    )


def covering_employment_row() -> tuple[object, ...]:
    """Return one active exclusive employment version covering the assignment date."""
    return (
        EMPLOYMENT,
        EMPLOYMENT_VERSION,
        PERSON,
        "active",
        "exclusive",
        date(2026, 8, 1),
        None,
        RECORDED_AT,
        None,
    )


def covering_position_row() -> tuple[object, ...]:
    """Return one open position version covering the assignment date."""
    return (
        POSITION,
        POSITION_VERSION,
        "open",
        date(2026, 8, 1),
        None,
        RECORDED_AT,
        None,
    )


PRINCIPAL = AuthenticatedPrincipal(
    tenant_record_id=TENANT,
    actor_reference=ACTOR,
    granted_scope_codes=frozenset({"orgmetra.people.write", "orgmetra.job_architecture.write"}),
)


class PostgresPeopleMutationTests(unittest.TestCase):
    """Prove one tenant-bound transaction owns HRIS, conversion, and audit writes."""

    def _port(
        self,
        fetchmany_rows: list[list[tuple[object, ...]]],
        fetchall_rows: list[list[tuple[object, ...]]] | None = None,
        *,
        replay_row: tuple[object, ...] | None = None,
        skip_idempotency_lookup: bool = False,
    ) -> tuple[PostgresPeopleMutationPort, ScriptedCursor]:
        if skip_idempotency_lookup:
            lookup_rows = list(fetchmany_rows)
        else:
            lookup_rows = [[replay_row] if replay_row is not None else []] + list(fetchmany_rows)
        cursor = ScriptedCursor(lookup_rows, fetchall_rows or [])
        connection = FakeConnection(cursor)
        return PostgresPeopleMutationPort(lambda: connection), cursor

    def test_employment_requires_conversion_and_records_audit_atomically(self) -> None:
        port, cursor = self._port([[(CONVERSION, RECORDED_AT)]], [[]])
        result = create_employment_record(
            principal=PRINCIPAL,
            command=employment_command(),
            purpose_code="workforce_admin",
            policy=employment_policy(),
            mutation_port=port,
        )
        self.assertEqual(result.employment_record_id, EMPLOYMENT)
        sql_text = "\n".join(sql for sql, _parameters in cursor.executions)
        self.assertIn("public.candidate_worker_conversion_record", sql_text)
        conversion_sql = next(
            sql for sql, _parameters in cursor.executions if "candidate_worker_conversion_record" in sql
        )
        self.assertIn("conversion.recorded_to IS NULL", conversion_sql)
        self.assertIn("public.employment_record", sql_text)
        self.assertIn("employment_concurrency_code", sql_text)
        self.assertIn("public.record_audit_outbox_event", sql_text)
        self.assertIn("public.people_mutation_idempotency_record", sql_text)
        self.assertNotIn("candidate_worker_link", sql_text)
        audit_sql, audit_parameters = next(
            execution for execution in cursor.executions if execution[0].startswith("SELECT public.record_audit_outbox_event")
        )
        self.assertEqual(audit_sql, "SELECT public.record_audit_outbox_event(%s, %s, %s, %s, %s, %s)")
        assert audit_parameters is not None
        envelope = json.loads(audit_parameters[3])
        self.assertEqual(envelope["type"], "orgmetra.people.employment_created")
        self.assertEqual(envelope["orgmetraconfirmation"], "human_confirmation:review-88")
        self.assertEqual(audit_parameters[4], sha256(audit_parameters[3].encode("utf-8")).hexdigest())

    def test_position_requires_parents_and_records_audit(self) -> None:
        port, cursor = self._port([[(ORGANIZATION, JOB, RECORDED_AT)]])
        result = create_position_record(
            principal=PRINCIPAL,
            command=position_command(),
            purpose_code="job_architecture_admin",
            policy=position_policy(),
            mutation_port=port,
        )
        self.assertEqual(result.position_record_id, POSITION)
        sql_text = "\n".join(sql for sql, _parameters in cursor.executions)
        self.assertIn("public.organization_unit", sql_text)
        self.assertIn("public.position_record", sql_text)
        self.assertIn("public.record_audit_outbox_event", sql_text)
        self.assertIn("public.people_mutation_idempotency_record", sql_text)
        self.assertNotIn("candidate_worker_link", sql_text)

    def test_assignment_reuses_kernel_and_conversion_then_audits(self) -> None:
        prior_assignment = (
            UUID("0198a412-8200-7000-8000-000000000071"),
            EMPLOYMENT,
            PERSON,
            POSITION,
            Decimal("0.2500"),
            date(2026, 8, 1),
            date(2026, 8, 10),
            RECORDED_AT,
            None,
        )
        port, cursor = self._port(
            [[(CONVERSION, RECORDED_AT)]],
            [[covering_employment_row()], [covering_position_row()], [prior_assignment]],
        )
        result = create_assignment_record(
            principal=PRINCIPAL,
            command=assignment_command(),
            purpose_code="workforce_admin",
            policy=assignment_policy(),
            mutation_port=port,
        )
        self.assertEqual(result.assignment_record_id, ASSIGNMENT)
        sql_text = "\n".join(sql for sql, _parameters in cursor.executions)
        self.assertIn("public.candidate_worker_conversion_record", sql_text)
        conversion_sql = next(
            sql for sql, _parameters in cursor.executions if "candidate_worker_conversion_record" in sql
        )
        self.assertIn("conversion.recorded_to IS NULL", conversion_sql)
        self.assertIn("public.assignment_record", sql_text)
        self.assertIn("public.record_audit_outbox_event", sql_text)
        self.assertIn("public.people_mutation_idempotency_record", sql_text)
        self.assertNotIn("candidate_worker_link", sql_text)

    def test_missing_or_invalid_conversion_fails_before_insert(self) -> None:
        scenarios = (
            [[]],
            [[(CONVERSION, RECORDED_AT), (CONVERSION, RECORDED_AT)]],
            [[(CONVERSION,)]],
            [[(UUID(int=0), RECORDED_AT)]],
        )
        for rows in scenarios:
            with self.subTest(rows=rows):
                port, cursor = self._port(rows)
                with self.assertRaises(PeopleMutationIntegrityError):
                    create_employment_record(
                        principal=PRINCIPAL,
                        command=employment_command(),
                        purpose_code="workforce_admin",
                        policy=employment_policy(),
                        mutation_port=port,
                    )
                self.assertFalse(any("INSERT INTO public.employment_record" in sql for sql, _parameters in cursor.executions))

    def test_invalid_existing_employment_row_fails_closed(self) -> None:
        port, _cursor = self._port([[(CONVERSION, RECORDED_AT)]], [[("bad",)]])
        with self.assertRaisesRegex(PeopleMutationIntegrityError, "invalid shape"):
            create_employment_record(
                principal=PRINCIPAL,
                command=employment_command(),
                purpose_code="workforce_admin",
                policy=employment_policy(),
                mutation_port=port,
            )

    def test_overlapping_exclusive_employment_fails_closed(self) -> None:
        existing = (
            UUID("0198a412-8200-7000-8000-000000000099"),
            UUID("0198a412-8200-7000-8000-000000000098"),
            PERSON,
            "active",
            "exclusive",
            date(2026, 8, 1),
            None,
            RECORDED_AT,
            None,
        )
        port, cursor = self._port([[(CONVERSION, RECORDED_AT)]], [[existing]])
        with self.assertRaises(PeopleMutationIntegrityError):
            create_employment_record(
                principal=PRINCIPAL,
                command=employment_command(),
                purpose_code="workforce_admin",
                policy=employment_policy(),
                mutation_port=port,
            )
        self.assertFalse(any("INSERT INTO public.employment_record" in sql for sql, _parameters in cursor.executions))

    def test_missing_position_parents_are_not_found(self) -> None:
        port, _cursor = self._port([[]])
        with self.assertRaises(PeopleMutationNotFound):
            create_position_record(
                principal=PRINCIPAL,
                command=position_command(),
                purpose_code="job_architecture_admin",
                policy=position_policy(),
                mutation_port=port,
            )

    def test_ambiguous_or_mismatched_position_parents_fail_closed(self) -> None:
        cases = (
            [[(ORGANIZATION, JOB, RECORDED_AT), (ORGANIZATION, JOB, RECORDED_AT)]],
            [[(ORGANIZATION,)]],
            [[(JOB, ORGANIZATION, RECORDED_AT)]],
        )
        for rows in cases:
            with self.subTest(rows=rows):
                port, _cursor = self._port(rows)
                with self.assertRaises(PeopleMutationIntegrityError):
                    create_position_record(
                        principal=PRINCIPAL,
                        command=position_command(),
                        purpose_code="job_architecture_admin",
                        policy=position_policy(),
                        mutation_port=port,
                    )

    def test_assignment_kernel_rejection_and_invalid_rows_fail_closed(self) -> None:
        port, cursor = self._port([[(CONVERSION, RECORDED_AT)]], [[], [], []])
        with self.assertRaises(PeopleMutationIntegrityError):
            create_assignment_record(
                principal=PRINCIPAL,
                command=assignment_command(),
                purpose_code="workforce_admin",
                policy=assignment_policy(),
                mutation_port=port,
            )
        self.assertFalse(any("INSERT INTO public.assignment_record" in sql for sql, _parameters in cursor.executions))

        port, _cursor = self._port([[(CONVERSION, RECORDED_AT)]], [[("bad",)], [], []])
        with self.assertRaises(PeopleMutationIntegrityError):
            create_assignment_record(
                principal=PRINCIPAL,
                command=assignment_command(),
                purpose_code="workforce_admin",
                policy=assignment_policy(),
                mutation_port=port,
            )

        port, _cursor = self._port(
            [[(CONVERSION, RECORDED_AT)]],
            [[covering_employment_row()], [("bad",)], []],
        )
        with self.assertRaises(PeopleMutationIntegrityError):
            create_assignment_record(
                principal=PRINCIPAL,
                command=assignment_command(),
                purpose_code="workforce_admin",
                policy=assignment_policy(),
                mutation_port=port,
            )

        port, _cursor = self._port(
            [[(CONVERSION, RECORDED_AT)]],
            [[covering_employment_row()], [covering_position_row()], [("bad",)]],
        )
        with self.assertRaises(PeopleMutationIntegrityError):
            create_assignment_record(
                principal=PRINCIPAL,
                command=assignment_command(),
                purpose_code="workforce_admin",
                policy=assignment_policy(),
                mutation_port=port,
            )

    def test_forged_authorization_and_typed_commands_are_required(self) -> None:
        calls = 0

        def factory() -> FakeConnection:
            nonlocal calls
            calls += 1
            return FakeConnection(ScriptedCursor([[(CONVERSION, RECORDED_AT)]], [[]]))

        port = PostgresPeopleMutationPort(factory)
        with self.assertRaisesRegex(PeopleMutationIntegrityError, "authorization"):
            port.create_employment(command=employment_command(), authorization=object())  # type: ignore[arg-type]
        denied = issued_authorization(
            tenant_record_id=TENANT,
            actor_reference=ACTOR,
            resource_reference=f"employment_record:{EMPLOYMENT.hex}",
            policy_version_code="people-mutation-v1",
            purpose_code="workforce_admin",
            operation_code="create_record",
            resource_kind="employment_record",
            requested_fields=frozenset({"employment_record"}),
            required_scope_code="orgmetra.people.write",
            granted_scope_codes=frozenset({"orgmetra.people.read"}),
        )
        self.assertFalse(denied.allowed)
        with self.assertRaisesRegex(PeopleMutationIntegrityError, "authorization"):
            port.create_employment(command=employment_command(), authorization=denied)
        with self.assertRaisesRegex(TypeError, "EmploymentMutationCommand"):
            port.create_employment(command=object(), authorization=employment_authorization())  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "PositionMutationCommand"):
            port.create_position(command=object(), authorization=position_authorization())  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "AssignmentMutationCommand"):
            port.create_assignment(command=object(), authorization=assignment_authorization())  # type: ignore[arg-type]
        self.assertEqual(calls, 0)
        with self.assertRaisesRegex(TypeError, "connection_factory"):
            PostgresPeopleMutationPort(None)  # type: ignore[arg-type]

    def test_invalid_version_cell_values_fail_closed(self) -> None:
        bad_employment = (
            EMPLOYMENT,
            EMPLOYMENT_VERSION,
            PERSON,
            "active",
            "exclusive",
            "2026-08-01",
            None,
            RECORDED_AT,
            None,
        )
        port, _cursor = self._port([[(CONVERSION, RECORDED_AT)]], [[bad_employment]])
        with self.assertRaisesRegex(PeopleMutationIntegrityError, "invalid"):
            create_employment_record(
                principal=PRINCIPAL,
                command=employment_command(),
                purpose_code="workforce_admin",
                policy=employment_policy(),
                mutation_port=port,
            )
        bad_position = (POSITION, POSITION_VERSION, "open", "2026-08-01", None, RECORDED_AT, None)
        port, _cursor = self._port(
            [[(CONVERSION, RECORDED_AT)]],
            [[covering_employment_row()], [bad_position], []],
        )
        with self.assertRaisesRegex(PeopleMutationIntegrityError, "invalid"):
            create_assignment_record(
                principal=PRINCIPAL,
                command=assignment_command(),
                purpose_code="workforce_admin",
                policy=assignment_policy(),
                mutation_port=port,
            )
        bad_assignment = (
            ASSIGNMENT,
            EMPLOYMENT,
            PERSON,
            POSITION,
            "1.0000",
            date(2026, 8, 1),
            None,
            RECORDED_AT,
            None,
        )
        port, _cursor = self._port(
            [[(CONVERSION, RECORDED_AT)]],
            [[covering_employment_row()], [covering_position_row()], [bad_assignment]],
        )
        with self.assertRaisesRegex(PeopleMutationIntegrityError, "invalid"):
            create_assignment_record(
                principal=PRINCIPAL,
                command=assignment_command(),
                purpose_code="workforce_admin",
                policy=assignment_policy(),
                mutation_port=port,
            )

    def test_same_key_replays_without_second_hris_or_audit_facts(self) -> None:
        employment_digest = mutation_command_digest(
            command=employment_command(),
            authorization=employment_authorization(),
        )
        port, cursor = self._port([], replay_row=(EMPLOYMENT, employment_digest))
        result = create_employment_record(
            principal=PRINCIPAL,
            command=employment_command(
                employment_record_id=UUID("0198a412-8200-7000-8000-000000000033"),
                audit_event_record_id=UUID("0198a412-8200-7000-8000-000000000088"),
                outbox_delivery_record_id=UUID("0198a412-8200-7000-8000-000000000089"),
            ),
            purpose_code="workforce_admin",
            policy=employment_policy(),
            mutation_port=port,
        )
        self.assertEqual(result.employment_record_id, EMPLOYMENT)
        sql_text = "\n".join(sql for sql, _parameters in cursor.executions)
        self.assertFalse(any("INSERT INTO public.employment_record" in sql for sql, _ in cursor.executions))
        self.assertNotIn("record_audit_outbox_event", sql_text)
        self.assertFalse(
            any("INSERT INTO public.people_mutation_idempotency_record" in sql for sql, _ in cursor.executions)
        )

        position_digest = mutation_command_digest(
            command=position_command(),
            authorization=position_authorization(),
        )
        port, cursor = self._port([], replay_row=(POSITION, position_digest))
        position = create_position_record(
            principal=PRINCIPAL,
            command=position_command(position_record_id=UUID("0198a412-8200-7000-8000-000000000044")),
            purpose_code="job_architecture_admin",
            policy=position_policy(),
            mutation_port=port,
        )
        self.assertEqual(position.position_record_id, POSITION)
        self.assertFalse(any("INSERT INTO public.position_record" in sql for sql, _ in cursor.executions))

        assignment_digest = mutation_command_digest(
            command=assignment_command(),
            authorization=assignment_authorization(),
        )
        port, cursor = self._port([], replay_row=(ASSIGNMENT, assignment_digest))
        assignment = create_assignment_record(
            principal=PRINCIPAL,
            command=assignment_command(assignment_record_id=UUID("0198a412-8200-7000-8000-000000000077")),
            purpose_code="workforce_admin",
            policy=assignment_policy(),
            mutation_port=port,
        )
        self.assertEqual(assignment.assignment_record_id, ASSIGNMENT)
        self.assertFalse(any("INSERT INTO public.assignment_record" in sql for sql, _ in cursor.executions))

    def test_same_key_different_command_fails_closed(self) -> None:
        digest = mutation_command_digest(
            command=employment_command(),
            authorization=employment_authorization(),
        )
        port, cursor = self._port([], replay_row=(EMPLOYMENT, digest))
        with self.assertRaisesRegex(PeopleMutationIntegrityError, "different command"):
            create_employment_record(
                principal=PRINCIPAL,
                command=employment_command(employment_status_code="leave"),
                purpose_code="workforce_admin",
                policy=employment_policy(),
                mutation_port=port,
            )
        self.assertFalse(any("INSERT INTO public.employment_record" in sql for sql, _ in cursor.executions))
        self.assertFalse(any("record_audit_outbox_event" in sql for sql, _ in cursor.executions))

    def test_different_key_is_a_new_command(self) -> None:
        other_employment = UUID("0198a412-8200-7000-8000-000000000034")
        other_version = UUID("0198a412-8200-7000-8000-000000000035")
        other_audit = UUID("0198a412-8200-7000-8000-00000000008a")
        other_outbox = UUID("0198a412-8200-7000-8000-00000000008b")
        cursor = ScriptedCursor(
            [[], [(CONVERSION, RECORDED_AT)], [], [(CONVERSION, RECORDED_AT)]],
            [[], []],
        )
        connection = FakeConnection(cursor)
        port = PostgresPeopleMutationPort(lambda: connection)
        first = create_employment_record(
            principal=PRINCIPAL,
            command=employment_command(),
            purpose_code="workforce_admin",
            policy=employment_policy(),
            mutation_port=port,
        )
        second = create_employment_record(
            principal=PRINCIPAL,
            command=employment_command(
                employment_record_id=other_employment,
                employment_record_version_id=other_version,
                audit_event_record_id=other_audit,
                outbox_delivery_record_id=other_outbox,
                idempotency_key="idempotency-key-29xx",
            ),
            purpose_code="workforce_admin",
            policy=employment_policy(),
            mutation_port=port,
        )
        self.assertEqual(first.employment_record_id, EMPLOYMENT)
        self.assertEqual(second.employment_record_id, other_employment)
        employment_inserts = [sql for sql, _ in cursor.executions if sql.startswith("INSERT INTO public.employment_record (")]
        audit_inserts = [sql for sql, _ in cursor.executions if sql.startswith("SELECT public.record_audit_outbox_event")]
        idempotency_inserts = [
            sql for sql, _ in cursor.executions if "INSERT INTO public.people_mutation_idempotency_record" in sql
        ]
        self.assertEqual(len(employment_inserts), 2)
        self.assertEqual(len(audit_inserts), 2)
        self.assertEqual(len(idempotency_inserts), 2)

    def test_invalid_idempotency_rows_fail_closed(self) -> None:
        cases = (
            [(EMPLOYMENT, "digest"), (EMPLOYMENT, "digest")],
            [(EMPLOYMENT,)],
            [(UUID(int=0), "a" * 64)],
            [(EMPLOYMENT, 17)],
        )
        for rows in cases:
            with self.subTest(rows=rows):
                port, cursor = self._port([], replay_row=rows[0] if len(rows) == 1 else None)
                if len(rows) != 1:
                    cursor.fetchmany_rows = [rows]
                with self.assertRaisesRegex(PeopleMutationIntegrityError, "invalid"):
                    create_employment_record(
                        principal=PRINCIPAL,
                        command=employment_command(),
                        purpose_code="workforce_admin",
                        policy=employment_policy(),
                        mutation_port=port,
                    )
                self.assertFalse(any("INSERT INTO public.employment_record" in sql for sql, _ in cursor.executions))


if __name__ == "__main__":
    unittest.main()
