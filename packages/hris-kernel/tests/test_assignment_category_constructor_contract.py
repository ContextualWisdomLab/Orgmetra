"""Regression for explicit Assignment category construction semantics."""

from datetime import date, datetime, timezone
from decimal import Decimal
import unittest
from uuid import UUID

from orgmetra_hris_kernel import AssignmentFact, DateInterval, RecordedInterval


class AssignmentCategoryConstructorContractTests(unittest.TestCase):
    """Keep legacy classification confined to explicit restoration/fixture paths."""

    def test_public_assignment_fact_requires_explicit_category(self) -> None:
        """Reject omission instead of silently creating a new legacy-unspecified fact."""
        with self.assertRaises(TypeError):
            AssignmentFact(
                tenant_record_id=UUID("10000000-0000-7000-8000-000000000101"),
                assignment_record_id=UUID("10000000-0000-7000-8000-000000000301"),
                employment_record_id=UUID("10000000-0000-7000-8000-000000000104"),
                person_record_id=UUID("10000000-0000-7000-8000-000000000102"),
                position_record_id=UUID("10000000-0000-7000-8000-000000000106"),
                allocation_ratio=Decimal("1.0000"),
                effective=DateInterval(date(2024, 3, 1)),
                recorded=RecordedInterval(datetime(2024, 3, 1, 16, tzinfo=timezone.utc)),
            )


if __name__ == "__main__":
    unittest.main()
