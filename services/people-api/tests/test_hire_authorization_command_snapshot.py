"""Application command-snapshot regression for confirmed-hire authorization."""

from __future__ import annotations

from datetime import date
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.hire import (
    HireAcceptanceCommand,
    HireAcceptanceResult,
    accept_confirmed_hire,
)

TENANT = UUID("0198a412-c200-7000-8000-000000000001")
CANDIDATE = UUID("0198a412-c200-7000-8000-000000000010")
SELECTION_DECISION = UUID("0198a412-c200-7000-8000-000000000011")
PERSON = UUID("0198a412-c200-7000-8000-000000000020")
PERSON_NAME = UUID("0198a412-c200-7000-8000-000000000021")
EMPLOYMENT = UUID("0198a412-c200-7000-8000-000000000030")
EMPLOYMENT_VERSION = UUID("0198a412-c200-7000-8000-000000000031")
CONVERSION = UUID("0198a412-c200-7000-8000-000000000040")
AUDIT_EVENT = UUID("0198a412-c200-7000-8000-000000000050")
OUTBOX = UUID("0198a412-c200-7000-8000-000000000051")
EFFECTIVE_FROM = date(2026, 9, 5)
ORIGINAL_DISPLAY_NAME = "Authorization Snapshot Worker"
MUTATED_DISPLAY_NAME = "Authorization Callback Rewrite"

PRINCIPAL = AuthenticatedPrincipal(
    tenant_record_id=TENANT,
    actor_reference="keyverse_subject:hire-authorization-snapshot-operator",
    granted_scope_codes=frozenset({"orgmetra.people.materialize_worker"}),
)


class _MutatingResourceKind(str):
    """Rewrite retained caller hire data when policy comparison executes."""

    def __new__(
        cls,
        value: str,
        *,
        command: HireAcceptanceCommand,
    ) -> _MutatingResourceKind:
        """Retain the caller command solely for the adversarial comparison callback."""
        instance = super().__new__(cls, value)
        instance.command = command
        return instance

    def _mutate_command(self) -> None:
        """Rewrite valid PII after application validation but during authorization."""
        object.__setattr__(self.command, "display_name", MUTATED_DISPLAY_NAME)

    def __eq__(self, other: object) -> bool:
        """Mutate before preserving ordinary string equality semantics."""
        self._mutate_command()
        return str.__eq__(self, other)

    def __ne__(self, other: object) -> bool:
        """Mutate before preserving ordinary string inequality semantics."""
        self._mutate_command()
        return str.__ne__(self, other)


class _CapturingHirePort:
    """Capture the hire command that crosses the application port boundary."""

    command: HireAcceptanceCommand | None = None

    def accept_hire(
        self,
        *,
        command: HireAcceptanceCommand,
        authorization: object,
    ) -> HireAcceptanceResult:
        """Capture hire semantics and return the commanded authoritative identities."""
        del authorization
        self.command = command
        return HireAcceptanceResult(
            person_record_id=command.person_record_id,
            employment_record_id=command.employment_record_id,
            candidate_worker_conversion_record_id=command.candidate_worker_conversion_record_id,
        )


def _command() -> HireAcceptanceCommand:
    """Build one valid confirmed-hire command for authorization interleaving."""
    return HireAcceptanceCommand(
        tenant_record_id=TENANT,
        candidate_profile_id=CANDIDATE,
        selection_decision_id=SELECTION_DECISION,
        person_record_id=PERSON,
        person_name_record_id=PERSON_NAME,
        employment_record_id=EMPLOYMENT,
        employment_record_version_id=EMPLOYMENT_VERSION,
        candidate_worker_conversion_record_id=CONVERSION,
        audit_event_record_id=AUDIT_EVENT,
        outbox_delivery_record_id=OUTBOX,
        effective_from=EFFECTIVE_FROM,
        display_name=ORIGINAL_DISPLAY_NAME,
        idempotency_key="hire-authorization-snapshot-1",
    )


def _policy(command: HireAcceptanceCommand) -> PurposeBoundAccessPolicy:
    """Build a valid policy whose resource-kind comparison mutates caller state."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="hire-authorization-snapshot-v1",
        resource_kind=_MutatingResourceKind("selection_decision", command=command),
        purpose_code="candidate_hire",
        operation_code="materialize_worker",
        required_scope_code="orgmetra.people.materialize_worker",
        permitted_fields=frozenset({"candidate_worker_conversion"}),
    )


class HireAuthorizationCommandSnapshotTests(unittest.TestCase):
    """Require authorization callbacks to have no authority over the port hire command."""

    def test_hire_port_receives_pre_authorization_semantics(self) -> None:
        """Policy execution may mutate caller PII but not the detached port command."""
        command = _command()
        port = _CapturingHirePort()

        result = accept_confirmed_hire(
            principal=PRINCIPAL,
            command=command,
            purpose_code="candidate_hire",
            policy=_policy(command),
            mutation_port=port,
        )

        self.assertEqual(command.display_name, MUTATED_DISPLAY_NAME)
        self.assertIsNotNone(port.command)
        assert port.command is not None
        self.assertEqual(port.command.display_name, ORIGINAL_DISPLAY_NAME)
        self.assertIsNot(port.command, command)
        self.assertEqual(result.person_record_id, PERSON)
        self.assertEqual(result.employment_record_id, EMPLOYMENT)
        self.assertEqual(result.candidate_worker_conversion_record_id, CONVERSION)


if __name__ == "__main__":
    unittest.main()
