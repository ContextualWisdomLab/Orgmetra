"""Regression contracts for PostgreSQL connection capability binding."""

from __future__ import annotations

from contextlib import nullcontext
import unittest

from orgmetra_people_api.postgres_hire import PostgresHireAcceptancePort
from orgmetra_people_api.postgres_mutations import PostgresPeopleMutationPort


class PostgresConnectionCapabilityBindingTests(unittest.TestCase):
    """Prove accepted database capabilities cannot be replaced after validation."""

    def _assert_factory_remains_bound(self, port_type: type[object]) -> None:
        calls: list[str] = []

        def accepted_factory():
            calls.append("accepted")
            return nullcontext(object())

        def replacement_factory():
            calls.append("replacement")
            return nullcontext(object())

        port = port_type(accepted_factory)
        try:
            object.__setattr__(port, "connection_factory", replacement_factory)
        except (AttributeError, TypeError):
            pass

        self.assertIs(port.connection_factory, accepted_factory)
        with port.connection_factory():
            pass
        self.assertEqual(calls, ["accepted"])

    def test_hire_port_keeps_the_exact_validated_connection_factory(self) -> None:
        """Retained hire-port references cannot redirect later database execution."""
        self._assert_factory_remains_bound(PostgresHireAcceptancePort)

    def test_people_mutation_port_keeps_the_exact_validated_connection_factory(self) -> None:
        """Retained mutation-port references cannot redirect later database execution."""
        self._assert_factory_remains_bound(PostgresPeopleMutationPort)


if __name__ == "__main__":
    unittest.main()
