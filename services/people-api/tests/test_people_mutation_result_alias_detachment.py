"""Retained result-alias regressions for authoritative People mutation boundaries."""

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
    accept_confirmed_hire,
)
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

TENANT = UUID("0198a412-b300-7000-8000-000000000001")
PERSON = UUID("0198a412-b300-7000-8000-000000000020")
PERSON_NAME = UUID("0198a412-b300-7000-8000-000000000021")
CANDIDATE = UUID("0198a412-b300-7000-8000-000000000022")
SELECTION_DECISION = UUID("0198a412-b300-7000-8000-000000000023")
EMPLOYMENT = UUID("0198a412-b300-7000-8000-000000000030")
EMPLOYMENT_VERSION = UUID("0198a412-b300-7000-8000-000000000031")
POSITION = UUID("0198a412-b300-7000-8000-000000000040")
POSITION_VERSION = UUID("0198a412-b300-7000-8000-000000000041")
ORGANIZATION = UUID("0198a412-b300-7000-8000-000000000050")
JOB = UUID("0198a412-b300-7000-8000-000000000060")
ASSIGNMENT = UUID("0198a412-b300-7000-8000-000000000070")
CONVERSION = UUID("0198a412-b300-7000-8000-000000000071")
AUDIT_EVENT = UUID("0198a412-b300-7000-8000-000000000080")
OUTBOX = UUID("0198a412-b300-7000-8000-000000000081")
OTHER = UUID("0198a412-b300-7000-8000-000000000099")
EFFECTIVE_FROM = date(2026, 9, 7)

PRINCIPAL = AuthenticatedPrincipal(
    tenant_record_id=TENANT,
    actor_reference="keyverse_subject:result-alias-operator",
    granted_scope_codes=frozenset(
        {
            "orgmetra.people.write",
            "orgmetra.job_architecture.write",
            "orgmetra.people.materialize_worker",
        }
    ),
)


def _policy(
    *,
    resource_kind: str,
    purpose_code: str,
    operation_code: str,
    scope_code: str,
    field_name: str,
) -> PurposeBoundAccessPolicy:
    """Build one exact purpose-bound policy for a focused result boundary."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="result-alias-v1",
        resource_kind=resource_kind,
        purpose_code=purpose_code,
        operation_code=operation_code,
        required_scope_code=scope_code,
        permitted_fields=frozenset({field_name}),
    )


def _employment_command() -> EmploymentMutationCommand:
    """Build one valid Employment create command."""
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
        confirmation_reference="human_confirmation:result-alias",
        evidence_version_code="result-alias-v1",
        idempotency_key="result-alias-employment-1",
    )


def _position_command() -> PositionMutationCommand:
    """Build one valid Position create command."""
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
        confirmation_reference="human_confirmation:result-alias",
        evidence_version_code="result-alias-v1",
        idempotency_key="result-alias-position-1",
    )


def _assignment_command() -> AssignmentMutationCommand:
    """Build one valid Assignment create command."""
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
        confirmation_reference="human_confirmation:result-alias",
        evidence_version_code="result-alias-v1",
        idempotency_key="result-alias-assignment-1",
    )


def _hire_command() -> HireAcceptanceCommand:
    """Build one valid confirmed-hire command."""
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
        display_name="Result Alias Worker",
        idempotency_key="result-alias-hire-1",
    )


class _RetainedPeopleResultPort:
    """Return exact result objects while retaining the same mutable object aliases."""

    def __init__(
        self,
        *,
        employment_result: EmploymentMutationResult | None = None,
        position_result: PositionMutationResult | None = None,
        assignment_result: AssignmentMutationResult | None = None,
    ) -> None:
        """Retain each result so the adapter can mutate it after service return."""
        self.employment_result = employment_result
        self.position_result = position_result
        self.assignment_result = assignment_result

    def create_employment(self, *, command: EmploymentMutationCommand, authorization: object) -> EmploymentMutationResult:
        """Return the retained Employment result."""
        del command, authorization
        assert self.employment_result is not None
        return self.employment_result

    def create_position(self, *, command: PositionMutationCommand, authorization: object) -> PositionMutationResult:
        """Return the retained Position result."""
        del command, authorization
        assert self.position_result is not None
        return self.position_result

    def create_assignment(self, *, command: AssignmentMutationCommand, authorization: object) -> AssignmentMutationResult:
        """Return the retained Assignment result."""
        del command, authorization
        assert self.assignment_result is not None
        return self.assignment_result


class _RetainedHireResultPort:
    """Return one exact hire result while retaining the same mutable object alias."""

    def __init__(self, result: HireAcceptanceResult) -> None:
        """Retain the result so the adapter can mutate it after service return."""
        self.result = result

    def accept_hire(self, *, command: HireAcceptanceCommand, authorization: object) -> HireAcceptanceResult:
        """Return the retained confirmed-hire result."""
        del command, authorization
        return self.result


class PeopleMutationResultAliasDetachmentTests(unittest.TestCase):
    """Require service outputs to stop sharing result objects or UUID payloads with ports."""

    @staticmethod
    def _mutate_retained_result(result: object, field_name: str) -> None:
        """Rewrite both a retained nested UUID and then its containing result field."""
        retained_uuid = getattr(result, field_name)
        object.__setattr__(retained_uuid, "int", OTHER.int)
        object.__setattr__(result, field_name, OTHER)

    def test_employment_result_is_detached_from_port_alias(self) -> None:
        """A port must not rewrite an accepted Employment result after service return."""
        source = EmploymentMutationResult(employment_record_id=EMPLOYMENT)
        port = _RetainedPeopleResultPort(employment_result=source)
        returned = create_employment_record(
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
            mutation_port=port,
        )
        self._mutate_retained_result(source, "employment_record_id")
        self.assertEqual(returned.employment_record_id, EMPLOYMENT)

    def test_position_result_is_detached_from_port_alias(self) -> None:
        """A port must not rewrite an accepted Position result after service return."""
        source = PositionMutationResult(position_record_id=POSITION)
        port = _RetainedPeopleResultPort(position_result=source)
        returned = create_position_record(
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
            mutation_port=port,
        )
        self._mutate_retained_result(source, "position_record_id")
        self.assertEqual(returned.position_record_id, POSITION)

    def test_assignment_result_is_detached_from_port_alias(self) -> None:
        """A port must not rewrite an accepted Assignment result after service return."""
        source = AssignmentMutationResult(assignment_record_id=ASSIGNMENT)
        port = _RetainedPeopleResultPort(assignment_result=source)
        returned = create_assignment_record(
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
            mutation_port=port,
        )
        self._mutate_retained_result(source, "assignment_record_id")
        self.assertEqual(returned.assignment_record_id, ASSIGNMENT)

    def test_hire_result_is_detached_from_port_alias(self) -> None:
        """A port must not rewrite accepted hire identities after service return."""
        source = HireAcceptanceResult(
            person_record_id=PERSON,
            employment_record_id=EMPLOYMENT,
            candidate_worker_conversion_record_id=CONVERSION,
        )
        port = _RetainedHireResultPort(source)
        returned = accept_confirmed_hire(
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
            mutation_port=port,
        )
        self._mutate_retained_result(source, "person_record_id")
        self._mutate_retained_result(source, "employment_record_id")
        self._mutate_retained_result(source, "candidate_worker_conversion_record_id")
        self.assertEqual(returned.person_record_id, PERSON)
        self.assertEqual(returned.employment_record_id, EMPLOYMENT)
        self.assertEqual(returned.candidate_worker_conversion_record_id, CONVERSION)


if __name__ == "__main__":
    unittest.main()
