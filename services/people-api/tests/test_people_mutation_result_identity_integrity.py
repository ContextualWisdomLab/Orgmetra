"""Result-to-command identity regressions for governed People mutations."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
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
    create_assignment_record,
    create_employment_record,
    create_position_record,
)

TENANT = UUID("0198a412-b100-7000-8000-000000000001")
PERSON = UUID("0198a412-b100-7000-8000-000000000020")
PERSON_NAME = UUID("0198a412-b100-7000-8000-000000000021")
CANDIDATE = UUID("0198a412-b100-7000-8000-000000000022")
SELECTION_DECISION = UUID("0198a412-b100-7000-8000-000000000023")
EMPLOYMENT = UUID("0198a412-b100-7000-8000-000000000030")
EMPLOYMENT_VERSION = UUID("0198a412-b100-7000-8000-000000000031")
POSITION = UUID("0198a412-b100-7000-8000-000000000040")
POSITION_VERSION = UUID("0198a412-b100-7000-8000-000000000041")
ORGANIZATION = UUID("0198a412-b100-7000-8000-000000000050")
JOB = UUID("0198a412-b100-7000-8000-000000000060")
ASSIGNMENT = UUID("0198a412-b100-7000-8000-000000000070")
CONVERSION = UUID("0198a412-b100-7000-8000-000000000071")
AUDIT_EVENT = UUID("0198a412-b100-7000-8000-000000000080")
OUTBOX = UUID("0198a412-b100-7000-8000-000000000081")
OTHER = UUID("0198a412-b100-7000-8000-000000000099")
EFFECTIVE_FROM = date(2026, 9, 5)

PRINCIPAL = AuthenticatedPrincipal(
    tenant_record_id=TENANT,
    actor_reference="keyverse_subject:result-integrity-operator",
    granted_scope_codes=frozenset(
        {
            "orgmetra.people.write",
            "orgmetra.job_architecture.write",
            "orgmetra.people.materialize_worker",
        }
    ),
)


def _employment_command() -> EmploymentMutationCommand:
    """Build one governed Employment create command."""
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
        confirmation_reference="human_confirmation:result-integrity",
        evidence_version_code="result-integrity-v1",
        idempotency_key="result-integrity-employment-1",
    )


def _position_command() -> PositionMutationCommand:
    """Build one governed Position create command."""
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
        confirmation_reference="human_confirmation:result-integrity",
        evidence_version_code="result-integrity-v1",
        idempotency_key="result-integrity-position-1",
    )


def _assignment_command() -> AssignmentMutationCommand:
    """Build one governed Assignment create command."""
    return AssignmentMutationCommand(
        tenant_record_id=TENANT,
        employment_record_id=EMPLOYMENT,
        person_record_id=PERSON,
        position_record_id=POSITION,
        assignment_record_id=ASSIGNMENT,
        audit_event_record_id=AUDIT_EVENT,
        outbox_delivery_record_id=OUTBOX,
        allocation_ratio=Decimal("1.0000"),
        effective_from=EFFECTIVE_FROM,
        confirmation_reference="human_confirmation:result-integrity",
        evidence_version_code="result-integrity-v1",
        idempotency_key="result-integrity-assignment-1",
    )


def _hire_command() -> HireAcceptanceCommand:
    """Build one governed confirmed-hire command."""
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
        display_name="Result Integrity Worker",
        idempotency_key="result-integrity-hire-1",
    )


def _policy(
    *,
    resource_kind: str,
    purpose_code: str,
    operation_code: str,
    scope_code: str,
    field_name: str,
) -> PurposeBoundAccessPolicy:
    """Build one exact purpose-bound policy for a mutation target."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="result-integrity-v1",
        resource_kind=resource_kind,
        purpose_code=purpose_code,
        operation_code=operation_code,
        required_scope_code=scope_code,
        permitted_fields=frozenset({field_name}),
    )


class _PeopleResultPort:
    """Return supplied structurally valid results without honoring command identity."""

    def __init__(
        self,
        *,
        employment_result: EmploymentMutationResult | None = None,
        position_result: PositionMutationResult | None = None,
        assignment_result: AssignmentMutationResult | None = None,
    ) -> None:
        """Retain the result selected by each focused regression."""
        self.employment_result = employment_result
        self.position_result = position_result
        self.assignment_result = assignment_result

    def create_employment(self, *, command: EmploymentMutationCommand, authorization: object) -> EmploymentMutationResult:
        """Return the configured Employment result."""
        del command, authorization
        assert self.employment_result is not None
        return self.employment_result

    def create_position(self, *, command: PositionMutationCommand, authorization: object) -> PositionMutationResult:
        """Return the configured Position result."""
        del command, authorization
        assert self.position_result is not None
        return self.position_result

    def create_assignment(self, *, command: AssignmentMutationCommand, authorization: object) -> AssignmentMutationResult:
        """Return the configured Assignment result."""
        del command, authorization
        assert self.assignment_result is not None
        return self.assignment_result


class _HireResultPort:
    """Return one structurally valid confirmed-hire result supplied by the regression."""

    def __init__(self, result: HireAcceptanceResult) -> None:
        """Retain the result without deriving it from the command."""
        self.result = result

    def accept_hire(self, *, command: HireAcceptanceCommand, authorization: object) -> HireAcceptanceResult:
        """Return the configured hire result."""
        del command, authorization
        return self.result


class PeopleMutationResultIdentityTests(unittest.TestCase):
    """Require generic People port results to name exactly the commanded records."""

    def test_employment_result_must_match_command_identity(self) -> None:
        """A valid but different Employment identity must fail closed."""
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
                mutation_port=_PeopleResultPort(
                    employment_result=EmploymentMutationResult(employment_record_id=OTHER)
                ),
            )

    def test_position_result_must_match_command_identity(self) -> None:
        """A valid but different Position identity must fail closed."""
        with self.assertRaisesRegex(PeopleMutationIntegrityError, "position result identity"):
            create_position_record(
                principal=PRINCIPAL,
                command=_position_command(),
                purpose_code="job_architecture_admin",
                policy=_policy(
                    resource_kind="position_record",
                    purpose_code="job_architecture_admin",
                    operation_code="create_record",
                    scope_code="orgmetra.job_architecture.write",
                    field_name="position_record",
                ),
                mutation_port=_PeopleResultPort(position_result=PositionMutationResult(position_record_id=OTHER)),
            )

    def test_assignment_result_must_match_command_identity(self) -> None:
        """A valid but different Assignment identity must fail closed."""
        with self.assertRaisesRegex(PeopleMutationIntegrityError, "assignment result identity"):
            create_assignment_record(
                principal=PRINCIPAL,
                command=_assignment_command(),
                purpose_code="workforce_admin",
                policy=_policy(
                    resource_kind="assignment_record",
                    purpose_code="workforce_admin",
                    operation_code="create_record",
                    scope_code="orgmetra.people.write",
                    field_name="assignment_record",
                ),
                mutation_port=_PeopleResultPort(
                    assignment_result=AssignmentMutationResult(assignment_record_id=OTHER)
                ),
            )


class HireResultIdentityTests(unittest.TestCase):
    """Require confirmed-hire results to preserve every commanded authoritative identity."""

    def test_hire_result_must_match_person_employment_and_conversion_identities(self) -> None:
        """Any structurally valid but foreign hire identity must fail closed."""
        mismatched_results = (
            HireAcceptanceResult(
                person_record_id=OTHER,
                employment_record_id=EMPLOYMENT,
                candidate_worker_conversion_record_id=CONVERSION,
            ),
            HireAcceptanceResult(
                person_record_id=PERSON,
                employment_record_id=OTHER,
                candidate_worker_conversion_record_id=CONVERSION,
            ),
            HireAcceptanceResult(
                person_record_id=PERSON,
                employment_record_id=EMPLOYMENT,
                candidate_worker_conversion_record_id=OTHER,
            ),
        )
        for result in mismatched_results:
            with self.subTest(result=result), self.assertRaisesRegex(HireDecisionIntegrityError, "hire result identity"):
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
                    mutation_port=_HireResultPort(result),
                )


if __name__ == "__main__":
    unittest.main()
