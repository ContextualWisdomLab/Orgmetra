"""Regression contract for unhashable direct People status values."""

from __future__ import annotations

import unittest

from test_people_mutations import employment_command, position_command


class UnhashableStatusRegressionTests(unittest.TestCase):
    """Require stable ValueError input failures instead of set-membership TypeError."""

    def test_commands_reject_unhashable_status_values_as_value_errors(self) -> None:
        """Normalize malformed integration values before closed-set membership checks."""
        cases = (
            lambda: employment_command(employment_status_code=[]),
            lambda: employment_command(employment_concurrency_code={}),
            lambda: position_command(position_status_code=[]),
        )
        for builder in cases:
            with self.subTest(builder=builder), self.assertRaises(ValueError):
                builder()


if __name__ == "__main__":
    unittest.main()
