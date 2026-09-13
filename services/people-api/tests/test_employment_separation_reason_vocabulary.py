"""Governed reason-code contract for authoritative Employment separation."""

from __future__ import annotations

from datetime import date
import unittest
from uuid import UUID

from orgmetra_people_api.separation import EmploymentSeparationCommand

TENANT = UUID("0198a412-8000-7000-8000-000000000001")
PERSON = UUID("0198a412-8000-7000-8000-000000000020")
EMPLOYMENT = UUID("0198a412-8000-7000-8000-000000000030")
EXPECTED_VERSION = UUID("0198a412-8000-7000-8000-000000000031")
AUDIT_EVENT = UUID("0198a412-8000-7000-8000-000000000080")
OUTBOX = UUID("0198a412-8000-7000-8000-000000000081")

REVIEWED_REASON_CODES = (
    "voluntary_resignation",
    "retirement_transition",
    "fixed_term_completion",
    "position_elimination",
    "employer_initiated_separation",
)


def command(reason_code: str) -> EmploymentSeparationCommand:
    """Build one otherwise-valid separation command for reason-code validation."""
    return EmploymentSeparationCommand(
        tenant_record_id=TENANT,
        person_record_id=PERSON,
        employment_record_id=EMPLOYMENT,
        expected_employment_record_version_id=EXPECTED_VERSION,
        separation_effective_on=date(2026, 10, 1),
        separation_reason_code=reason_code,
        evidence_reference="separation_packet:case-17",
        evidence_version_code="v1",
        confirmation_reference="human_confirmation:case-17",
        idempotency_key="employment-separation-case-17",
        audit_event_record_id=AUDIT_EVENT,
        outbox_delivery_record_id=OUTBOX,
    )


class EmploymentSeparationReasonVocabularyTests(unittest.TestCase):
    """Keep mutation reasons value-free and inside the reviewed People vocabulary."""

    def test_accepts_each_reviewed_reason_code(self) -> None:
        for reason_code in REVIEWED_REASON_CODES:
            with self.subTest(reason_code=reason_code):
                self.assertEqual(command(reason_code).separation_reason_code, reason_code)

    def test_rejects_unreviewed_lower_snake_case_reason(self) -> None:
        with self.assertRaisesRegex(ValueError, "approved separation reason"):
            command("manager_notes_compensation_case")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
