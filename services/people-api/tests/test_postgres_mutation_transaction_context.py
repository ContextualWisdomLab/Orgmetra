"""Reject core People writes that cannot prove an actual PostgreSQL transaction."""

from __future__ import annotations

import unittest

from orgmetra_people_api.postgres_mutations import PostgresPeopleMutationPort
from test_people_mutations import assignment_command, employment_command, position_command
from test_postgres_people_mutations import (
    assignment_authorization,
    employment_authorization,
    position_authorization,
)

_MISSING = object()


class _Connection:
    """Expose only the transaction-mode evidence needed by this boundary contract."""

    def __init__(self, autocommit: object = False) -> None:
        if autocommit is not _MISSING:
            self.autocommit = autocommit
        self.cursor_calls = 0

    def __enter__(self) -> _Connection:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def cursor(self) -> object:
        self.cursor_calls += 1
        raise AssertionError("cursor acquired before exact transaction-context proof")


class PostgresMutationTransactionContextTests(unittest.TestCase):
    """Require Employment, Position, and Assignment writes to fail before SQL."""

    def test_rejects_unproven_transaction_context_before_cursor_acquisition(self) -> None:
        operations = (
            (
                "employment",
                lambda port: port.create_employment(
                    command=employment_command(),
                    authorization=employment_authorization(),
                ),
            ),
            (
                "position",
                lambda port: port.create_position(
                    command=position_command(),
                    authorization=position_authorization(),
                ),
            ),
            (
                "assignment",
                lambda port: port.create_assignment(
                    command=assignment_command(),
                    authorization=assignment_authorization(),
                ),
            ),
        )
        invalid_modes = (
            ("autocommit", True),
            ("unknown", None),
            ("integer_false", 0),
            ("text_false", "false"),
            ("missing", _MISSING),
        )

        for operation_name, operation in operations:
            for mode_name, autocommit in invalid_modes:
                connection = _Connection(autocommit)
                port = PostgresPeopleMutationPort(lambda: connection)
                with self.subTest(operation=operation_name, mode=mode_name), self.assertRaisesRegex(
                    RuntimeError,
                    "People mutations require autocommit disabled",
                ):
                    operation(port)
                self.assertEqual(connection.cursor_calls, 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
