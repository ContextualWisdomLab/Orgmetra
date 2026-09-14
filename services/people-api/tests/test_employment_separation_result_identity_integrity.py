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
    """Require receipt identities to remain stable and retained storage to fail closed."""

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

    def test_low_level_tuple_fabrication_is_revalidated_on_use(self) -> None:
        """Bypassing the public constructor must not create trusted receipt authority."""
        forged = tuple.__new__(
            EmploymentSeparationResult,
            (True, _VERSION.int, _RECORDED_AT, False),
        )

        with self.assertRaisesRegex(ValueError, "employment_record_id"):
            _ = forged.employment_record_id

    def test_low_level_tuple_length_fabrication_is_rejected(self) -> None:
        """Malformed retained storage must fail before any receipt property is returned."""
        forged = tuple.__new__(EmploymentSeparationResult, (_EMPLOYMENT.int,))

        with self.assertRaisesRegex(ValueError, "storage is invalid"):
            _ = forged.replayed


if __name__ == "__main__":
    unittest.main()
