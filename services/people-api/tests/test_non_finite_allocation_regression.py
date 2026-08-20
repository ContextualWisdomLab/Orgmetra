"""Regression contract for non-finite direct assignment allocation values."""

from __future__ import annotations

from decimal import Decimal
import unittest

from test_people_mutations import assignment_command


class NonFiniteAllocationRegressionTests(unittest.TestCase):
    """Require the application command boundary to normalize non-finite decimals."""

    def test_assignment_command_rejects_non_finite_ratios_as_value_errors(self) -> None:
        """Do not leak decimal arithmetic/type exceptions from malformed command input."""
        for token in ("NaN", "sNaN", "Infinity", "-Infinity"):
            with self.subTest(token=token), self.assertRaisesRegex(ValueError, "finite"):
                assignment_command(allocation_ratio=Decimal(token))


if __name__ == "__main__":
    unittest.main()
