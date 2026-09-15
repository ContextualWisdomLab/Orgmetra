"""Regression contracts for stable generic People mutation persistence capabilities."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.mutations import (
    AssignmentMutationCommand,
    AssignmentMutationResult,
    EmploymentMutationCommand,
    EmploymentMutationResult,
    PeopleMutationPort,
    PositionMutationCommand,
    PositionMutationResult,
    create_assignment_record,
    create_employment_record,
    create_position_record,
)

TENANT = UUID("0198a412-8000-7000-8000-000000000001")
PERSON = UUID("0198a412-8000-7000-8000-000000000020")
EMPLOYMENT = UUID("0198a412-8000-7000-8000-000000000030")
EMPLOYMENT_VERSION = UUID("0198a412-8000-7000-8000-000000000031")
POSITION = UUID("0198a412-8000-7000-8000-000000000040")
POSITION_VERSION = UUID("0198a412-8000-7000-8000-000000000041")
ORGANIZATION_UNIT = UUID("0198a412-8000-7000-8000-000000000050")
JOB_PROFILE = UUID("0198a412-8000-7000-8000-000000000060")
ASSIGNMENT = UUID("0198a412-8000-7000-8000-000000000070")
AUDIT_EVENT = UUID("0198a412-8000-7000-8000-000000000080")
OUTBOX = UUID("0198a412-8000-7000-8000-000000000081")

PRINCIPAL = AuthenticatedPrincipal(
    tenant_record_id=TENANT,
    actor_reference="keyverse_subject:generic-capability-binding-test",
    granted_scope_codes=frozenset({"orgmetra.people.write"}),
)


def _employment_command() -> EmploymentMutationCommand:
    return EmploymentMutationCommand(
        tenant_record_id=TENANT,
        person_record_id=PERSON,
        employment_record_id=EMPLOYMENT,
        employment_record_version_id=EMPLOYMENT_VERSION,
        audit_event_record_id=AUDIT_EVENT,
        outbox_delivery_record_id=OUTBOX,
        employment_status_code="active",
        employment_concurrency_code="exclusive",
        effective_from=date(2026, 9, 15),
        confirmation_reference="human_confirmation:generic-capability-binding",
        evidence_version_code="v1",
        idempotency_key="generic-employment-capability-binding",
    )


def _position_command() -> PositionMutationCommand:
    return PositionMutationCommand(
        tenant_record_id=TENANT,
        position_record_id=POSITION,
        position_record_version_id=POSITION_VERSION,
        organization_unit_id=ORGANIZATION_UNIT,
        job_profile_id=JOB_PROFILE,
        audit_event_record_id=AUDIT_EVENT,
        outbox_delivery_record_id=OUTBOX,
        position_status_code="open",
        effective_from=date(2026, 9, 15),
        confirmation_reference="human_confirmation:generic-capability-binding",
        evidence_version_code="v1",
        idempotency_key="generic-position-capability-binding",
    )


def _assignment_command() -> AssignmentMutationCommand:
    return AssignmentMutationCommand(
        tenant_record_id=TENANT,
        employment_record_id=EMPLOYMENT,
        person_record_id=PERSON,
        position_record_id=POSITION,
        assignment_record_id=ASSIGNMENT,
        audit_event_record_id=AUDIT_EVENT,
        outbox_delivery_record_id=OUTBOX,
        allocation_ratio=Decimal("1.0000"),
        effective_from=date(2026, 9, 15),
        confirmation_reference="human_confirmation:generic-capability-binding",
        evidence_version_code="v1",
        idempotency_key="generic-assignment-capability-binding",
    )


def _policy(resource_kind: str, field_name: str) -> PurposeBoundAccessPolicy:
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="people-mutation-v1",
        resource_kind=resource_kind,
        purpose_code="workforce_admin",
        operation_code="create_record",
        required_scope_code="orgmetra.people.write",
        permitted_fields=frozenset({field_name}),
    )


class _DynamicLookupPort:
    """Expose any dynamic persistence-operation lookup on an in-flight mutation."""

    def __init__(self) -> None:
        self.operation_lookups = {
            "create_employment": 0,
            "create_position": 0,
            "create_assignment": 0,
        }

    def __getattribute__(self, name: str) -> object:
        if name in {"create_employment", "create_position", "create_assignment"}:
            lookups = object.__getattribute__(self, "operation_lookups")
            lookups[name] += 1
        return object.__getattribute__(self, name)

    def create_employment(
        self,
        *,
        command: EmploymentMutationCommand,
        authorization: object,
    ) -> EmploymentMutationResult:
        del authorization
        return EmploymentMutationResult(employment_record_id=command.employment_record_id)

    def create_position(
        self,
        *,
        command: PositionMutationCommand,
        authorization: object,
    ) -> PositionMutationResult:
        del authorization
        return PositionMutationResult(position_record_id=command.position_record_id)

    def create_assignment(
        self,
        *,
        command: AssignmentMutationCommand,
        authorization: object,
    ) -> AssignmentMutationResult:
        del authorization
        return AssignmentMutationResult(assignment_record_id=command.assignment_record_id)


class _DescriptorPort:
    """Look structurally compatible while keeping persistence behavior behind descriptors."""

    def __init__(self) -> None:
        self.descriptor_calls = 0

    def _trip(self) -> object:
        self.descriptor_calls += 1
        raise RuntimeError("descriptor-backed persistence capability executed")

    @property
    def create_employment(self) -> object:
        return self._trip()

    @property
    def create_position(self) -> object:
        return self._trip()

    @property
    def create_assignment(self) -> object:
        return self._trip()


class _ProtocolPlaceholder(PeopleMutationPort):
    """Inherit only Protocol stubs; no concrete persistence operation exists."""


@pytest.mark.parametrize(
    ("operation_name", "invoke"),
    [
        (
            "create_employment",
            lambda port: create_employment_record(
                principal=PRINCIPAL,
                command=_employment_command(),
                purpose_code="workforce_admin",
                policy=_policy("employment_record", "employment_record"),
                mutation_port=port,
            ),
        ),
        (
            "create_position",
            lambda port: create_position_record(
                principal=PRINCIPAL,
                command=_position_command(),
                purpose_code="workforce_admin",
                policy=_policy("position_record", "position_record"),
                mutation_port=port,
            ),
        ),
        (
            "create_assignment",
            lambda port: create_assignment_record(
                principal=PRINCIPAL,
                command=_assignment_command(),
                purpose_code="workforce_admin",
                policy=_policy("assignment_record", "assignment_record"),
                mutation_port=port,
            ),
        ),
    ],
)
def test_success_path_does_not_dynamically_resolve_operation_after_validation(
    operation_name: str,
    invoke: object,
) -> None:
    port = _DynamicLookupPort()

    result = invoke(port)  # type: ignore[operator]

    assert result is not None
    assert port.operation_lookups[operation_name] == 0


@pytest.mark.parametrize(
    "invoke",
    [
        lambda port: create_employment_record(
            principal=PRINCIPAL,
            command=_employment_command(),
            purpose_code="workforce_admin",
            policy=_policy("employment_record", "employment_record"),
            mutation_port=port,
        ),
        lambda port: create_position_record(
            principal=PRINCIPAL,
            command=_position_command(),
            purpose_code="workforce_admin",
            policy=_policy("position_record", "position_record"),
            mutation_port=port,
        ),
        lambda port: create_assignment_record(
            principal=PRINCIPAL,
            command=_assignment_command(),
            purpose_code="workforce_admin",
            policy=_policy("assignment_record", "assignment_record"),
            mutation_port=port,
        ),
    ],
)
def test_descriptor_backed_operation_is_rejected_without_descriptor_execution(invoke: object) -> None:
    port = _DescriptorPort()

    with pytest.raises(TypeError, match="ordinary instance method"):
        invoke(port)  # type: ignore[operator]

    assert port.descriptor_calls == 0


@pytest.mark.parametrize(
    "invoke",
    [
        lambda port: create_employment_record(
            principal=PRINCIPAL,
            command=_employment_command(),
            purpose_code="workforce_admin",
            policy=_policy("employment_record", "employment_record"),
            mutation_port=port,
        ),
        lambda port: create_position_record(
            principal=PRINCIPAL,
            command=_position_command(),
            purpose_code="workforce_admin",
            policy=_policy("position_record", "position_record"),
            mutation_port=port,
        ),
        lambda port: create_assignment_record(
            principal=PRINCIPAL,
            command=_assignment_command(),
            purpose_code="workforce_admin",
            policy=_policy("assignment_record", "assignment_record"),
            mutation_port=port,
        ),
    ],
)
def test_protocol_placeholder_is_not_accepted_as_persistence_capability(invoke: object) -> None:
    with pytest.raises(TypeError, match="ordinary instance method"):
        invoke(_ProtocolPlaceholder())  # type: ignore[operator]
