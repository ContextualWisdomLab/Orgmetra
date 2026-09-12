"""Governed application boundary for authoritative Employment separation."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
import re
from typing import Protocol, runtime_checkable
from uuid import UUID
from zoneinfo import ZoneInfo

from orgmetra_keyverse_adapter import AuthorizationDecision, PurposeBoundAccessPolicy

from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.authorization import authorize_resource_fields
from orgmetra_people_api.mutations import validate_idempotency_key

_MAX_UUID_INT = (1 << 128) - 1
_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$")
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_REASON_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_EMPLOYMENT_FIELDS = frozenset({"employment_record"})


class EmploymentSeparationIntegrityError(RuntimeError):
    """Indicate that separation evidence cannot be trusted as the requested result."""


def _operational_uuid(field_name: str, value: object) -> UUID:
    """Validate one operational UUID and detach any retained identity alias."""
    if type(value) is not UUID:
        raise ValueError(f"{field_name} must be an operational UUID.")
    identity = value.int
    if type(identity) is not int or not (0 < identity < _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be an operational UUID.")
    return UUID(int=identity)


def _namespaced_reference(field_name: str, value: object) -> str:
    """Validate one bounded opaque namespaced reference."""
    if type(value) is not str or _REFERENCE_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a namespaced opaque reference.")
    return value


def _version_code(value: object) -> str:
    """Validate one whitespace-free evidence version token."""
    if type(value) is not str or _VERSION_PATTERN.fullmatch(value) is None:
        raise ValueError("evidence_version_code must be a whitespace-free version token.")
    return value


def _aware_datetime(field_name: str, value: object) -> datetime:
    """Validate database-owned time without retaining executable timezone aliases."""
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError(f"{field_name} must be an aware datetime.")
    if type(value.tzinfo) not in (timezone, ZoneInfo) or value.utcoffset() is None:
        raise ValueError(f"{field_name} must use a standard aware timezone provider.")
    return value


@dataclass(frozen=True, slots=True)
class EmploymentSeparationCommand:
    """High-impact evidence required to separate one exact current Employment."""

    tenant_record_id: UUID
    person_record_id: UUID
    employment_record_id: UUID
    expected_employment_record_version_id: UUID
    separation_effective_on: date
    separation_reason_code: str
    evidence_reference: str
    evidence_version_code: str
    confirmation_reference: str
    idempotency_key: str
    audit_event_record_id: UUID
    outbox_delivery_record_id: UUID

    def __post_init__(self) -> None:
        """Fail closed and detach operational identities before authorization."""
        for field_name in (
            "tenant_record_id",
            "person_record_id",
            "employment_record_id",
            "expected_employment_record_version_id",
            "audit_event_record_id",
            "outbox_delivery_record_id",
        ):
            object.__setattr__(self, field_name, _operational_uuid(field_name, getattr(self, field_name)))
        if type(self.separation_effective_on) is not date:
            raise ValueError("separation_effective_on must be a business date.")
        if type(self.separation_reason_code) is not str or _REASON_PATTERN.fullmatch(self.separation_reason_code) is None:
            raise ValueError("separation_reason_code must be a lower snake_case code.")
        _namespaced_reference("evidence_reference", self.evidence_reference)
        _version_code(self.evidence_version_code)
        _namespaced_reference("confirmation_reference", self.confirmation_reference)
        validate_idempotency_key(self.idempotency_key)


@dataclass(frozen=True, slots=True)
class EmploymentSeparationResult:
    """Database-owned identity and recorded-time evidence for one separation."""

    employment_record_id: UUID
    separated_employment_record_version_id: UUID
    recorded_at: datetime
    replayed: bool

    def __post_init__(self) -> None:
        """Validate and detach persistence evidence before returning it to callers."""
        object.__setattr__(
            self,
            "employment_record_id",
            _operational_uuid("employment_record_id", self.employment_record_id),
        )
        object.__setattr__(
            self,
            "separated_employment_record_version_id",
            _operational_uuid(
                "separated_employment_record_version_id",
                self.separated_employment_record_version_id,
            ),
        )
        _aware_datetime("recorded_at", self.recorded_at)
        if type(self.replayed) is not bool:
            raise ValueError("replayed must be a bool.")


@runtime_checkable
class EmploymentSeparationPort(Protocol):
    """Persist one authorized Employment separation in an Orgmetra-owned transaction."""

    def separate_employment(
        self,
        *,
        command: EmploymentSeparationCommand,
        authorization: AuthorizationDecision,
    ) -> EmploymentSeparationResult:
        """Return the first committed terminal Employment version or its replay."""


def _require_port(separation_port: object) -> EmploymentSeparationPort:
    """Reject dependencies that do not expose the governed separation operation."""
    if not isinstance(separation_port, EmploymentSeparationPort):
        raise TypeError("separation_port must implement EmploymentSeparationPort")
    return separation_port


def separate_employment_record(
    *,
    principal: AuthenticatedPrincipal,
    command: EmploymentSeparationCommand,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    separation_port: EmploymentSeparationPort,
) -> EmploymentSeparationResult:
    """Authorize one exact Employment separation before crossing persistence."""
    if type(command) is not EmploymentSeparationCommand:
        raise TypeError("command must be an EmploymentSeparationCommand")
    if type(purpose_code) is not str or purpose_code != "workforce_admin":
        raise ValueError("Employment separation requires workforce_admin purpose.")

    detached_command = replace(command)
    expected_employment_record_id = UUID(int=detached_command.employment_record_id.int)
    port = _require_port(separation_port)
    authorization = authorize_resource_fields(
        principal=principal,
        tenant_record_id=detached_command.tenant_record_id,
        resource_tenant_record_id=detached_command.tenant_record_id,
        resource_reference=f"employment_record:{detached_command.employment_record_id.hex}",
        purpose_code=purpose_code,
        operation_code="separate_record",
        resource_kind="employment_record",
        requested_fields=_EMPLOYMENT_FIELDS,
        policy=policy,
    )
    result = port.separate_employment(
        command=replace(detached_command),
        authorization=authorization,
    )
    if type(result) is not EmploymentSeparationResult:
        raise TypeError("separation_port must return EmploymentSeparationResult")
    detached_result = replace(result)
    if detached_result.employment_record_id != expected_employment_record_id:
        raise EmploymentSeparationIntegrityError("separation result identity does not match command")
    return detached_result
