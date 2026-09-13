"""Post-construction runtime-integrity regressions for governed People mutations."""

from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDecision, PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.mutations import (
    AssignmentMutationCommand,
    AssignmentMutationResult,
    EmploymentMutationCommand,
    EmploymentMutationResult,
    PositionMutationCommand,
    PositionMutationResult,
    create_employment_record,
    mutation_command_digest,
)

TENANT = UUID("0198a412-a600-7000-8000-000000000001")
PERSON = UUID("0198a412-a600-7000-8000-000000000020")
EMPLOYMENT = UUID("0198a412-a600-7000-8000-000000000030")
EMPLOYMENT_VERSION = UUID("0198a412-a600-7000-8000-000000000031")
AUDIT_EVENT = UUID("0198a412-a600-7000-8000-000000000080")
OUTBOX = UUID("0198a412-a600-7000-8000-000000000081")


class _ExecutableUUID(UUID):
    """Trip if a rewritten UUID is observed before exact runtime revalidation."""

    @property
    def hex(self) -> str:
        """Fail if resource-reference rendering executes before validation."""
        raise AssertionError("rewritten UUID hex behavior must not execute")

    def __str__(self) -> str:
        """Fail if canonical rendering executes before validation."""
        raise AssertionError("rewritten UUID string behavior must not execute")


def _command() -> EmploymentMutationCommand:
    """Build one initially valid exact employment mutation command."""
    return EmploymentMutationCommand(
        tenant_record_id=TENANT,
        person_record_id=PERSON,
        employment_record_id=EMPLOYMENT,
        employment_record_version_id=EMPLOYMENT_VERSION,
        audit_event_record_id=AUDIT_EVENT,
        outbox_delivery_record_id=OUTBOX,
        employment_status_code="active",
        employment_concurrency_code="exclusive",
        effective_from=date(2026, 9, 5),
        confirmation_reference="human_confirmation:post-construction-1",
        evidence_version_code="employment-evidence-v1",
        idempotency_key="post-construction-runtime-1",
    )


def _decision() -> AuthorizationDecision:
    """Build exact authorization evidence for the employment command."""
    fields = frozenset({"employment_record"})
    return AuthorizationDecision(
        allowed=True,
        tenant_record_id=TENANT,
        actor_reference="keyverse_subject:operator-226",
        resource_reference=f"employment_record:{EMPLOYMENT.hex}",
        policy_version_code="people-mutation-v1",
        purpose_code="workforce_admin",
        operation_code="create_record",
        resource_kind="employment_record",
        requested_fields=fields,
        authorized_fields=fields,
        reason_code="access_permitted",
        next_action="continue",
    )


def _principal() -> AuthenticatedPrincipal:
    """Build one exact authenticated principal for service-boundary testing."""
    return AuthenticatedPrincipal(
        tenant_record_id=TENANT,
        actor_reference="keyverse_subject:operator-226",
        granted_scope_codes=frozenset({"orgmetra.people.write"}),
    )


def _policy() -> PurposeBoundAccessPolicy:
    """Build one exact purpose-bound policy for employment creation."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="people-mutation-v1",
        resource_kind="employment_record",
        purpose_code="workforce_admin",
        operation_code="create_record",
        required_scope_code="orgmetra.people.write",
        permitted_fields=frozenset({"employment_record"}),
    )


class _ResultPort:
    """Return one supplied employment result while satisfying the mutation protocol."""

    def __init__(self, result: EmploymentMutationResult) -> None:
        """Retain the exact result supplied by the regression."""
        self.result = result

    def create_employment(
        self,
        *,
        command: EmploymentMutationCommand,
        authorization: AuthorizationDecision,
    ) -> EmploymentMutationResult:
        """Return the supplied employment result without changing it."""
        del command, authorization
        return self.result

    def create_position(
        self,
        *,
        command: PositionMutationCommand,
        authorization: AuthorizationDecision,
    ) -> PositionMutationResult:
        """Reject unrelated position work in this focused regression port."""
        del command, authorization
        raise AssertionError("position mutation is outside this regression")

    def create_assignment(
        self,
        *,
        command: AssignmentMutationCommand,
        authorization: AuthorizationDecision,
    ) -> AssignmentMutationResult:
        """Reject unrelated assignment work in this focused regression port."""
        del command, authorization
        raise AssertionError("assignment mutation is outside this regression")


def test_digest_revalidates_exact_command_after_object_setattr_rewrite() -> None:
    """Canonical digesting must reject rewritten command evidence before callbacks."""
    command = _command()
    object.__setattr__(
        command,
        "person_record_id",
        _ExecutableUUID("0198a412-a600-7000-8000-000000000099"),
    )

    with pytest.raises(ValueError, match="person_record_id must be an operational UUID"):
        mutation_command_digest(command=command, authorization=_decision())


def test_service_revalidates_exact_command_before_authorization_or_port_work() -> None:
    """An exact command rewritten after construction must fail before field rendering."""
    command = _command()
    object.__setattr__(
        command,
        "employment_record_id",
        _ExecutableUUID("0198a412-a600-7000-8000-000000000098"),
    )
    result = EmploymentMutationResult(employment_record_id=EMPLOYMENT)

    with pytest.raises(ValueError, match="employment_record_id must be an operational UUID"):
        create_employment_record(
            principal=_principal(),
            command=command,
            purpose_code="workforce_admin",
            policy=_policy(),
            mutation_port=_ResultPort(result),
        )


def test_service_revalidates_exact_result_after_port_rewrite() -> None:
    """An exact result rewritten by a port must not cross the People service boundary."""
    result = EmploymentMutationResult(employment_record_id=EMPLOYMENT)
    object.__setattr__(
        result,
        "employment_record_id",
        _ExecutableUUID("0198a412-a600-7000-8000-000000000097"),
    )

    with pytest.raises(ValueError, match="employment_record_id must be an operational UUID"):
        create_employment_record(
            principal=_principal(),
            command=_command(),
            purpose_code="workforce_admin",
            policy=_policy(),
            mutation_port=_ResultPort(result),
        )
