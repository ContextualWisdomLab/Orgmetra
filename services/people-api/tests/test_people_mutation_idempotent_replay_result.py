"""Result-receipt regressions for idempotent generic People mutation replay."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_people_api.mutations import (
    AssignmentMutationCommand,
    AssignmentMutationResult,
    EmploymentMutationCommand,
    EmploymentMutationResult,
    PeopleMutationIntegrityError,
    PositionMutationCommand,
    PositionMutationResult,
    create_assignment_record,
    create_employment_record,
    create_position_record,
    mutation_command_digest,
)
from test_people_mutations import (
    ASSIGNMENT,
    EMPLOYMENT,
    POSITION,
    PRINCIPAL,
    assignment_command,
    assignment_policy,
    employment_command,
    employment_policy,
    position_command,
    position_policy,
)

NEW_EMPLOYMENT = UUID("0198a412-8200-7000-8000-000000000033")
NEW_POSITION = UUID("0198a412-8200-7000-8000-000000000044")
NEW_ASSIGNMENT = UUID("0198a412-8200-7000-8000-000000000077")


class ReplayReceiptPort:
    """Return first-committed identities with independently checkable replay evidence."""

    def __init__(self, *, digest_override: str | None = None) -> None:
        self.digest_override = digest_override

    def _digest(self, *, command: object, authorization: object) -> str:
        digest = mutation_command_digest(command=command, authorization=authorization)  # type: ignore[arg-type]
        return self.digest_override if self.digest_override is not None else digest

    def create_employment(self, *, command: EmploymentMutationCommand, authorization: object) -> EmploymentMutationResult:
        return EmploymentMutationResult(
            employment_record_id=EMPLOYMENT,
            replay_command_digest=self._digest(command=command, authorization=authorization),
        )

    def create_position(self, *, command: PositionMutationCommand, authorization: object) -> PositionMutationResult:
        return PositionMutationResult(
            position_record_id=POSITION,
            replay_command_digest=self._digest(command=command, authorization=authorization),
        )

    def create_assignment(self, *, command: AssignmentMutationCommand, authorization: object) -> AssignmentMutationResult:
        return AssignmentMutationResult(
            assignment_record_id=ASSIGNMENT,
            replay_command_digest=self._digest(command=command, authorization=authorization),
        )


class PeopleMutationIdempotentReplayResultTests(unittest.TestCase):
    """Reconcile first-committed replay identity with result-integrity hardening."""

    def test_matching_replay_receipt_may_return_first_committed_identity(self) -> None:
        port = ReplayReceiptPort()

        employment = create_employment_record(
            principal=PRINCIPAL,
            command=employment_command(employment_record_id=NEW_EMPLOYMENT),
            purpose_code="workforce_admin",
            policy=employment_policy(),
            mutation_port=port,
        )
        position = create_position_record(
            principal=PRINCIPAL,
            command=position_command(position_record_id=NEW_POSITION),
            purpose_code="job_architecture_admin",
            policy=position_policy(),
            mutation_port=port,
        )
        assignment = create_assignment_record(
            principal=PRINCIPAL,
            command=assignment_command(assignment_record_id=NEW_ASSIGNMENT),
            purpose_code="workforce_admin",
            policy=assignment_policy(),
            mutation_port=port,
        )

        self.assertEqual(employment.employment_record_id, EMPLOYMENT)
        self.assertEqual(position.position_record_id, POSITION)
        self.assertEqual(assignment.assignment_record_id, ASSIGNMENT)

    def test_foreign_identity_with_mismatched_replay_digest_fails_closed(self) -> None:
        with self.assertRaisesRegex(PeopleMutationIntegrityError, "replay evidence"):
            create_employment_record(
                principal=PRINCIPAL,
                command=employment_command(employment_record_id=NEW_EMPLOYMENT),
                purpose_code="workforce_admin",
                policy=employment_policy(),
                mutation_port=ReplayReceiptPort(digest_override="0" * 64),
            )

    def test_replay_digest_must_be_an_exact_string(self) -> None:
        with self.assertRaisesRegex(ValueError, "replay_command_digest"):
            EmploymentMutationResult(
                employment_record_id=EMPLOYMENT,
                replay_command_digest=object(),  # type: ignore[arg-type]
            )


if __name__ == "__main__":
    unittest.main()
