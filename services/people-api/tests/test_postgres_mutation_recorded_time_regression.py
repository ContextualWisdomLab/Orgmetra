"""Regression contracts for post-lock People mutation recorded-time cutoffs."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
import unittest
from uuid import UUID

from orgmetra_people_api.mutations import (
    PeopleMutationIntegrityError,
    create_assignment_record,
    create_employment_record,
)
from orgmetra_people_api.postgres_mutations import PostgresPeopleMutationPort
from test_postgres_people_mutations import (
    ASSIGNMENT,
    CONVERSION,
    EMPLOYMENT,
    PERSON,
    POSITION,
    PRINCIPAL,
    RECORDED_AT,
    FakeConnection,
    ScriptedCursor,
    assignment_command,
    assignment_policy,
    covering_employment_row,
    covering_position_row,
    employment_command,
    employment_policy,
)

_POST_LOCK_CLOCK_SQL = "SELECT pg_catalog.clock_timestamp()"


class ClockRowsCursor(ScriptedCursor):
    """Allow malformed database-clock rows without changing the shared happy-path fake."""

    def __init__(self, clock_rows: list[tuple[object, ...]]) -> None:
        super().__init__([[], [(CONVERSION, RECORDED_AT)]], [[]])
        self.clock_rows = list(clock_rows)

    def fetchmany(self, size: int) -> list[tuple[object, ...]]:
        if self._clock_result_pending:
            self._clock_result_pending = False
            return self.clock_rows[:size]
        return super().fetchmany(size)


class PostLockRecordedTimeRegressionTests(unittest.TestCase):
    """Prevent lock wait order from hiding the winner at the validation cutoff."""

    def test_employment_rejects_winner_recorded_after_waiter_transaction_started(self) -> None:
        """A later lock winner must be visible after the converted-person lock is acquired."""
        winner_recorded_at = RECORDED_AT + timedelta(seconds=1)
        winner = (
            UUID("0198a412-8200-7000-8000-000000000099"),
            UUID("0198a412-8200-7000-8000-000000000098"),
            PERSON,
            "active",
            "exclusive",
            date(2026, 8, 1),
            None,
            winner_recorded_at,
            None,
        )
        cursor = ScriptedCursor(
            [[], [(CONVERSION, RECORDED_AT)]],
            [[winner]],
            clock_timestamp=winner_recorded_at,
        )
        port = PostgresPeopleMutationPort(lambda: FakeConnection(cursor))

        with self.assertRaises(PeopleMutationIntegrityError):
            create_employment_record(
                principal=PRINCIPAL,
                command=employment_command(),
                purpose_code="workforce_admin",
                policy=employment_policy(),
                mutation_port=port,
            )

        sql = [statement for statement, _parameters in cursor.executions]
        conversion_index = next(
            index for index, statement in enumerate(sql) if "candidate_worker_conversion_record" in statement
        )
        clock_index = sql.index(_POST_LOCK_CLOCK_SQL)
        employment_snapshot_index = next(
            index for index, statement in enumerate(sql) if "JOIN public.employment_record_version" in statement
        )
        self.assertLess(conversion_index, clock_index)
        self.assertLess(clock_index, employment_snapshot_index)

    def test_assignment_rejects_capacity_winner_recorded_after_waiter_transaction_started(self) -> None:
        """A later lock winner must be visible after the position lock is acquired."""
        winner_recorded_at = RECORDED_AT + timedelta(seconds=1)
        winner = (
            UUID("0198a412-8200-7000-8000-000000000071"),
            EMPLOYMENT,
            PERSON,
            POSITION,
            Decimal("1.0000"),
            date(2026, 8, 18),
            None,
            winner_recorded_at,
            None,
        )
        cursor = ScriptedCursor(
            [[], [(CONVERSION, RECORDED_AT)]],
            [[covering_employment_row()], [covering_position_row()], [winner]],
            clock_timestamp=winner_recorded_at,
        )
        port = PostgresPeopleMutationPort(lambda: FakeConnection(cursor))

        with self.assertRaises(PeopleMutationIntegrityError):
            create_assignment_record(
                principal=PRINCIPAL,
                command=assignment_command(assignment_record_id=ASSIGNMENT),
                purpose_code="workforce_admin",
                policy=assignment_policy(),
                mutation_port=port,
            )

        sql = [statement for statement, _parameters in cursor.executions]
        position_lock_index = next(
            index for index, statement in enumerate(sql) if "FOR UPDATE OF position" in statement
        )
        clock_index = sql.index(_POST_LOCK_CLOCK_SQL)
        assignment_snapshot_index = next(
            index for index, statement in enumerate(sql) if statement.startswith("SELECT\n    assignment.assignment_record_id")
        )
        self.assertLess(position_lock_index, clock_index)
        self.assertLess(clock_index, assignment_snapshot_index)

    def test_employment_fails_closed_on_invalid_post_lock_database_clock_rows(self) -> None:
        """Malformed or non-aware clock evidence must never fall back to transaction start time."""
        scenarios: tuple[list[tuple[object, ...]], ...] = (
            [],
            [(RECORDED_AT,), (RECORDED_AT,)],
            [(RECORDED_AT, "unexpected")],
            [("2026-08-18T00:01:00Z",)],
        )
        for clock_rows in scenarios:
            with self.subTest(clock_rows=clock_rows):
                cursor = ClockRowsCursor(clock_rows)
                port = PostgresPeopleMutationPort(lambda: FakeConnection(cursor))
                with self.assertRaisesRegex(PeopleMutationIntegrityError, "post-lock database clock"):
                    create_employment_record(
                        principal=PRINCIPAL,
                        command=employment_command(),
                        purpose_code="workforce_admin",
                        policy=employment_policy(),
                        mutation_port=port,
                    )
                self.assertFalse(
                    any(
                        statement.startswith("INSERT INTO public.employment_record (")
                        for statement, _parameters in cursor.executions
                    )
                )


if __name__ == "__main__":
    unittest.main()
