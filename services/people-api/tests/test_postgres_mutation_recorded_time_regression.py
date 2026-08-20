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


if __name__ == "__main__":
    unittest.main()
