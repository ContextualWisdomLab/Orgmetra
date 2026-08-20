"""Regression contract for semantic Assignment idempotency digests."""

from __future__ import annotations

from decimal import Decimal
import unittest

from orgmetra_people_api.mutations import mutation_command_digest
from test_people_mutations import assignment_command
from test_postgres_people_mutations import assignment_authorization


class AllocationDigestCanonicalizationTests(unittest.TestCase):
    """Bind numerically identical database ratios to one idempotency command digest."""

    def test_equivalent_decimal_scales_have_one_assignment_digest(self) -> None:
        """Database numeric(5,4) semantics must not depend on Decimal input spelling."""
        authorization = assignment_authorization()
        digests = {
            mutation_command_digest(
                command=assignment_command(allocation_ratio=Decimal(token)),
                authorization=authorization,
            )
            for token in ("0.25", "0.250", "0.2500")
        }
        self.assertEqual(len(digests), 1)


if __name__ == "__main__":
    unittest.main()
