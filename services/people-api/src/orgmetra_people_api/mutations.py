"""Governed application contracts for People employment, position, and assignment writes.

Each command authorizes an exact resource kind before crossing the mutation port.
The port owns one tenant-scoped transaction that persists the authoritative HRIS
fact together with ``record_audit_outbox_event``. Employment and assignment
writes require a current ``candidate_worker_conversion_record``
(``recorded_to IS NULL``) and never write the legacy
``candidate_worker_link`` relation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import re
from typing import Protocol, runtime_checkable
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDecision, PurposeBoundAccessPolicy

from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.authorization import authorize_resource_fields

_MAX_UUID_INT = (1 << 128) - 1
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


def _validate_operational_uuid(field_name: str, value: object) -> None:
    """Require a real UUID outside Orgmetra's reserved protocol sentinels."""
    if not isinstance(value, UUID) or value.int in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be an operational UUID.")


def _validate_confirmation(value: object) -> None:
    """Require one namespaced human-confirmation reference."""
    if not isinstance(value, str) or _REFERENCE_PATTERN.fullmatch(value) is None:
        raise ValueError("confirmation_reference must be a namespaced opaque reference.")


def _validate_evidence_version(value: object) -> None:
    """Require one whitespace-free evidence version token."""
    if not isinstance(value, str) or _VERSION_PATTERN.fullmatch(value) is None:
        raise ValueError("evidence_version_code must be a whitespace-free version token.")


@dataclass(frozen=True, slots=True)
class EmploymentMutationCommand:
    """Opaque identities and high-impact evidence needed to create one employment."""

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

    def __post_init__(self) -> None:
        """Fail closed before authorization or persistence on malformed input."""
        for field_name in (
            "tenant_record_id",
            "person_record_id",
            "employment_record_id",
            "employment_record_version_id",
            "audit_event_record_id",
            "outbox_delivery_record_id",
        ):
            _validate_operational_uuid(field_name, getattr(self, field_name))
        if type(self.effective_from) is not date:
            raise ValueError("effective_from must be a business date.")
        if self.employment_status_code not in _EMPLOYMENT_STATUSES:
            raise ValueError("employment_status_code must be active, leave, or terminated.")
        if self.employment_concurrency_code not in _CONCURRENCY_CODES:
            raise ValueError("employment_concurrency_code must be exclusive or concurrent.")
        _validate_confirmation(self.confirmation_reference)
        _validate_evidence_version(self.evidence_version_code)


@dataclass(frozen=True, slots=True)
class PositionMutationCommand:
    """Opaque identities and high-impact evidence needed to create one position seat."""

    tenant_record_id: UUID
    organization_unit_id: UUID
    job_profile_id: UUID
    position_record_id: UUID
    position_record_version_id: UUID
    audit_event_record_id: UUID
    outbox_delivery_record_id: UUID
    position_status_code: str
    effective_from: date
    confirmation_reference: str
    evidence_version_code: str

    def __post_init__(self) -> None:
        """Fail closed before authorization or persistence on malformed input."""
        for field_name in (
            "tenant_record_id",
            "organization_unit_id",
            "job_profile_id",
            "position_record_id",
            "position_record_version_id",
            "audit_event_record_id",
            "outbox_delivery_record_id",
        ):
            _validate_operational_uuid(field_name, getattr(self, field_name))
        if type(self.effective_from) is not date:
            raise ValueError("effective_from must be a business date.")
        if self.position_status_code not in _POSITION_STATUSES:
            raise ValueError("position_status_code must be a staffable or closed seat status.")
        _validate_confirmation(self.confirmation_reference)
        _validate_evidence_version(self.evidence_version_code)


@dataclass(frozen=True, slots=True)
class AssignmentMutationCommand:
    """Opaque identities and high-impact evidence needed to create one assignment."""

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

    def __post_init__(self) -> None:
        """Fail closed before authorization or persistence on malformed input."""
        for field_name in (
            "tenant_record_id",
            "employment_record_id",
            "person_record_id",
            "position_record_id",
            "assignment_record_id",
            "audit_event_record_id",
            "outbox_delivery_record_id",
        ):
            _validate_operational_uuid(field_name, getattr(self, field_name))
        if type(self.effective_from) is not date:
            raise ValueError("effective_from must be a business date.")
        if not isinstance(self.allocation_ratio, Decimal):
            raise ValueError("allocation_ratio must be a Decimal.")
        if self.allocation_ratio <= Decimal("0") or self.allocation_ratio > Decimal("1.0000"):
            raise ValueError("allocation_ratio must be greater than 0 and at most 1.0000.")
        _validate_confirmation(self.confirmation_reference)
        _validate_evidence_version(self.evidence_version_code)


@dataclass(frozen=True, slots=True)
class EmploymentMutationResult:
    """Opaque identity returned after one committed employment mutation."""

    employment_record_id: UUID

    def __post_init__(self) -> None:
        """Prevent malformed persistence results from crossing the service boundary."""
        _validate_operational_uuid("employment_record_id", self.employment_record_id)


@dataclass(frozen=True, slots=True)
class PositionMutationResult:
    """Opaque identity returned after one committed position mutation."""

    position_record_id: UUID

    def __post_init__(self) -> None:
        """Prevent malformed persistence results from crossing the service boundary."""
        _validate_operational_uuid("position_record_id", self.position_record_id)


@dataclass(frozen=True, slots=True)
class AssignmentMutationResult:
    """Opaque identity returned after one committed assignment mutation."""

    assignment_record_id: UUID

    def __post_init__(self) -> None:
        """Prevent malformed persistence results from crossing the service boundary."""
        _validate_operational_uuid("assignment_record_id", self.assignment_record_id)


@runtime_checkable
class PeopleMutationPort(Protocol):
    """Persist authorized People mutations atomically inside an Orgmetra-owned boundary."""

    def create_employment(
        self,
        *,
        command: EmploymentMutationCommand,
        authorization: AuthorizationDecision,
    ) -> EmploymentMutationResult:
        """Persist one employment or raise without partial writes."""

    def create_position(
        self,
        *,
        command: PositionMutationCommand,
        authorization: AuthorizationDecision,
    ) -> PositionMutationResult:
        """Persist one position or raise without partial writes."""

    def create_assignment(
        self,
        *,
        command: AssignmentMutationCommand,
        authorization: AuthorizationDecision,
    ) -> AssignmentMutationResult:
        """Persist one assignment or raise without partial writes."""


def _require_port(mutation_port: object) -> PeopleMutationPort:
    """Reject objects that do not implement the People mutation port."""
    if not isinstance(mutation_port, PeopleMutationPort):
        raise TypeError("mutation_port must implement PeopleMutationPort")
    return mutation_port


def create_employment_record(
    *,
    principal: AuthenticatedPrincipal,
    command: EmploymentMutationCommand,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    mutation_port: PeopleMutationPort,
) -> EmploymentMutationResult:
    """Authorize the exact employment target before persisting worker employment truth."""
    if not isinstance(command, EmploymentMutationCommand):
        raise TypeError("command must be an EmploymentMutationCommand")
    port = _require_port(mutation_port)
    authorization = authorize_resource_fields(
        principal=principal,
        tenant_record_id=command.tenant_record_id,
        resource_tenant_record_id=command.tenant_record_id,
        resource_reference=f"employment_record:{command.employment_record_id.hex}",
        purpose_code=purpose_code,
        operation_code="create_record",
        resource_kind="employment_record",
        requested_fields=_EMPLOYMENT_FIELDS,
        policy=policy,
    )
    result = port.create_employment(command=command, authorization=authorization)
    if not isinstance(result, EmploymentMutationResult):
        raise TypeError("mutation_port must return EmploymentMutationResult")
    return result


def create_position_record(
    *,
    principal: AuthenticatedPrincipal,
    command: PositionMutationCommand,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    mutation_port: PeopleMutationPort,
) -> PositionMutationResult:
    """Authorize the exact position target before persisting a staffable seat."""
    if not isinstance(command, PositionMutationCommand):
        raise TypeError("command must be a PositionMutationCommand")
    port = _require_port(mutation_port)
    authorization = authorize_resource_fields(
        principal=principal,
        tenant_record_id=command.tenant_record_id,
        resource_tenant_record_id=command.tenant_record_id,
        resource_reference=f"position_record:{command.position_record_id.hex}",
        purpose_code=purpose_code,
        operation_code="create_record",
        resource_kind="position_record",
        requested_fields=_POSITION_FIELDS,
        policy=policy,
    )
    result = port.create_position(command=command, authorization=authorization)
    if not isinstance(result, PositionMutationResult):
        raise TypeError("mutation_port must return PositionMutationResult")
    return result


def create_assignment_record(
    *,
    principal: AuthenticatedPrincipal,
    command: AssignmentMutationCommand,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    mutation_port: PeopleMutationPort,
) -> AssignmentMutationResult:
    """Authorize the exact assignment target before persisting seat allocation."""
    if not isinstance(command, AssignmentMutationCommand):
        raise TypeError("command must be an AssignmentMutationCommand")
    port = _require_port(mutation_port)
    authorization = authorize_resource_fields(
        principal=principal,
        tenant_record_id=command.tenant_record_id,
        resource_tenant_record_id=command.tenant_record_id,
        resource_reference=f"assignment_record:{command.assignment_record_id.hex}",
        purpose_code=purpose_code,
        operation_code="create_record",
        resource_kind="assignment_record",
        requested_fields=_ASSIGNMENT_FIELDS,
        policy=policy,
    )
    result = port.create_assignment(command=command, authorization=authorization)
    if not isinstance(result, AssignmentMutationResult):
        raise TypeError("mutation_port must return AssignmentMutationResult")
    return result


def parse_allocation_ratio(raw_value: object) -> Decimal:
    """Parse the OpenAPI allocation token into an exact four-decimal ratio."""
    if not isinstance(raw_value, str) or re.fullmatch(r"^(0\.[0-9]{4}|1\.0000)$", raw_value) is None:
        raise ValueError("allocation_ratio must match 0.0001-1.0000 four-decimal form.")
    return Decimal(raw_value)

