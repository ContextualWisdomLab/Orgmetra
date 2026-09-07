"""Pre-port semantic snapshot regressions for People mutation replay receipts."""

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
    PRINCIPAL,
    assignment_command,
    assignment_policy,
    employment_command,
    employment_policy,
    position_command,
    position_policy,
)

OTHER = UUID("0198a412-b300-7000-8000-000000000099")


class _SemanticSwitchingReplayPort:
    """Mutate the received command before manufacturing matching replay evidence."""

    def create_employment(
        self,
        *,
        command: EmploymentMutationCommand,
        authorization: object,
    ) -> EmploymentMutationResult:
        """Switch Person semantics while retaining a syntactically valid replay receipt."""
        object.__setattr__(command, "person_record_id", OTHER)
        return EmploymentMutationResult(
            employment_record_id=OTHER,
            replay_command_digest=mutation_command_digest(
                command=command,
                authorization=authorization,  # type: ignore[arg-type]
            ),
        )

    def create_position(
        self,
        *,
        command: PositionMutationCommand,
        authorization: object,
    ) -> PositionMutationResult:
        """Switch Job semantics while retaining a syntactically valid replay receipt."""
        object.__setattr__(command, "job_profile_id", OTHER)
        return PositionMutationResult(
            position_record_id=OTHER,
            replay_command_digest=mutation_command_digest(
                command=command,
                authorization=authorization,  # type: ignore[arg-type]
            ),
        )

    def create_assignment(
        self,
        *,
        command: AssignmentMutationCommand,
        authorization: object,
    ) -> AssignmentMutationResult:
        """Switch Position semantics while retaining a syntactically valid replay receipt."""
        object.__setattr__(command, "position_record_id", OTHER)
        return AssignmentMutationResult(
            assignment_record_id=OTHER,
            replay_command_digest=mutation_command_digest(
                command=command,
                authorization=authorization,  # type: ignore[arg-type]
            ),
        )


class PeopleMutationReplaySemanticSnapshotTests(unittest.TestCase):
    """Require replay verification to use semantics fixed before executable port work."""

    def test_employment_replay_digest_cannot_follow_port_mutated_semantics(self) -> None:
        """Employment replay evidence remains bound to the authorized Person semantics."""
        with self.assertRaisesRegex(PeopleMutationIntegrityError, "replay evidence does not match command"):
            create_employment_record(
                principal=PRINCIPAL,
                command=employment_command(),
                purpose_code="workforce_admin",
                policy=employment_policy(),
                mutation_port=_SemanticSwitchingReplayPort(),
            )

    def test_position_replay_digest_cannot_follow_port_mutated_semantics(self) -> None:
        """Position replay evidence remains bound to the authorized Job semantics."""
        with self.assertRaisesRegex(PeopleMutationIntegrityError, "replay evidence does not match command"):
            create_position_record(
                principal=PRINCIPAL,
                command=position_command(),
                purpose_code="job_architecture_admin",
                policy=position_policy(),
                mutation_port=_SemanticSwitchingReplayPort(),
            )

    def test_assignment_replay_digest_cannot_follow_port_mutated_semantics(self) -> None:
        """Assignment replay evidence remains bound to the authorized Position semantics."""
        with self.assertRaisesRegex(PeopleMutationIntegrityError, "replay evidence does not match command"):
            create_assignment_record(
                principal=PRINCIPAL,
                command=assignment_command(),
                purpose_code="workforce_admin",
                policy=assignment_policy(),
                mutation_port=_SemanticSwitchingReplayPort(),
            )


if __name__ == "__main__":
    unittest.main()
