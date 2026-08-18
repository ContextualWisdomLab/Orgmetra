"""Regression contracts for current People mutation review findings.

These tests intentionally exercise the public/application boundaries rather than
accepting review narration as evidence.  They cover complete evidence-version
validation, exact assignment precision, serialized durable idempotency, and the
confirmed-hire idempotency contract.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest
from uuid import UUID

from orgmetra_people_api.hire import HireAcceptanceCommand
from orgmetra_people_api.mutation_http import _InvalidHttpRequest, _evidence_version
from orgmetra_people_api.postgres_mutations import _LOOKUP_IDEMPOTENCY_SQL
from test_people_mutations import assignment_command


class CurrentReviewRegressionTests(unittest.TestCase):
    """Pin the exact data-integrity boundaries identified by current review."""

    def test_every_evidence_reference_requires_a_string_version(self) -> None:
        """Do not admit trailing unversioned or malformed evidence references."""
        valid_first = {"evidence_version_code": "decision_evidence_set:v1"}
        invalid_references = (
            {},
            {"evidence_version_code": 17},
            "not-a-mapping",
        )
        for invalid in invalid_references:
            with self.subTest(invalid=invalid), self.assertRaises(_InvalidHttpRequest):
                _evidence_version(
                    {
                        "evidence_references": [valid_first, invalid],
                    }
                )

    def test_assignment_command_rejects_more_than_four_decimal_places(self) -> None:
        """Prevent semantic digests from carrying precision the database cannot store."""
        with self.assertRaises(ValueError):
            assignment_command(allocation_ratio=Decimal("0.12345"))

    def test_idempotency_lookup_serializes_same_key_transactions(self) -> None:
        """The pre-write lookup must hold a transaction lock for one command key."""
        normalized = " ".join(_LOOKUP_IDEMPOTENCY_SQL.lower().split())
        self.assertIn("pg_advisory_xact_lock", normalized)
        self.assertIn("hashtextextended", normalized)
        self.assertIn("tenant_record_id", normalized)
        self.assertIn("command_route", normalized)
        self.assertIn("idempotency_key", normalized)

    def test_confirmed_hire_command_carries_validated_idempotency_key(self) -> None:
        """Confirmed-hire retries need the same durable key boundary as other writes."""
        command = HireAcceptanceCommand(
            tenant_record_id=UUID("0198a412-8000-7000-8000-000000000001"),
            candidate_profile_id=UUID("0198a412-8000-7000-8000-000000000002"),
            selection_decision_id=UUID("0198a412-8000-7000-8000-000000000003"),
            person_record_id=UUID("0198a412-8000-7000-8000-000000000004"),
            person_name_record_id=UUID("0198a412-8000-7000-8000-000000000005"),
            employment_record_id=UUID("0198a412-8000-7000-8000-000000000006"),
            employment_record_version_id=UUID("0198a412-8000-7000-8000-000000000007"),
            candidate_worker_conversion_record_id=UUID("0198a412-8000-7000-8000-000000000008"),
            audit_event_record_id=UUID("0198a412-8000-7000-8000-000000000009"),
            outbox_delivery_record_id=UUID("0198a412-8000-7000-8000-00000000000a"),
            effective_from=date(2026, 8, 18),
            display_name="Regression Worker",
            employment_status_code="active",
            idempotency_key="hire-idempotency-key-17",
        )
        self.assertEqual(command.idempotency_key, "hire-idempotency-key-17")
        with self.assertRaises(ValueError):
            HireAcceptanceCommand(
                tenant_record_id=command.tenant_record_id,
                candidate_profile_id=command.candidate_profile_id,
                selection_decision_id=command.selection_decision_id,
                person_record_id=command.person_record_id,
                person_name_record_id=command.person_name_record_id,
                employment_record_id=command.employment_record_id,
                employment_record_version_id=command.employment_record_version_id,
                candidate_worker_conversion_record_id=command.candidate_worker_conversion_record_id,
                audit_event_record_id=command.audit_event_record_id,
                outbox_delivery_record_id=command.outbox_delivery_record_id,
                effective_from=command.effective_from,
                display_name=command.display_name,
                employment_status_code=command.employment_status_code,
                idempotency_key="short",
            )


if __name__ == "__main__":
    unittest.main()
