"""Regression contract for Assignment correction adapter runtime evidence types."""

from __future__ import annotations

import unittest

from orgmetra_keyverse_adapter import AuthorizationDecision
from orgmetra_people_api.assignment_correction_mutations import (
    AssignmentCorrectionMutationCommand,
    assignment_correction_command_digest,
)
from orgmetra_people_api.mutations import PeopleMutationIntegrityError
from orgmetra_people_api.postgres_assignment_corrections import PostgresAssignmentCorrectionMutationPort
from test_assignment_correction_mutations import ForgedCorrectionCommand, correction_command
from test_postgres_assignment_corrections import correction_authorization


class ForgedAuthorizationDecision(AuthorizationDecision):
    """Represent caller-defined authorization evidence at the persistence boundary."""


def forged_command() -> AssignmentCorrectionMutationCommand:
    """Return a valid-value command whose runtime type is caller-controlled."""
    command = correction_command()
    return ForgedCorrectionCommand(
        tenant_record_id=command.tenant_record_id,
        predecessor_assignment_record_id=command.predecessor_assignment_record_id,
        replacement_assignment_record_id=command.replacement_assignment_record_id,
        assignment_supersession_record_id=command.assignment_supersession_record_id,
        audit_event_record_id=command.audit_event_record_id,
        outbox_delivery_record_id=command.outbox_delivery_record_id,
        corrected_category_code=command.corrected_category_code,
        confirmation_reference=command.confirmation_reference,
        evidence_version_code=command.evidence_version_code,
        idempotency_key=command.idempotency_key,
    )


def forged_authorization() -> AuthorizationDecision:
    """Return valid-value allow evidence whose runtime type is caller-controlled."""
    decision = correction_authorization()
    return ForgedAuthorizationDecision(
        allowed=decision.allowed,
        tenant_record_id=decision.tenant_record_id,
        actor_reference=decision.actor_reference,
        resource_reference=decision.resource_reference,
        policy_version_code=decision.policy_version_code,
        purpose_code=decision.purpose_code,
        operation_code=decision.operation_code,
        resource_kind=decision.resource_kind,
        requested_fields=decision.requested_fields,
        authorized_fields=decision.authorized_fields,
        reason_code=decision.reason_code,
        next_action=decision.next_action,
    )


class ExplodingConnectionFactory:
    """Prove malformed runtime evidence is rejected before database access."""

    def __init__(self) -> None:
        """Start with no attempted connection."""
        self.calls = 0

    def __call__(self) -> object:
        """Fail if the persistence boundary reaches the database factory."""
        self.calls += 1
        raise AssertionError("database connection must not be opened")


class AssignmentCorrectionAdapterRuntimeIntegrityTests(unittest.TestCase):
    """Reject caller-defined command and authorization subtypes before replay or I/O."""

    def test_digest_rejects_command_subtype(self) -> None:
        """Do not hash semantic fields through a caller-defined command runtime type."""
        with self.assertRaisesRegex(TypeError, "exact AssignmentCorrectionMutationCommand"):
            assignment_correction_command_digest(
                command=forged_command(),
                authorization=correction_authorization(),
            )

    def test_digest_rejects_authorization_subtype(self) -> None:
        """Do not hash actor or purpose fields through caller-defined authorization evidence."""
        with self.assertRaisesRegex(TypeError, "exact AuthorizationDecision"):
            assignment_correction_command_digest(
                command=correction_command(),
                authorization=forged_authorization(),
            )

    def test_postgres_port_rejects_command_subtype_before_connection(self) -> None:
        """Reject a command subtype before transaction or tenant context setup."""
        factory = ExplodingConnectionFactory()
        port = PostgresAssignmentCorrectionMutationPort(factory)

        with self.assertRaisesRegex(TypeError, "exact AssignmentCorrectionMutationCommand"):
            port.correct_assignment_category(
                command=forged_command(),
                authorization=correction_authorization(),
            )

        self.assertEqual(factory.calls, 0)

    def test_postgres_port_rejects_authorization_subtype_before_connection(self) -> None:
        """Reject forged allow evidence before transaction or tenant context setup."""
        factory = ExplodingConnectionFactory()
        port = PostgresAssignmentCorrectionMutationPort(factory)

        with self.assertRaisesRegex(PeopleMutationIntegrityError, "exact authorization decision"):
            port.correct_assignment_category(
                command=correction_command(),
                authorization=forged_authorization(),
            )

        self.assertEqual(factory.calls, 0)


if __name__ == "__main__":
    unittest.main()
