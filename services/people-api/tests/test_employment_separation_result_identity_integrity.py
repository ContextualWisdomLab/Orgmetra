"""Structural identity integrity for Employment separation application receipts."""

from __future__ import annotations

from datetime import datetime, timezone
import unittest
from uuid import UUID

from orgmetra_people_api.separation import EmploymentSeparationResult

_EMPLOYMENT = UUID("0198a412-9000-7000-8000-000000000030")
_VERSION = UUID("0198a412-9000-7000-8000-000000000032")
_OTHER = UUID("0198a412-9000-7000-8000-000000000099")
_RECORDED_AT = datetime(2026, 9, 15, 0, 9, tzinfo=timezone.utc)


class EmploymentSeparationResultIdentityIntegrityTests(unittest.TestCase):
    """Require receipt identities to remain stable after a returned UUID view is mutated."""

    def test_returned_uuid_view_cannot_mutate_retained_receipt_identity(self) -> None:
        """Receipt identity authority must not be the UUID object handed to a consumer."""
        result = EmploymentSeparationResult(
            employment_record_id=_EMPLOYMENT,
            separated_employment_record_version_id=_VERSION,
            recorded_at=_RECORDED_AT,
            replayed=False,
        )

        first_view = result.employment_record_id
        object.__setattr__(first_view, "int", _OTHER.int)
        second_view = result.employment_record_id

        self.assertEqual(second_view, _EMPLOYMENT)
        self.assertIsNot(first_view, second_view)
        self.assertEqual(result.separated_employment_record_version_id, _VERSION)


if __name__ == "__main__":
    unittest.main()
