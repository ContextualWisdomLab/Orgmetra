"""Regression contract for Assignment correction result runtime integrity."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api.assignment_correction_mutations import (
    AssignmentCorrectionMutationCommand,
    AssignmentCorrectionMutationResult,
    correct_assignment_record_category,
)
from orgmetra_people_api.auth import AuthenticatedPrincipal

TENANT = UUID("0198a412-8000-7000-8000-000000000001")
PREDECESSOR = UUID("0198a412-8000-7000-8000-000000000070")
REPLACEMENT = UUID("0198a412-8000-7000-8000-000000000071")
SUPERSESSION = UUID("0198a412-8000-7000-8000-000000000072")
AUDIT_EVENT = UUID("0198a412-8000-7000-8000-000000000080")
OUTBOX = UUID("0198a412-8000-7000-8000-000000000081")


class ForgedCorrectionResult(AssignmentCorrectionMutationResult):
    """Represent caller-defined executable behavior at the result boundary."""


class ForgedResultPort:
    """Return a subtype instead of the exact governed correction result."""

    def correct_assignment_category(
        self,
        *,
        command: AssignmentCorrectionMutationCommand,
        authorization: object,
    ) -> AssignmentCorrectionMutationResult:
        """Return a structurally valid but caller-defined result subtype."""
        del command, authorization
        return ForgedCorrectionResult(
            replacement_assignment_record_id=REPLACEMENT,
            assignment_supersession_record_id=SUPERSESSION,
        )


class AssignmentCorrectionResultRuntimeIntegrityTests(unittest.TestCase):
    """Keep untrusted result subtypes from crossing the application boundary."""

    def test_service_rejects_result_subtype_after_port_call(self) -> None:
        """Require the exact governed result before HTTP code can consume its fields."""
        principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:operator-17",
            granted_scope_codes=frozenset({"orgmetra.people.write"}),
        )
        policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="assignment-correction-v1",
            resource_kind="assignment_record",
            purpose_code="workforce_admin",
            operation_code="correct_record",
            required_scope_code="orgmetra.people.write",
            permitted_fields=frozenset({"assignment_category_code"}),
        )
        command = AssignmentCorrectionMutationCommand(
            tenant_record_id=TENANT,
            predecessor_assignment_record_id=PREDECESSOR,
            replacement_assignment_record_id=REPLACEMENT,
            assignment_supersession_record_id=SUPERSESSION,
            audit_event_record_id=AUDIT_EVENT,
            outbox_delivery_record_id=OUTBOX,
            corrected_category_code="concurrent_secondary",
            confirmation_reference="human_confirmation:assignment-category-review-88",
            evidence_version_code="assignment_category_review:v1",
            idempotency_key="assignment-correction-17xx",
        )

        with self.assertRaisesRegex(TypeError, "exact AssignmentCorrectionMutationResult"):
            correct_assignment_record_category(
                principal=principal,
                command=command,
                purpose_code="workforce_admin",
                policy=policy,
                mutation_port=ForgedResultPort(),
            )


if __name__ == "__main__":
    unittest.main()
