"""Governed application contracts for People employment, position, and assignment writes.

Each command authorizes an exact resource kind before crossing the mutation port.
The port owns one tenant-scoped transaction that persists the authoritative HRIS
fact together with ``record_audit_outbox_event``. Generic Employment and Assignment
writes operate on canonical People truth rather than treating recruiting conversion
provenance as mutation authority, and never write the legacy
``candidate_worker_link`` relation.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from hashlib import sha256
import json
import re
from typing import Protocol, runtime_checkable
from uuid import UUID, uuid5

from orgmetra_keyverse_adapter import AuthorizationDecision, PurposeBoundAccessPolicy

from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.authorization import authorize_resource_fields

_MAX_UUID_INT = (1 << 128) - 1
_IDEMPOTENCY_MIN = 16
_IDEMPOTENCY_MAX = 200
_IDEMPOTENCY_NAMESPACE = UUID("0198a412-9000-7000-8000-0000000000aa")
_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$")
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_EMPLOYMENT_STATUSES = frozenset({"active", "leave", "terminated"})
_CONCURRENCY_CODES = frozenset({"exclusive", "concurrent"})
_POSITION_STATUSES = frozenset({"active", "open", "closed", "frozen", "abolished"})
_EMPLOYMENT_FIELDS = frozenset({"employment_record"})
_POSITION_FIELDS = frozenset({"position_record"})
_ASSIGNMENT_FIELDS = frozenset({"assignment_record"})


class PeopleMutationNotFound(LookupError):
    """Indicate that a required parent HRIS fact is not visible in this tenant."""


class PeopleMutationIntegrityError(RuntimeError):
    """Indicate that the mutation cannot persist without violating employment truth."""


def _validate_operational_uuid(field_name: str, value: object) -> int:
    """Return the inert integer payload of one exact operational UUID."""
    if type(value) is not UUID:
        raise ValueError(f"{field_name} must be an operational UUID.")
    identity = value.int
    if type(identity) is not int or not (0 < identity < _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be an operational UUID.")
    return identity


def _validate_confirmation(value: object) -> None:
    """Require one namespaced human-confirmation reference."""
    if type(value) is not str or _REFERENCE_PATTERN.fullmatch(value) is None:
        raise ValueError("confirmation_reference must be a namespaced opaque reference.")


def _validate_evidence_version(value: object) -> None:
    """Require one whitespace-free evidence version token."""
    if type(value) is not str or _VERSION_PATTERN.fullmatch(value) is None:
        raise ValueError("evidence_version_code must be a whitespace-free version token.")


def validate_idempotency_key(value: object) -> str:
    """Require the same visible-ASCII Idempotency-Key contract as the HTTP boundary."""
    if type(value) is not str or not (_IDEMPOTENCY_MIN <= len(value) <= _IDEMPOTENCY_MAX):
        raise ValueError("idempotency_key must be 16 to 200 visible ASCII characters.")
    if any(ord(character) < 0x21 or ord(character) > 0x7E for character in value):
        raise ValueError("idempotency_key must be 16 to 200 visible ASCII characters.")
    return value


def _canonical_allocation_ratio(value: Decimal) -> str:
    """Return the exact plain-decimal assignment allocation for semantic hashing."""
    if type(value) is not Decimal or not value.is_finite():
        raise ValueError("allocation_ratio must be a finite Decimal.")
    return format(value, "f")


def _canonical_uuid(value: object, *, field_name: str) -> str:
    """Return a canonical UUID string after exact operational validation."""
    _validate_operational_uuid(field_name, value)
    assert isinstance(value, UUID)
    return str(value)


def _validate_semantic_text(field_name: str, value: object, allowed: frozenset[str]) -> str:
    """Return one exact built-in governance token drawn from a bounded vocabulary."""
    if type(value) is not str or value not in allowed:
        raise ValueError(f"{field_name} is invalid.")
    return value


@dataclass(frozen=True, slots=True)
class EmploymentMutationCommand:
    """Describe one governed Employment identity/version creation request."""

    tenant_record_id: UUID
    person_record_id: UUID
    employment_record_id: UUID
    employment_record_version_id: UUID
    audit_event_record_id: UUID
    outbox_delivery_record_id: UUID
    employment_status_code: str
    employment_concurrency_code: str
    effective_from: date
    confirmation_reference: str
    evidence_version_code: str
    idempotency_key: str

    def __post_init__(self) -> None:
        """Reject ambiguous or mutable command identity before authorization or persistence."""
        _validate_operational_uuid("tenant_record_id", self.tenant_record_id)
        _validate_operational_uuid("person_record_id", self.person_record_id)
        _validate_operational_uuid("employment_record_id", self.employment_record_id)
        _validate_operational_uuid("employment_record_version_id", self.employment_record_version_id)
        _validate_operational_uuid("audit_event_record_id", self.audit_event_record_id)
        _validate_operational_uuid("outbox_delivery_record_id", self.outbox_delivery_record_id)
        _validate_semantic_text("employment_status_code", self.employment_status_code, _EMPLOYMENT_STATUSES)
        _validate_semantic_text(
            "employment_concurrency_code", self.employment_concurrency_code, _CONCURRENCY_CODES
        )
        if type(self.effective_from) is not date:
            raise ValueError("effective_from must be a date.")
        _validate_confirmation(self.confirmation_reference)
        _validate_evidence_version(self.evidence_version_code)
        validate_idempotency_key(self.idempotency_key)


@dataclass(frozen=True, slots=True)
class PositionMutationCommand:
    """Describe one governed Position identity/version creation request."""

    tenant_record_id: UUID
    position_record_id: UUID
    position_record_version_id: UUID
    organization_unit_id: UUID
    job_profile_id: UUID
    audit_event_record_id: UUID
    outbox_delivery_record_id: UUID
    position_status_code: str
    effective_from: date
    confirmation_reference: str
    evidence_version_code: str
    idempotency_key: str

    def __post_init__(self) -> None:
        """Reject ambiguous or mutable command identity before authorization or persistence."""
        _validate_operational_uuid("tenant_record_id", self.tenant_record_id)
        _validate_operational_uuid("position_record_id", self.position_record_id)
        _validate_operational_uuid("position_record_version_id", self.position_record_version_id)
        _validate_operational_uuid("organization_unit_id", self.organization_unit_id)
        _validate_operational_uuid("job_profile_id", self.job_profile_id)
        _validate_operational_uuid("audit_event_record_id", self.audit_event_record_id)
        _validate_operational_uuid("outbox_delivery_record_id", self.outbox_delivery_record_id)
        _validate_semantic_text("position_status_code", self.position_status_code, _POSITION_STATUSES)
        if type(self.effective_from) is not date:
            raise ValueError("effective_from must be a date.")
        _validate_confirmation(self.confirmation_reference)
        _validate_evidence_version(self.evidence_version_code)
        validate_idempotency_key(self.idempotency_key)


@dataclass(frozen=True, slots=True)
class AssignmentMutationCommand:
    """Describe one governed Assignment creation request."""

    tenant_record_id: UUID
    employment_record_id: UUID
    person_record_id: UUID
    position_record_id: UUID
    assignment_record_id: UUID
    audit_event_record_id: UUID
    outbox_delivery_record_id: UUID
    allocation_ratio: Decimal
    effective_from: date
    confirmation_reference: str
    evidence_version_code: str
    idempotency_key: str

    def __post_init__(self) -> None:
        """Reject ambiguous or mutable command identity before authorization or persistence."""
        _validate_operational_uuid("tenant_record_id", self.tenant_record_id)
        _validate_operational_uuid("employment_record_id", self.employment_record_id)
        _validate_operational_uuid("person_record_id", self.person_record_id)
        _validate_operational_uuid("position_record_id", self.position_record_id)
        _validate_operational_uuid("assignment_record_id", self.assignment_record_id)
        _validate_operational_uuid("audit_event_record_id", self.audit_event_record_id)
        _validate_operational_uuid("outbox_delivery_record_id", self.outbox_delivery_record_id)
        _canonical_allocation_ratio(self.allocation_ratio)
        if type(self.effective_from) is not date:
            raise ValueError("effective_from must be a date.")
        _validate_confirmation(self.confirmation_reference)
        _validate_evidence_version(self.evidence_version_code)
        validate_idempotency_key(self.idempotency_key)


@dataclass(frozen=True, slots=True)
class EmploymentMutationResult:
    """Return the canonical committed Employment identity and optional replay digest."""

    employment_record_id: UUID
    replay_command_digest: str | None = None

    def __post_init__(self) -> None:
        """Reject executable or sentinel result identities crossing the service boundary."""
        _validate_operational_uuid("employment_record_id", self.employment_record_id)
        if self.replay_command_digest is not None and type(self.replay_command_digest) is not str:
            raise ValueError("replay_command_digest must be a string when present.")


@dataclass(frozen=True, slots=True)
class PositionMutationResult:
    """Return the canonical committed Position identity and optional replay digest."""

    position_record_id: UUID
    replay_command_digest: str | None = None

    def __post_init__(self) -> None:
        """Reject executable or sentinel result identities crossing the service boundary."""
        _validate_operational_uuid("position_record_id", self.position_record_id)
        if self.replay_command_digest is not None and type(self.replay_command_digest) is not str:
            raise ValueError("replay_command_digest must be a string when present.")


@dataclass(frozen=True, slots=True)
class AssignmentMutationResult:
    """Return the canonical committed Assignment identity and optional replay digest."""

    assignment_record_id: UUID
    replay_command_digest: str | None = None

    def __post_init__(self) -> None:
        """Reject executable or sentinel result identities crossing the service boundary."""
        _validate_operational_uuid("assignment_record_id", self.assignment_record_id)
        if self.replay_command_digest is not None and type(self.replay_command_digest) is not str:
            raise ValueError("replay_command_digest must be a string when present.")


@runtime_checkable
class PeopleMutationPort(Protocol):
    """Persist governed People facts after application authorization."""

    def create_employment(
        self,
        *,
        command: EmploymentMutationCommand,
        authorization: AuthorizationDecision,
    ) -> EmploymentMutationResult:
        """Persist one Employment mutation."""
        ...

    def create_position(
        self,
        *,
        command: PositionMutationCommand,
        authorization: AuthorizationDecision,
    ) -> PositionMutationResult:
        """Persist one Position mutation."""
        ...

    def create_assignment(
        self,
        *,
        command: AssignmentMutationCommand,
        authorization: AuthorizationDecision,
    ) -> AssignmentMutationResult:
        """Persist one Assignment mutation."""
        ...


def command_route(
    command: EmploymentMutationCommand | PositionMutationCommand | AssignmentMutationCommand,
) -> str:
    """Return the exact HTTP command route used by the durable replay key."""
    if type(command) is EmploymentMutationCommand:
        return "employment-records"
    if type(command) is PositionMutationCommand:
        return "position-records"
    if type(command) is AssignmentMutationCommand:
        return "assignment-records"
    raise TypeError("unsupported People mutation command")


def mutation_command_digest(
    *,
    command: EmploymentMutationCommand | PositionMutationCommand | AssignmentMutationCommand,
    authorization: AuthorizationDecision,
) -> str:
    """Hash the semantic command and exact authorization context for replay binding."""
    if type(authorization) is not AuthorizationDecision:
        raise TypeError("authorization must be an AuthorizationDecision")
    common = {
        "actor_reference": authorization.actor_reference,
        "confirmation_reference": command.confirmation_reference,
        "evidence_version_code": command.evidence_version_code,
        "policy_version_code": authorization.policy_version_code,
        "purpose_code": authorization.purpose_code,
        "route": command_route(command),
        "tenant_record_id": _canonical_uuid(command.tenant_record_id, field_name="tenant_record_id"),
    }
    if type(command) is EmploymentMutationCommand:
        payload = {
            **common,
            "effective_from": command.effective_from.isoformat(),
            "employment_concurrency_code": command.employment_concurrency_code,
            "employment_status_code": command.employment_status_code,
            "person_record_id": _canonical_uuid(command.person_record_id, field_name="person_record_id"),
        }
    elif type(command) is PositionMutationCommand:
        payload = {
            **common,
            "effective_from": command.effective_from.isoformat(),
            "job_profile_id": _canonical_uuid(command.job_profile_id, field_name="job_profile_id"),
            "organization_unit_id": _canonical_uuid(
                command.organization_unit_id, field_name="organization_unit_id"
            ),
            "position_status_code": command.position_status_code,
        }
    elif type(command) is AssignmentMutationCommand:
        payload = {
            **common,
            "allocation_ratio": _canonical_allocation_ratio(command.allocation_ratio),
            "effective_from": command.effective_from.isoformat(),
            "employment_record_id": _canonical_uuid(
                command.employment_record_id, field_name="employment_record_id"
            ),
            "person_record_id": _canonical_uuid(command.person_record_id, field_name="person_record_id"),
            "position_record_id": _canonical_uuid(
                command.position_record_id, field_name="position_record_id"
            ),
        }
    else:  # pragma: no cover - guarded by command_route and exact command construction
        raise TypeError("unsupported People mutation command")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256(encoded).hexdigest()


def idempotency_record_id(*, tenant_record_id: UUID, command_route_value: str, idempotency_key: str) -> UUID:
    """Derive a stable opaque row identity from the tenant/route/key business key."""
    tenant_integer = _validate_operational_uuid("tenant_record_id", tenant_record_id)
    validate_idempotency_key(idempotency_key)
    if type(command_route_value) is not str or not command_route_value:
        raise ValueError("command_route_value must be a non-empty string.")
    return uuid5(_IDEMPOTENCY_NAMESPACE, f"{tenant_integer}:{command_route_value}:{idempotency_key}")


def _authorize_mutation(
    *,
    principal: AuthenticatedPrincipal,
    tenant_record_id: UUID,
    purpose_code: str,
    resource_kind: str,
    resource_id: UUID,
    requested_fields: frozenset[str],
    required_scope_code: str,
    policy: PurposeBoundAccessPolicy,
) -> AuthorizationDecision:
    """Bind one mutation to its exact tenant, actor, purpose, resource, scope, and fields."""
    return authorize_resource_fields(
        principal=principal,
        tenant_record_id=tenant_record_id,
        purpose_code=purpose_code,
        resource_kind=resource_kind,
        resource_id=resource_id,
        requested_fields=requested_fields,
        required_scope_code=required_scope_code,
        permitted_fields=requested_fields,
        policy=policy,
    )


def create_employment_record(
    *,
    principal: AuthenticatedPrincipal,
    command: EmploymentMutationCommand,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    mutation_port: PeopleMutationPort,
) -> EmploymentMutationResult:
    """Authorize and persist one governed Employment record/version."""
    if type(command) is not EmploymentMutationCommand:
        raise TypeError("command must be an EmploymentMutationCommand")
    command = replace(command)
    authorization = _authorize_mutation(
        principal=principal,
        tenant_record_id=command.tenant_record_id,
        purpose_code=purpose_code,
        resource_kind="employment_record",
        resource_id=command.employment_record_id,
        requested_fields=_EMPLOYMENT_FIELDS,
        required_scope_code="orgmetra.people.write",
        policy=policy,
    )
    result = mutation_port.create_employment(command=command, authorization=authorization)
    if type(result) is not EmploymentMutationResult:
        raise PeopleMutationIntegrityError("employment mutation port returned an invalid result")
    return replace(result)


def create_position_record(
    *,
    principal: AuthenticatedPrincipal,
    command: PositionMutationCommand,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    mutation_port: PeopleMutationPort,
) -> PositionMutationResult:
    """Authorize and persist one governed Position record/version."""
    if type(command) is not PositionMutationCommand:
        raise TypeError("command must be a PositionMutationCommand")
    command = replace(command)
    authorization = _authorize_mutation(
        principal=principal,
        tenant_record_id=command.tenant_record_id,
        purpose_code=purpose_code,
        resource_kind="position_record",
        resource_id=command.position_record_id,
        requested_fields=_POSITION_FIELDS,
        required_scope_code="orgmetra.job_architecture.write",
        policy=policy,
    )
    result = mutation_port.create_position(command=command, authorization=authorization)
    if type(result) is not PositionMutationResult:
        raise PeopleMutationIntegrityError("position mutation port returned an invalid result")
    return replace(result)


def create_assignment_record(
    *,
    principal: AuthenticatedPrincipal,
    command: AssignmentMutationCommand,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    mutation_port: PeopleMutationPort,
) -> AssignmentMutationResult:
    """Authorize and persist one governed Assignment record."""
    if type(command) is not AssignmentMutationCommand:
        raise TypeError("command must be an AssignmentMutationCommand")
    command = replace(command)
    authorization = _authorize_mutation(
        principal=principal,
        tenant_record_id=command.tenant_record_id,
        purpose_code=purpose_code,
        resource_kind="assignment_record",
        resource_id=command.assignment_record_id,
        requested_fields=_ASSIGNMENT_FIELDS,
        required_scope_code="orgmetra.people.write",
        policy=policy,
    )
    result = mutation_port.create_assignment(command=command, authorization=authorization)
    if type(result) is not AssignmentMutationResult:
        raise PeopleMutationIntegrityError("assignment mutation port returned an invalid result")
    return replace(result)
