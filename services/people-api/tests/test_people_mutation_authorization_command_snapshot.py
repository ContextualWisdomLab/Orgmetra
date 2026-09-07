"""Application command-snapshot regressions across purpose-bound authorization."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.mutations import (
    AssignmentMutationCommand,
    AssignmentMutationResult,
    EmploymentMutationCommand,
    EmploymentMutationResult,
    PositionMutationCommand,
    PositionMutationResult,
    create_assignment_record,
    create_employment_record,
    create_position_record,
)

TENANT = UUID("0198a412-c100-7000-8000-000000000001")
PERSON = UUID("0198a412-c100-7000-8000-000000000010")
OTHER_PERSON = UUID("0198a412-c100-7000-8000-000000000011")
EMPLOYMENT = UUID("0198a412-c100-7000-8000-000000000020")
EMPLOYMENT_VERSION = UUID("0198a412-c100-7000-8000-000000000021")
ORGANIZATION = UUID("0198a412-c100-7000-8000-000000000030")
JOB = UUID("0198a412-c100-7000-8000-000000000040")
OTHER_JOB = UUID("0198a412-c100-7000-8000-000000000041")
POSITION = UUID("0198a412-c100-7000-8000-000000000050")
POSITION_VERSION = UUID("0198a412-c100-7000-8000-000000000051")
OTHER_POSITION = UUID("0198a412-c100-7000-8000-000000000052")
ASSIGNMENT = UUID("0198a412-c100-7000-8000-000000000060")
AUDIT_EVENT = UUID("0198a412-c100-7000-8000-000000000070")
OUTBOX = UUID("0198a412-c100-7000-8000-000000000071")
EFFECTIVE_FROM = date(2026, 9, 5)

PRINCIPAL = AuthenticatedPrincipal(
    tenant_record_id=TENANT,
    actor_reference="keyverse_subject:authorization-snapshot-operator",
    granted_scope_codes=frozenset({"orgmetra.people.write"}),
)


class _MutatingResourceKind(str):
    """Rewrite a retained caller command when policy comparison executes."""

    def __new__(
        cls,
        value: str,
        *,
        command: object,
        field_name: str,
        replacement: object,
    ) -> _MutatingResourceKind:
        """Retain the caller command solely for the adversarial comparison callback."""
        instance = super().__new__(cls, value)
        instance.command = command
        instance.field_name = field_name
        instance.replacement = replacement
        return instance

    def _mutate_command(self) -> None:
        """Simulate caller-owned executable policy behavior during authorization."""
        object.__setattr__(self.command, self.field_name, self.replacement)

    def __eq__(self, other: object) -> bool:
        """Mutate before preserving ordinary string equality semantics."""
        self._mutate_command()
        return str.__eq__(self, other)

    def __ne__(self, other: object) -> bool:
        """Mutate before preserving ordinary string inequality semantics."""
        self._mutate_command()
        return str.__ne__(self, other)


class _CapturingMutationPort:
    """Capture the semantic command that crosses the application port boundary."""

    employment_command: EmploymentMutationCommand | None = None
    position_command: PositionMutationCommand | None = None
    assignment_command: AssignmentMutationCommand | None = None

    def create_employment(
        self,
        *,
        command: EmploymentMutationCommand,
        authorization: object,
    ) -> EmploymentMutationResult:
        """Capture Employment semantics and return the commanded target identity."""
        del authorization
        self.employment_command = command
        return EmploymentMutationResult(employment_record_id=command.employment_record_id)

    def create_position(
        self,
        *,
        command: PositionMutationCommand,
        authorization: object,
    ) -> PositionMutationResult:
        """Capture Position semantics and return the commanded target identity."""
        del authorization
        self.position_command = command
        return PositionMutationResult(position_record_id=command.position_record_id)

    def create_assignment(
        self,
        *,
        command: AssignmentMutationCommand,
        authorization: object,
    ) -> AssignmentMutationResult:
        """Capture Assignment semantics and return the commanded target identity."""
        del authorization
        self.assignment_command = command
        return AssignmentMutationResult(assignment_record_id=command.assignment_record_id)


def _policy(
    *,
    resource_kind: str,
    field_name: str,
    command: object,
    command_field_name: str,
    replacement: object,
) -> PurposeBoundAccessPolicy:
    """Build a valid policy whose resource-kind comparison mutates caller state."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="authorization-snapshot-v1",
        resource_kind=_MutatingResourceKind(
            resource_kind,
            command=command,
            field_name=command_field_name,
            replacement=replacement,
        ),
        purpose_code="workforce_admin",
        operation_code="create_record",
        required_scope_code="orgmetra.people.write",
        permitted_fields=frozenset({field_name}),
    )


def _employment_command() -> EmploymentMutationCommand:
    """Build one valid Employment command for authorization interleaving."""
    return EmploymentMutationCommand(
        tenant_record_id=TENANT,
        person_record_id=PERSON,
        employment_record_id=EMPLOYMENT,
        employment_record_version_id=EMPLOYMENT_VERSION,
        audit_event_record_id=AUDIT_EVENT,
        outbox_delivery_record_id=OUTBOX,
        employment_status_code="active",
        employment_concurrency_code="exclusive",
        effective_from=EFFECTIVE_FROM,
        confirmation_reference="human_confirmation:authorization-snapshot",
        evidence_version_code="authorization-snapshot-v1",
        idempotency_key="authorization-snapshot-employment-1",
    )


def _position_command() -> PositionMutationCommand:
    """Build one valid Position command for authorization interleaving."""
    return PositionMutationCommand(
        tenant_record_id=TENANT,
        organization_unit_id=ORGANIZATION,
        job_profile_id=JOB,
        position_record_id=POSITION,
        position_record_version_id=POSITION_VERSION,
        audit_event_record_id=AUDIT_EVENT,
        outbox_delivery_record_id=OUTBOX,
        position_status_code="open",
        effective_from=EFFECTIVE_FROM,
        confirmation_reference="human_confirmation:authorization-snapshot",
        evidence_version_code="authorization-snapshot-v1",
        idempotency_key="authorization-snapshot-position-1",
    )


def _assignment_command() -> AssignmentMutationCommand:
    """Build one valid Assignment command for authorization interleaving."""
    return AssignmentMutationCommand(
        tenant_record_id=TENANT,
        employment_record_id=EMPLOYMENT,
        person_record_id=PERSON,
        position_record_id=POSITION,
        assignment_record_id=ASSIGNMENT,
        audit_event_record_id=AUDIT_EVENT,
        outbox_delivery_record_id=OUTBOX,
        allocation_ratio=Decimal("0.5000"),
        effective_from=EFFECTIVE_FROM,
        confirmation_reference="human_confirmation:authorization-snapshot",
        evidence_version_code="authorization-snapshot-v1",
        idempotency_key="authorization-snapshot-assignment-1",
    )


class PeopleMutationAuthorizationCommandSnapshotTests(unittest.TestCase):
    """Require authorization callbacks to see no caller-owned command authority."""

    def test_employment_port_receives_pre_authorization_semantics(self) -> None:
        """Policy execution may mutate caller state but not the Employment port command."""
        command = _employment_command()
        port = _CapturingMutationPort()
        create_employment_record(
            principal=PRINCIPAL,
            command=command,
            purpose_code="workforce_admin",
            policy=_policy(
                resource_kind="employment_record",
                field_name="employment_record",
                command=command,
                command_field_name="person_record_id",
                replacement=OTHER_PERSON,
            ),
            mutation_port=port,
        )
        self.assertEqual(command.person_record_id, OTHER_PERSON)
        self.assertIsNotNone(port.employment_command)
        assert port.employment_command is not None
        self.assertEqual(port.employment_command.person_record_id, PERSON)
        self.assertIsNot(port.employment_command, command)

    def test_position_port_receives_pre_authorization_semantics(self) -> None:
        """Policy execution may mutate caller state but not the Position port command."""
        command = _position_command()
        port = _CapturingMutationPort()
        create_position_record(
            principal=PRINCIPAL,
            command=command,
            purpose_code="workforce_admin",
            policy=_policy(
                resource_kind="position_record",
                field_name="position_record",
                command=command,
                command_field_name="job_profile_id",
                replacement=OTHER_JOB,
            ),
            mutation_port=port,
        )
        self.assertEqual(command.job_profile_id, OTHER_JOB)
        self.assertIsNotNone(port.position_command)
        assert port.position_command is not None
        self.assertEqual(port.position_command.job_profile_id, JOB)
        self.assertIsNot(port.position_command, command)

    def test_assignment_port_receives_pre_authorization_semantics(self) -> None:
        """Policy execution may mutate caller state but not the Assignment port command."""
        command = _assignment_command()
        port = _CapturingMutationPort()
        create_assignment_record(
            principal=PRINCIPAL,
            command=command,
            purpose_code="workforce_admin",
            policy=_policy(
                resource_kind="assignment_record",
                field_name="assignment_record",
                command=command,
                command_field_name="position_record_id",
                replacement=OTHER_POSITION,
            ),
            mutation_port=port,
        )
        self.assertEqual(command.position_record_id, OTHER_POSITION)
        self.assertIsNotNone(port.assignment_command)
        assert port.assignment_command is not None
        self.assertEqual(port.assignment_command.position_record_id, POSITION)
        self.assertIsNot(port.assignment_command, command)


if __name__ == "__main__":
    unittest.main()
