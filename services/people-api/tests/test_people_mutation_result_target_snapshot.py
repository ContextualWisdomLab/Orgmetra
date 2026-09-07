"""Pre-port target binding regressions for People mutation results."""

from __future__ import annotations

from datetime import date
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.hire import (
    HireAcceptanceCommand,
    HireAcceptanceResult,
    HireDecisionIntegrityError,
    accept_confirmed_hire,
)
from orgmetra_people_api.mutations import (
    AssignmentMutationCommand,
    AssignmentMutationResult,
    EmploymentMutationCommand,
    EmploymentMutationResult,
    PeopleMutationIntegrityError,
    PositionMutationCommand,
    PositionMutationResult,
    create_employment_record,
)

TENANT = UUID("0198a412-b200-7000-8000-000000000001")
PERSON = UUID("0198a412-b200-7000-8000-000000000020")
PERSON_NAME = UUID("0198a412-b200-7000-8000-000000000021")
CANDIDATE = UUID("0198a412-b200-7000-8000-000000000022")
SELECTION_DECISION = UUID("0198a412-b200-7000-8000-000000000023")
EMPLOYMENT = UUID("0198a412-b200-7000-8000-000000000030")
EMPLOYMENT_VERSION = UUID("0198a412-b200-7000-8000-000000000031")
CONVERSION = UUID("0198a412-b200-7000-8000-000000000040")
AUDIT_EVENT = UUID("0198a412-b200-7000-8000-000000000050")
OUTBOX = UUID("0198a412-b200-7000-8000-000000000051")
OTHER = UUID("0198a412-b200-7000-8000-000000000099")
EFFECTIVE_FROM = date(2026, 9, 5)

PRINCIPAL = AuthenticatedPrincipal(
    tenant_record_id=TENANT,
    actor_reference="keyverse_subject:target-snapshot-operator",
    granted_scope_codes=frozenset(
        {"orgmetra.people.write", "orgmetra.people.materialize_worker"}
    ),
)


def _employment_command() -> EmploymentMutationCommand:
    """Build one valid Employment command whose target can be rewritten by a port."""
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
        confirmation_reference="human_confirmation:target-snapshot",
        evidence_version_code="target-snapshot-v1",
        idempotency_key="target-snapshot-employment-1",
    )


def _hire_command() -> HireAcceptanceCommand:
    """Build one valid hire command whose target can be rewritten by a port."""
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
        display_name="Target Snapshot Worker",
        idempotency_key="target-snapshot-hire-1",
    )


def _policy(
    *,
    resource_kind: str,
    purpose_code: str,
    operation_code: str,
    scope_code: str,
    field_name: str,
) -> PurposeBoundAccessPolicy:
    """Build one exact policy for the focused mutation boundary."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="target-snapshot-v1",
        resource_kind=resource_kind,
        purpose_code=purpose_code,
        operation_code=operation_code,
        required_scope_code=scope_code,
        permitted_fields=frozenset({field_name}),
    )


class _MutatingPeoplePort:
    """Rewrite the caller command during the port call and report the rewritten identity."""

    def create_employment(
        self,
        *,
        command: EmploymentMutationCommand,
        authorization: object,
    ) -> EmploymentMutationResult:
        """Replace the commanded Employment target before returning a valid result."""
        del authorization
        object.__setattr__(command, "employment_record_id", OTHER)
        return EmploymentMutationResult(employment_record_id=OTHER)

    def create_position(
        self,
        *,
        command: PositionMutationCommand,
        authorization: object,
    ) -> PositionMutationResult:
        """Reject unrelated Position work while satisfying the runtime protocol."""
        del command, authorization
        raise AssertionError("position mutation is outside this regression")

    def create_assignment(
        self,
        *,
        command: AssignmentMutationCommand,
        authorization: object,
    ) -> AssignmentMutationResult:
        """Reject unrelated Assignment work while satisfying the runtime protocol."""
        del command, authorization
        raise AssertionError("assignment mutation is outside this regression")


class _MutatingHirePort:
    """Rewrite all hire targets during the port call and report those rewritten identities."""

    def accept_hire(
        self,
        *,
        command: HireAcceptanceCommand,
        authorization: object,
    ) -> HireAcceptanceResult:
        """Replace authoritative targets after authorization but before service return."""
        del authorization
        object.__setattr__(command, "person_record_id", OTHER)
        object.__setattr__(command, "employment_record_id", OTHER)
        object.__setattr__(command, "candidate_worker_conversion_record_id", OTHER)
        return HireAcceptanceResult(
            person_record_id=OTHER,
            employment_record_id=OTHER,
            candidate_worker_conversion_record_id=OTHER,
        )


class PeopleMutationResultTargetSnapshotTests(unittest.TestCase):
    """Require result coherence against targets captured before executable port work."""

    def test_employment_result_check_uses_pre_port_target(self) -> None:
        """A port must not redefine the expected Employment identity by mutating the command."""
        with self.assertRaisesRegex(PeopleMutationIntegrityError, "employment result identity"):
            create_employment_record(
                principal=PRINCIPAL,
                command=_employment_command(),
                purpose_code="workforce_admin",
                policy=_policy(
                    resource_kind="employment_record",
                    purpose_code="workforce_admin",
                    operation_code="create_record",
                    scope_code="orgmetra.people.write",
                    field_name="employment_record",
                ),
                mutation_port=_MutatingPeoplePort(),
            )

    def test_hire_result_check_uses_pre_port_targets(self) -> None:
        """A port must not redefine Person/Employment/conversion result authority."""
        with self.assertRaisesRegex(HireDecisionIntegrityError, "hire result identity"):
            accept_confirmed_hire(
                principal=PRINCIPAL,
                command=_hire_command(),
                purpose_code="candidate_hire",
                policy=_policy(
                    resource_kind="selection_decision",
                    purpose_code="candidate_hire",
                    operation_code="materialize_worker",
                    scope_code="orgmetra.people.materialize_worker",
                    field_name="candidate_worker_conversion",
                ),
                mutation_port=_MutatingHirePort(),
            )


if __name__ == "__main__":
    unittest.main()
