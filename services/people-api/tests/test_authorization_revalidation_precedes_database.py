"""Regressions proving corrupted authorization evidence cannot acquire a DB connection."""

from __future__ import annotations

import unittest

from orgmetra_people_api.hire import HireDecisionIntegrityError
from orgmetra_people_api.mutations import PeopleMutationIntegrityError, mutation_command_digest
from orgmetra_people_api.postgres_hire import PostgresHireAcceptancePort, _hire_command_digest
from orgmetra_people_api.postgres_mutations import PostgresPeopleMutationPort
from test_people_mutations import assignment_command, employment_command, position_command
from test_postgres_hire_acceptance import allowed_authorization, command as hire_command
from test_postgres_people_mutations import (
    assignment_authorization,
    employment_authorization,
    position_authorization,
)


def _contradict(decision: object) -> object:
    """Corrupt a field not used by the old local allow/matching predicates."""
    object.__setattr__(decision, "reason_code", "access_denied")
    return decision


class CountingConnectionFactory:
    """Fail if a persistence path asks for a connection after invalid evidence."""

    def __init__(self) -> None:
        self.call_count = 0

    def __call__(self) -> object:
        self.call_count += 1
        raise AssertionError("database connection must not be acquired")


class AuthorizationRevalidationBeforeDatabaseTests(unittest.TestCase):
    """Keep semantic authorization validation ahead of every People SQL boundary."""

    def test_hire_port_rejects_corruption_before_connection_factory(self) -> None:
        """Confirmed-hire persistence must reject invalid evidence before SQL setup."""
        factory = CountingConnectionFactory()
        port = PostgresHireAcceptancePort(factory)

        with self.assertRaises(HireDecisionIntegrityError):
            port.accept_hire(
                command=hire_command(),
                authorization=_contradict(allowed_authorization()),  # type: ignore[arg-type]
            )

        self.assertEqual(factory.call_count, 0)

    def test_employment_port_rejects_corruption_before_connection_factory(self) -> None:
        """Employment persistence must reject invalid evidence before SQL setup."""
        factory = CountingConnectionFactory()
        port = PostgresPeopleMutationPort(factory)

        with self.assertRaises(PeopleMutationIntegrityError):
            port.create_employment(
                command=employment_command(),
                authorization=_contradict(employment_authorization()),  # type: ignore[arg-type]
            )

        self.assertEqual(factory.call_count, 0)

    def test_position_port_rejects_corruption_before_connection_factory(self) -> None:
        """Position persistence must reject invalid evidence before SQL setup."""
        factory = CountingConnectionFactory()
        port = PostgresPeopleMutationPort(factory)

        with self.assertRaises(PeopleMutationIntegrityError):
            port.create_position(
                command=position_command(),
                authorization=_contradict(position_authorization()),  # type: ignore[arg-type]
            )

        self.assertEqual(factory.call_count, 0)

    def test_assignment_port_rejects_corruption_before_connection_factory(self) -> None:
        """Assignment persistence must reject invalid evidence before SQL setup."""
        factory = CountingConnectionFactory()
        port = PostgresPeopleMutationPort(factory)

        with self.assertRaises(PeopleMutationIntegrityError):
            port.create_assignment(
                command=assignment_command(),
                authorization=_contradict(assignment_authorization()),  # type: ignore[arg-type]
            )

        self.assertEqual(factory.call_count, 0)

    def test_generic_digest_revalidates_before_reading_corrupt_evidence(self) -> None:
        """Idempotency hashing must reject contradictory decision data before hashing it."""
        with self.assertRaises(ValueError):
            mutation_command_digest(
                command=employment_command(),
                authorization=_contradict(employment_authorization()),  # type: ignore[arg-type]
            )

    def test_hire_digest_revalidates_before_reading_corrupt_evidence(self) -> None:
        """Hire replay hashing must reject contradictory decision data before hashing it."""
        with self.assertRaises(ValueError):
            _hire_command_digest(
                hire_command(),
                _contradict(allowed_authorization()),  # type: ignore[arg-type]
            )


if __name__ == "__main__":
    unittest.main()
