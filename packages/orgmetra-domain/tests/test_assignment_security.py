"""Regression tests for assignment numeric safety and client-safe errors."""

from datetime import date, datetime, timezone
from decimal import Decimal
import unittest
from uuid import UUID

from orgmetra_domain import (
    AllocationExceededError,
    AssignmentRecord,
    BitemporalPeriod,
    InvalidDomainValueError,
    validate_assignment_portfolio,
)


PERSON_ID = UUID("00000000-0000-7000-8000-000000000001")
POSITION_ID = UUID("00000000-0000-7000-8000-000000000004")
OTHER_POSITION_ID = UUID("00000000-0000-7000-8000-000000000005")


def _assignment(assignment_id: int, allocation: str, start: date) -> AssignmentRecord:
    """Build one open-ended assignment for focused regression tests."""

    return AssignmentRecord(
        assignment_record_id=UUID(
            f"00000000-0000-7000-8000-{assignment_id:012d}"
        ),
        person_record_id=PERSON_ID,
        position_record_id=POSITION_ID if assignment_id % 2 else OTHER_POSITION_ID,
        allocation_ratio=Decimal(allocation),
        period=BitemporalPeriod(
            effective_from=start,
            effective_to=None,
            recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc),
            recorded_to=None,
        ),
    )


class AssignmentSecurityRegressionTests(unittest.TestCase):
    """Keep assignment validation deterministic and free of HR data leakage."""

    def test_non_finite_allocations_fail_with_stable_domain_error(self) -> None:
        for ratio in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(ratio=ratio), self.assertRaisesRegex(
                InvalidDomainValueError, "allocation_ratio"
            ):
                _assignment(31, ratio, date(2026, 1, 1))

    def test_overallocation_error_omits_person_ratio_and_effective_date(self) -> None:
        assignments = [
            _assignment(31, "0.7", date(2026, 1, 1)),
            _assignment(32, "0.4", date(2026, 2, 1)),
        ]

        with self.assertRaises(AllocationExceededError) as captured:
            validate_assignment_portfolio(assignments)

        message = str(captured.exception)
        self.assertEqual(
            message,
            "assignment portfolio allocation exceeds allowed maximum",
        )
        for sensitive_value in (str(PERSON_ID), "1.1", "2026-02-01"):
            self.assertNotIn(sensitive_value, message)


if __name__ == "__main__":
    unittest.main()
