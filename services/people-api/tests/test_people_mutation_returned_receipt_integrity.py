"""Structural-integrity regressions for returned People mutation receipts."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_people_api.mutations import (
    AssignmentMutationResult,
    EmploymentMutationResult,
    PositionMutationResult,
)

EMPLOYMENT = UUID("0198a412-c100-7000-8000-000000000030")
POSITION = UUID("0198a412-c100-7000-8000-000000000040")
ASSIGNMENT = UUID("0198a412-c100-7000-8000-000000000070")
OTHER = UUID("0198a412-c100-7000-8000-000000000099")


class PeopleMutationReturnedReceiptIntegrityTests(unittest.TestCase):
    """Require accepted receipt identity authority to remain immutable after return."""

    def _assert_identity_is_structural(
        self,
        *,
        result: object,
        field_name: str,
        expected_identity: UUID,
    ) -> None:
        """Mutating one returned UUID view must not rewrite retained receipt authority."""
        first_view = getattr(result, field_name)
        object.__setattr__(first_view, "int", OTHER.int)
        self.assertEqual(getattr(result, field_name), expected_identity)
        self.assertIsNot(getattr(result, field_name), first_view)
        with self.assertRaises(AttributeError):
            object.__setattr__(result, field_name, OTHER)

    def test_employment_receipt_identity_is_structurally_immutable(self) -> None:
        """Employment receipt identity must survive mutation of a previously returned UUID view."""
        self._assert_identity_is_structural(
            result=EmploymentMutationResult(employment_record_id=EMPLOYMENT),
            field_name="employment_record_id",
            expected_identity=EMPLOYMENT,
        )

    def test_position_receipt_identity_is_structurally_immutable(self) -> None:
        """Position receipt identity must survive mutation of a previously returned UUID view."""
        self._assert_identity_is_structural(
            result=PositionMutationResult(position_record_id=POSITION),
            field_name="position_record_id",
            expected_identity=POSITION,
        )

    def test_assignment_receipt_identity_is_structurally_immutable(self) -> None:
        """Assignment receipt identity must survive mutation of a previously returned UUID view."""
        self._assert_identity_is_structural(
            result=AssignmentMutationResult(assignment_record_id=ASSIGNMENT),
            field_name="assignment_record_id",
            expected_identity=ASSIGNMENT,
        )


if __name__ == "__main__":
    unittest.main()
