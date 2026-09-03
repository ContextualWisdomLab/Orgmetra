"""Executable contract for purpose-bound Assignment category correction commands."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_people_api.assignment_correction_mutations import (
    AssignmentCorrectionMutationCommand,
    AssignmentCorrectionMutationPort,
    AssignmentCorrectionMutationResult,
    assignment_correction_command_digest,
    correct_assignment_record_category,
)
from orgmetra_people_api.auth import AuthenticatedPrincipal

TENANT = UUID("0198a412-8000-7000-8000-000000000001")
PREDECESSOR = UUID("0198a412-8000-7000-8000-000000000070")
REPLACEMENT = UUID("0198a412-8000-7000-8000-000000000071")
SUPERSESSION = UUID("0198a412-8000-7000-8000-000000000072")
AUDIT_EVENT = UUID("0198a412-8000-7000-8000-000000000080")
OUTBOX = UUID("0198a412-8000-7000-8000-000000000081")
CONFIRMATION = "human_confirmation:assignment-category-review-88"
EVIDENCE = "assignment_category_review:v1"
IDEMPOTENCY = "assignment-correction-17xx"


class ForgedUUID(UUID):
    """Represent executable UUID behavior at the application trust boundary."""


class ForgedString(str):
    """Represent executable string behavior at the application trust boundary."""


class ForgedCorrectionCommand(AssignmentCorrectionMutationCommand):
    """Represent caller-defined command subtype behavior at the service boundary."""


def correction_command(**overrides: object) -> AssignmentCorrectionMutationCommand:
    """Build one deterministic category-correction command."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "predecessor_assignment_record_id": PREDECESSOR,
        "replacement_assignment_record_id": REPLACEMENT,
        "assignment_supersession_record_id": SUPERSESSION,
        "audit_event_record_id": AUDIT_EVENT,
        "outbox_delivery_record_id": OUTBOX,
        "corrected_category_code": "concurrent_secondary",
        "confirmation_reference": CONFIRMATION,
        "evidence_version_code": EVIDENCE,
        "idempotency_key": IDEMPOTENCY,
    }
    values.update(overrides)
    return AssignmentCorrectionMutationCommand(**values)  # type: ignore[arg-type]


def correction_policy(*, purpose_code: str = "workforce_admin") -> PurposeBoundAccessPolicy:
    """Return the exact purpose-bound correction policy."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="assignment-correction-v1",
        resource_kind="assignment_record",
        purpose_code=purpose_code,
        operation_code="correct_record",
        required_scope_code="orgmetra.people.write",
        permitted_fields=frozenset({"assignment_category_code"}),
    )


PRINCIPAL = AuthenticatedPrincipal(
    tenant_record_id=TENANT,
    actor_reference="keyverse_subject:operator-17",
    granted_scope_codes=frozenset({"orgmetra.people.write"}),
)


class RecordingCorrectionPort:
    """Capture the exact authorized command without persisting HRIS truth."""

    def __init__(self) -> None:
        """Initialize an empty authorized-call ledger."""
        self.calls: list[tuple[AssignmentCorrectionMutationCommand, object]] = []

    def correct_assignment_category(
        self,
        *,
        command: AssignmentCorrectionMutationCommand,
        authorization: object,
    ) -> AssignmentCorrectionMutationResult:
        """Record one authorized correction call."""
        self.calls.append((command, authorization))
        return AssignmentCorrectionMutationResult(
            replacement_assignment_record_id=command.replacement_assignment_record_id,
            assignment_supersession_record_id=command.assignment_supersession_record_id,
        )


class InvalidResultPort(RecordingCorrectionPort):
    """Return an invalid adapter result for service-boundary regression."""

    def correct_assignment_category(
        self,
        *,
        command: AssignmentCorrectionMutationCommand,
        authorization: object,
    ) -> object:
        """Return a value outside the governed port contract."""
        del command, authorization
        return object()


class AssignmentCorrectionMutationTests(unittest.TestCase):
    """Prove correction authority, evidence, identity, and replay semantics."""

    def test_authorizes_exact_predecessor_category_field_before_persistence(self) -> None:
        """Authorize only the predecessor Assignment category before invoking persistence."""
        port = RecordingCorrectionPort()
        result = correct_assignment_record_category(
            principal=PRINCIPAL,
            command=correction_command(),
            purpose_code="workforce_admin",
            policy=correction_policy(),
            mutation_port=port,
        )

        self.assertIsInstance(port, AssignmentCorrectionMutationPort)
        self.assertEqual(result.replacement_assignment_record_id, REPLACEMENT)
        self.assertEqual(result.assignment_supersession_record_id, SUPERSESSION)
        authorization = port.calls[0][1]
        self.assertEqual(authorization.resource_reference, f"assignment_record:{PREDECESSOR.hex}")
        self.assertEqual(authorization.operation_code, "correct_record")
        self.assertEqual(authorization.requested_fields, frozenset({"assignment_category_code"}))
        self.assertEqual(authorization.authorized_fields, frozenset({"assignment_category_code"}))

    def test_policy_denial_prevents_correction(self) -> None:
        """Do not call persistence when purpose-bound authorization denies the correction."""
        port = RecordingCorrectionPort()
        with self.assertRaises(AuthorizationDeniedError):
            correct_assignment_record_category(
                principal=PRINCIPAL,
                command=correction_command(),
                purpose_code="workforce_admin",
                policy=correction_policy(purpose_code="benefits_admin"),
                mutation_port=port,
            )
        self.assertEqual(port.calls, [])

    def test_command_rejects_malformed_identity_category_and_evidence(self) -> None:
        """Reject malformed trust-bearing command values before authorization."""
        cases = (
            lambda: correction_command(tenant_record_id=UUID(int=0)),
            lambda: correction_command(predecessor_assignment_record_id=UUID(int=(1 << 128) - 1)),
            lambda: correction_command(replacement_assignment_record_id=ForgedUUID(str(REPLACEMENT))),
            lambda: correction_command(assignment_supersession_record_id="not-a-uuid"),
            lambda: correction_command(replacement_assignment_record_id=PREDECESSOR),
            lambda: correction_command(corrected_category_code="legacy_unspecified"),
            lambda: correction_command(corrected_category_code=ForgedString("primary")),
            lambda: correction_command(confirmation_reference="not-namespaced"),
            lambda: correction_command(confirmation_reference=ForgedString(CONFIRMATION)),
            lambda: correction_command(confirmation_reference="human_confirmation:" + "a" * 300),
            lambda: correction_command(evidence_version_code="has space"),
            lambda: correction_command(evidence_version_code=ForgedString(EVIDENCE)),
            lambda: correction_command(evidence_version_code="v" * 201),
            lambda: correction_command(idempotency_key="short"),
            lambda: correction_command(idempotency_key=ForgedString(IDEMPOTENCY)),
            lambda: AssignmentCorrectionMutationResult(
                replacement_assignment_record_id=UUID(int=0),
                assignment_supersession_record_id=SUPERSESSION,
            ),
        )
        for builder in cases:
            with self.subTest(builder=builder), self.assertRaises(ValueError):
                builder()

    def test_command_accepts_exact_high_impact_metadata_limits(self) -> None:
        """Accept confirmation and evidence metadata exactly at their governed maxima."""
        confirmation_reference = "human_confirmation:" + "a" * 281
        evidence_version_code = "v" * 200

        command = correction_command(
            confirmation_reference=confirmation_reference,
            evidence_version_code=evidence_version_code,
        )

        self.assertEqual(len(command.confirmation_reference), 300)
        self.assertEqual(len(command.evidence_version_code), 200)

    def test_digest_binds_semantics_but_excludes_generated_correction_ids(self) -> None:
        """Keep semantic replay stable across retry-generated correction identities."""
        port = RecordingCorrectionPort()
        correct_assignment_record_category(
            principal=PRINCIPAL,
            command=correction_command(),
            purpose_code="workforce_admin",
            policy=correction_policy(),
            mutation_port=port,
        )
        authorization = port.calls[0][1]
        first = assignment_correction_command_digest(
            command=correction_command(),
            authorization=authorization,
        )
        retried = assignment_correction_command_digest(
            command=correction_command(
                replacement_assignment_record_id=UUID("0198a412-8000-7000-8000-000000000091"),
                assignment_supersession_record_id=UUID("0198a412-8000-7000-8000-000000000092"),
                audit_event_record_id=UUID("0198a412-8000-7000-8000-000000000093"),
                outbox_delivery_record_id=UUID("0198a412-8000-7000-8000-000000000094"),
            ),
            authorization=authorization,
        )
        changed_category = assignment_correction_command_digest(
            command=correction_command(corrected_category_code="primary"),
            authorization=authorization,
        )
        changed_confirmation = assignment_correction_command_digest(
            command=correction_command(confirmation_reference="human_confirmation:assignment-category-review-89"),
            authorization=authorization,
        )
        self.assertEqual(first, retried)
        self.assertNotEqual(first, changed_category)
        self.assertNotEqual(first, changed_confirmation)

    def test_service_requires_typed_command_port_and_result(self) -> None:
        """Reject ungoverned command types, ports, results, and command subtypes."""
        forged_command = ForgedCorrectionCommand(
            tenant_record_id=TENANT,
            predecessor_assignment_record_id=PREDECESSOR,
            replacement_assignment_record_id=REPLACEMENT,
            assignment_supersession_record_id=SUPERSESSION,
            audit_event_record_id=AUDIT_EVENT,
            outbox_delivery_record_id=OUTBOX,
            corrected_category_code="concurrent_secondary",
            confirmation_reference=CONFIRMATION,
            evidence_version_code=EVIDENCE,
            idempotency_key=IDEMPOTENCY,
        )
        with self.assertRaisesRegex(TypeError, "exact AssignmentCorrectionMutationCommand"):
            correct_assignment_record_category(
                principal=PRINCIPAL,
                command=forged_command,
                purpose_code="workforce_admin",
                policy=correction_policy(),
                mutation_port=RecordingCorrectionPort(),
            )
        with self.assertRaisesRegex(TypeError, "AssignmentCorrectionMutationCommand"):
            correct_assignment_record_category(
                principal=PRINCIPAL,
                command=object(),  # type: ignore[arg-type]
                purpose_code="workforce_admin",
                policy=correction_policy(),
                mutation_port=RecordingCorrectionPort(),
            )
        with self.assertRaisesRegex(TypeError, "AssignmentCorrectionMutationPort"):
            correct_assignment_record_category(
                principal=PRINCIPAL,
                command=correction_command(),
                purpose_code="workforce_admin",
                policy=correction_policy(),
                mutation_port=object(),  # type: ignore[arg-type]
            )
        with self.assertRaisesRegex(TypeError, "AssignmentCorrectionMutationResult"):
            correct_assignment_record_category(
                principal=PRINCIPAL,
                command=correction_command(),
                purpose_code="workforce_admin",
                policy=correction_policy(),
                mutation_port=InvalidResultPort(),  # type: ignore[arg-type]
            )


if __name__ == "__main__":
    unittest.main()
