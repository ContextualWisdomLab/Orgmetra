"""Runtime-integrity regressions for authoritative People mutations."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDecision, PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.mutations import (
    AssignmentMutationCommand,
    EmploymentMutationCommand,
    EmploymentMutationResult,
    command_route,
    create_employment_record,
    mutation_command_digest,
)

TENANT = UUID("0198a412-8000-7000-8000-000000000001")
PERSON = UUID("0198a412-8000-7000-8000-000000000020")
EMPLOYMENT = UUID("0198a412-8000-7000-8000-000000000030")
EMPLOYMENT_VERSION = UUID("0198a412-8000-7000-8000-000000000031")
AUDIT_EVENT = UUID("0198a412-8000-7000-8000-000000000080")
OUTBOX = UUID("0198a412-8000-7000-8000-000000000081")


class _ForgedUUID(UUID):
    """Attempt to rewrite mutation identity text during canonical digesting."""

    def __str__(self) -> str:
        """Render an identity different from the underlying UUID."""
        return "0198a412-8000-7000-8000-ffffffffffff"


class _ForgedDecimal(Decimal):
    """Attempt to rewrite an assignment ratio during canonical digesting."""

    def __format__(self, spec: str) -> str:
        """Render a ratio different from the underlying Decimal value."""
        del spec
        return "0.9999"


class _UnvalidatedEmploymentCommand(EmploymentMutationCommand):
    """Attempt to bypass base command validation through post-init dispatch."""

    def __post_init__(self) -> None:
        """Intentionally skip the governed base validation."""


class _UnvalidatedEmploymentResult(EmploymentMutationResult):
    """Attempt to bypass persistence-result validation."""

    def __post_init__(self) -> None:
        """Intentionally skip the governed base validation."""


def _employment_values(**overrides: object) -> dict[str, object]:
    """Return one otherwise-valid employment mutation command mapping."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "person_record_id": PERSON,
        "employment_record_id": EMPLOYMENT,
        "employment_record_version_id": EMPLOYMENT_VERSION,
        "audit_event_record_id": AUDIT_EVENT,
        "outbox_delivery_record_id": OUTBOX,
        "employment_status_code": "active",
        "employment_concurrency_code": "exclusive",
        "effective_from": date(2026, 8, 21),
        "confirmation_reference": "human_confirmation:runtime-21",
        "evidence_version_code": "decision_evidence_set:v1",
        "idempotency_key": "mutation-runtime-key-21",
    }
    values.update(overrides)
    return values


def _employment(**overrides: object) -> EmploymentMutationCommand:
    """Build one exact employment mutation command."""
    return EmploymentMutationCommand(**_employment_values(**overrides))  # type: ignore[arg-type]


def _assignment(**overrides: object) -> AssignmentMutationCommand:
    """Build one exact assignment mutation command."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "employment_record_id": EMPLOYMENT,
        "person_record_id": PERSON,
        "position_record_id": UUID("0198a412-8000-7000-8000-000000000040"),
        "assignment_record_id": UUID("0198a412-8000-7000-8000-000000000070"),
        "audit_event_record_id": AUDIT_EVENT,
        "outbox_delivery_record_id": OUTBOX,
        "allocation_ratio": Decimal("1.0000"),
        "effective_from": date(2026, 8, 21),
        "confirmation_reference": "human_confirmation:runtime-21",
        "evidence_version_code": "decision_evidence_set:v1",
        "idempotency_key": "mutation-runtime-key-21",
    }
    values.update(overrides)
    return AssignmentMutationCommand(**values)  # type: ignore[arg-type]


def _decision() -> AuthorizationDecision:
    """Build one minimal exact authorization decision for digest testing."""
    return AuthorizationDecision(
        allowed=True,
        tenant_record_id=TENANT,
        actor_reference="keyverse_subject:operator-21",
        resource_reference=f"employment_record:{EMPLOYMENT.hex}",
        policy_version_code="people-mutation-v1",
        purpose_code="workforce_admin",
        operation_code="create_record",
        resource_kind="employment_record",
        requested_fields=frozenset({"employment_record"}),
        authorized_fields=frozenset({"employment_record"}),
        reason_code="access_permitted",
        next_action="Continue with only the authorized fields.",
    )


def test_mutation_command_rejects_uuid_subclass_before_digest_or_persistence() -> None:
    """Caller-controlled UUID rendering cannot rewrite People mutation identity."""
    forged = _ForgedUUID("0198a412-8000-7000-8000-000000000123")
    with pytest.raises(ValueError, match="person_record_id must be an operational UUID"):
        _employment(person_record_id=forged)


def test_mutation_result_rejects_uuid_subclass_before_service_return() -> None:
    """Persistence cannot return an identity object with forged rendering."""
    forged = _ForgedUUID("0198a412-8000-7000-8000-000000000123")
    with pytest.raises(ValueError, match="employment_record_id must be an operational UUID"):
        EmploymentMutationResult(employment_record_id=forged)


def test_assignment_rejects_decimal_subclass_before_canonical_ratio_digest() -> None:
    """Allocation evidence cannot invoke caller-controlled Decimal formatting."""
    forged = _ForgedDecimal("0.5000")
    with pytest.raises(ValueError, match="allocation_ratio must be a Decimal"):
        _assignment(allocation_ratio=forged)


def test_command_helpers_reject_validation_bypassing_subclasses() -> None:
    """Routing and digest helpers require exact validated mutation commands."""
    forged = _UnvalidatedEmploymentCommand(
        **_employment_values(person_record_id="not-a-uuid")  # type: ignore[arg-type]
    )
    with pytest.raises(TypeError, match="governed People mutation command"):
        command_route(forged)
    with pytest.raises(TypeError, match="governed People mutation command"):
        mutation_command_digest(command=forged, authorization=_decision())


def test_create_employment_rejects_command_subclass_before_authorization_or_port() -> None:
    """A command that skipped post-init validation cannot reach the mutation port."""
    forged = _UnvalidatedEmploymentCommand(
        **_employment_values(person_record_id="not-a-uuid")  # type: ignore[arg-type]
    )
    principal = AuthenticatedPrincipal(
        tenant_record_id=TENANT,
        actor_reference="keyverse_subject:operator-21",
        granted_scope_codes=frozenset({"orgmetra.people.write"}),
    )
    policy = PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="people-mutation-v1",
        resource_kind="employment_record",
        purpose_code="workforce_admin",
        operation_code="create_record",
        required_scope_code="orgmetra.people.write",
        permitted_fields=frozenset({"employment_record"}),
    )

    class _Port:
        def create_employment(self, *, command: EmploymentMutationCommand, authorization: object) -> EmploymentMutationResult:
            del command, authorization
            pytest.fail("validation-bypassing command reached persistence")

        def create_position(self, *, command: object, authorization: object) -> object:
            del command, authorization
            raise AssertionError

        def create_assignment(self, *, command: object, authorization: object) -> object:
            del command, authorization
            raise AssertionError

    with pytest.raises(TypeError, match="command must be an EmploymentMutationCommand"):
        create_employment_record(
            principal=principal,
            command=forged,
            purpose_code="workforce_admin",
            policy=policy,
            mutation_port=_Port(),  # type: ignore[arg-type]
        )


def test_create_employment_rejects_result_subclass_that_skipped_validation() -> None:
    """Malformed result subclasses cannot cross the authoritative mutation boundary."""
    principal = AuthenticatedPrincipal(
        tenant_record_id=TENANT,
        actor_reference="keyverse_subject:operator-21",
        granted_scope_codes=frozenset({"orgmetra.people.write"}),
    )
    policy = PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="people-mutation-v1",
        resource_kind="employment_record",
        purpose_code="workforce_admin",
        operation_code="create_record",
        required_scope_code="orgmetra.people.write",
        permitted_fields=frozenset({"employment_record"}),
    )

    class _Port:
        def create_employment(self, *, command: EmploymentMutationCommand, authorization: object) -> EmploymentMutationResult:
            del command, authorization
            return _UnvalidatedEmploymentResult(employment_record_id="not-a-uuid")  # type: ignore[arg-type]

        def create_position(self, *, command: object, authorization: object) -> object:
            del command, authorization
            raise AssertionError

        def create_assignment(self, *, command: object, authorization: object) -> object:
            del command, authorization
            raise AssertionError

    with pytest.raises(TypeError, match="mutation_port must return EmploymentMutationResult"):
        create_employment_record(
            principal=principal,
            command=_employment(),
            purpose_code="workforce_admin",
            policy=policy,
            mutation_port=_Port(),  # type: ignore[arg-type]
        )
