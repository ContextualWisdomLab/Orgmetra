"""Executable contract for atomic PostgreSQL Assignment category corrections."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDecision
from orgmetra_people_api.assignment_correction_mutations import (
    assignment_correction_command_digest,
    correct_assignment_record_category,
)
from orgmetra_people_api.mutations import PeopleMutationIntegrityError
from orgmetra_people_api.postgres_assignment_corrections import PostgresAssignmentCorrectionMutationPort
from test_assignment_correction_mutations import (
    IDEMPOTENCY,
    PREDECESSOR,
    REPLACEMENT,
    SUPERSESSION,
    TENANT,
    PRINCIPAL,
    correction_command,
    correction_policy,
)
from test_people_mutations import EMPLOYMENT, EMPLOYMENT_VERSION, PERSON, POSITION, POSITION_VERSION
from test_postgres_people_mutations import FakeConnection, ScriptedCursor

RECORDED_START = datetime(2026, 9, 3, 0, 1, tzinfo=timezone.utc)
CORRECTED_AT = datetime(2026, 9, 3, 0, 2, tzinfo=timezone.utc)
ACTOR = "keyverse_subject:operator-17"


def correction_authorization() -> AuthorizationDecision:
    """Return the exact allow decision produced by the correction policy."""
    return AuthorizationDecision(
        allowed=True,
        tenant_record_id=TENANT,
        actor_reference=ACTOR,
        resource_reference=f"assignment_record:{PREDECESSOR.hex}",
        policy_version_code="assignment-correction-v1",
        purpose_code="workforce_admin",
        operation_code="correct_record",
        resource_kind="assignment_record",
        requested_fields=frozenset({"assignment_category_code"}),
        authorized_fields=frozenset({"assignment_category_code"}),
        reason_code="access_permitted",
        next_action="continue",
    )


def predecessor_row() -> tuple[object, ...]:
    """Return one recorded-open primary Assignment eligible for correction."""
    return (
        PREDECESSOR,
        EMPLOYMENT,
        PERSON,
        POSITION,
        Decimal("0.5000"),
        "primary",
        date(2026, 8, 1),
        None,
        RECORDED_START,
        None,
    )


def employment_row() -> tuple[object, ...]:
    """Return one active Employment version covering the Assignment effective time."""
    return (
        EMPLOYMENT,
        EMPLOYMENT_VERSION,
        PERSON,
        "active",
        "exclusive",
        date(2026, 8, 1),
        None,
        RECORDED_START,
        None,
    )


def position_row() -> tuple[object, ...]:
    """Return one open Position version covering the Assignment effective time."""
    return (
        POSITION,
        POSITION_VERSION,
        "open",
        date(2026, 8, 1),
        None,
        RECORDED_START,
        None,
    )


class PostgresAssignmentCorrectionMutationTests(unittest.TestCase):
    """Prove locking, revalidation, replay, provenance, audit, and rollback boundaries."""

    def test_correction_locks_revalidates_and_commits_linked_evidence_atomically(self) -> None:
        cursor = ScriptedCursor(
            [[], [predecessor_row()]],
            [[employment_row()], [position_row()], [predecessor_row()]],
            clock_timestamp=CORRECTED_AT,
        )
        connection = FakeConnection(cursor)
        port = PostgresAssignmentCorrectionMutationPort(lambda: connection)

        result = correct_assignment_record_category(
            principal=PRINCIPAL,
            command=correction_command(),
            purpose_code="workforce_admin",
            policy=correction_policy(),
            mutation_port=port,
        )

        self.assertEqual(result.replacement_assignment_record_id, REPLACEMENT)
        self.assertEqual(result.assignment_supersession_record_id, SUPERSESSION)
        sql = [statement for statement, _parameters in cursor.executions]
        predecessor_read = next(
            i
            for i, statement in enumerate(sql)
            if "assignment.assignment_record_id = %s" in statement and "LIMIT 2" in statement
        )
        employment_lock = next(i for i, statement in enumerate(sql) if "FOR UPDATE OF employment" in statement)
        position_lock = next(i for i, statement in enumerate(sql) if "FOR UPDATE OF position" in statement)
        portfolio_lock = next(
            i
            for i, statement in enumerate(sql)
            if "OR assignment.position_record_id = %s" in statement
        )
        clock_read = sql.index("SELECT pg_catalog.clock_timestamp()")
        close_write = next(i for i, statement in enumerate(sql) if statement.startswith("UPDATE public.assignment_record"))
        replacement_write = next(
            i
            for i, statement in enumerate(sql)
            if statement.startswith("INSERT INTO public.assignment_record (")
        )
        supersession_write = next(
            i
            for i, statement in enumerate(sql)
            if statement.startswith("INSERT INTO public.assignment_supersession_record")
        )
        audit_write = next(i for i, statement in enumerate(sql) if "record_audit_outbox_event" in statement)
        replay_write = next(
            i
            for i, statement in enumerate(sql)
            if statement.startswith("INSERT INTO public.people_mutation_idempotency_record")
        )
        self.assertNotIn("FOR UPDATE", sql[predecessor_read])
        self.assertIn("ORDER BY assignment.assignment_record_id", sql[portfolio_lock])
        self.assertLess(predecessor_read, employment_lock)
        self.assertLess(employment_lock, position_lock)
        self.assertLess(position_lock, portfolio_lock)
        self.assertLess(portfolio_lock, clock_read)
        self.assertLess(clock_read, close_write)
        self.assertLess(close_write, replacement_write)
        self.assertLess(replacement_write, supersession_write)
        self.assertLess(supersession_write, audit_write)
        self.assertLess(audit_write, replay_write)
        self.assertEqual(cursor.fetchall_rows, [])
        close_parameters = cursor.executions[close_write][1]
        assert close_parameters is not None
        self.assertEqual(close_parameters, (CORRECTED_AT, TENANT, PREDECESSOR))
        self.assertIsNone(connection.exit_exception)

    def test_matching_replay_returns_committed_replacement_and_supersession_without_new_writes(self) -> None:
        digest = assignment_correction_command_digest(
            command=correction_command(),
            authorization=correction_authorization(),
        )
        cursor = ScriptedCursor(
            [[(REPLACEMENT, digest)], [(SUPERSESSION, REPLACEMENT)]],
            [],
            clock_timestamp=CORRECTED_AT,
        )
        port = PostgresAssignmentCorrectionMutationPort(lambda: FakeConnection(cursor))

        result = correct_assignment_record_category(
            principal=PRINCIPAL,
            command=correction_command(
                replacement_assignment_record_id=UUID("0198a412-8000-7000-8000-000000000091"),
                assignment_supersession_record_id=UUID("0198a412-8000-7000-8000-000000000092"),
                audit_event_record_id=UUID("0198a412-8000-7000-8000-000000000093"),
                outbox_delivery_record_id=UUID("0198a412-8000-7000-8000-000000000094"),
            ),
            purpose_code="workforce_admin",
            policy=correction_policy(),
            mutation_port=port,
        )

        self.assertEqual(result.replacement_assignment_record_id, REPLACEMENT)
        self.assertEqual(result.assignment_supersession_record_id, SUPERSESSION)
        sql_text = "\n".join(statement for statement, _parameters in cursor.executions)
        self.assertNotIn("UPDATE public.assignment_record", sql_text)
        self.assertNotIn("INSERT INTO public.assignment_record (", sql_text)
        self.assertNotIn("record_audit_outbox_event", sql_text)

    def test_same_key_with_changed_semantics_fails_before_authoritative_locks(self) -> None:
        digest = assignment_correction_command_digest(
            command=correction_command(),
            authorization=correction_authorization(),
        )
        cursor = ScriptedCursor([[(REPLACEMENT, digest)]], [], clock_timestamp=CORRECTED_AT)
        connection = FakeConnection(cursor)
        port = PostgresAssignmentCorrectionMutationPort(lambda: connection)

        with self.assertRaisesRegex(PeopleMutationIntegrityError, "different command"):
            correct_assignment_record_category(
                principal=PRINCIPAL,
                command=correction_command(
                    corrected_category_code="primary",
                    idempotency_key=IDEMPOTENCY,
                ),
                purpose_code="workforce_admin",
                policy=correction_policy(),
                mutation_port=port,
            )

        sql_text = "\n".join(statement for statement, _parameters in cursor.executions)
        self.assertNotIn("FOR UPDATE OF assignment", sql_text)
        self.assertNotIn("UPDATE public.assignment_record", sql_text)
        self.assertIs(connection.exit_exception, PeopleMutationIntegrityError)

    def test_missing_predecessor_rolls_back_before_close_or_provenance(self) -> None:
        cursor = ScriptedCursor([[], []], [], clock_timestamp=CORRECTED_AT)
        connection = FakeConnection(cursor)
        port = PostgresAssignmentCorrectionMutationPort(lambda: connection)

        with self.assertRaises(PeopleMutationIntegrityError):
            correct_assignment_record_category(
                principal=PRINCIPAL,
                command=correction_command(),
                purpose_code="workforce_admin",
                policy=correction_policy(),
                mutation_port=port,
            )

        sql_text = "\n".join(statement for statement, _parameters in cursor.executions)
        self.assertNotIn("UPDATE public.assignment_record", sql_text)
        self.assertNotIn("INSERT INTO public.assignment_supersession_record", sql_text)
        self.assertIs(connection.exit_exception, PeopleMutationIntegrityError)

    def test_failed_portfolio_revalidation_rolls_back_before_any_correction_write(self) -> None:
        cursor = ScriptedCursor(
            [[], [predecessor_row()]],
            [[], [position_row()], [predecessor_row()]],
            clock_timestamp=CORRECTED_AT,
        )
        connection = FakeConnection(cursor)
        port = PostgresAssignmentCorrectionMutationPort(lambda: connection)

        with self.assertRaises(PeopleMutationIntegrityError):
            correct_assignment_record_category(
                principal=PRINCIPAL,
                command=correction_command(),
                purpose_code="workforce_admin",
                policy=correction_policy(),
                mutation_port=port,
            )

        sql_text = "\n".join(statement for statement, _parameters in cursor.executions)
        self.assertNotIn("UPDATE public.assignment_record", sql_text)
        self.assertNotIn("INSERT INTO public.assignment_record (", sql_text)
        self.assertNotIn("INSERT INTO public.assignment_supersession_record", sql_text)
        self.assertIs(connection.exit_exception, PeopleMutationIntegrityError)


if __name__ == "__main__":
    unittest.main()
