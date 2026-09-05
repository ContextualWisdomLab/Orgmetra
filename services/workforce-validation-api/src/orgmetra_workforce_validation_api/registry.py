"""Purpose-bound application boundary for the workforce-validation study registry.

This module deliberately stops before PostgreSQL. The protected foundation still
stores validity-study tables in the legacy foundation schema, while
``ARCHITECTURE.md`` assigns persistence ownership to ``workforce_validation``.
The application contract therefore depends on an owner repository port instead
of normalizing direct cross-context SQL into a long-lived service contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Protocol, runtime_checkable
from uuid import UUID
from zoneinfo import ZoneInfo

from orgmetra_keyverse_adapter import (
    PurposeBoundAccessPolicy,
    PurposeBoundAccessRequest,
    require_purpose_bound_access,
)

_MAX_UUID_INT = (1 << 128) - 1
_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$")
_SCOPE_PATTERN = re.compile(r"^orgmetra(?:\.[a-z][a-z0-9_]*){2,}$")
_RESOURCE_KIND = "validity_study_record"
_OPERATION = "read"
_READ_FIELDS = frozenset(
    {
        "criterion_blueprint_id",
        "study_status_code",
        "recorded_from",
        "recorded_to",
    }
)


class ValidityStudyNotFound(LookupError):
    """Indicate that an authorized study identity has no visible registry record."""


class ValidityStudyIntegrityError(RuntimeError):
    """Indicate that persistence returned a record outside the authorized target."""


def _require_operational_uuid(field_name: str, value: object) -> UUID:
    """Return one exact operational UUID and reject protocol sentinels or subtypes."""
    if type(value) is not UUID or value.int in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be an exact operational UUID.")
    return value


def _require_code(field_name: str, value: object) -> str:
    """Return one exact lower-snake-case code used in an auditable policy request."""
    if type(value) is not str or _CODE_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be an exact lower snake_case code.")
    return value


def _require_aware_datetime(field_name: str, value: object) -> datetime:
    """Detach one durable timestamp to exact UTC without arbitrary timezone callbacks."""
    if type(value) is not datetime:
        raise ValueError(f"{field_name} must be an exact datetime.")
    provider = value.tzinfo
    if type(provider) is not timezone and type(provider) is not ZoneInfo:
        raise ValueError(f"{field_name} must use a standard-library timezone provider.")
    return value.astimezone(timezone.utc)


def _validate_scope_set(values: object) -> frozenset[str]:
    """Require immutable explicit Keyverse scopes before constructing an access request."""
    if type(values) is not frozenset or not values:
        raise ValueError("granted_scope_codes must be a non-empty exact frozenset.")
    if any(type(value) is not str or _SCOPE_PATTERN.fullmatch(value) is None for value in values):
        raise ValueError("granted_scope_codes must contain exact Orgmetra scopes.")
    return values


def _validate_requested_fields(values: object) -> frozenset[str]:
    """Require a non-empty immutable subset of the published registry read fields."""
    if type(values) is not frozenset or not values:
        raise ValueError("requested_fields must be a non-empty exact frozenset.")
    if any(type(value) is not str for value in values) or not values.issubset(_READ_FIELDS):
        raise ValueError("requested_fields contains a field outside the validity-study registry contract.")
    return values


def _detach_policy(policy: PurposeBoundAccessPolicy) -> PurposeBoundAccessPolicy:
    """Copy policy evidence into exact inert values before any authorization comparison.

    The protected Keyverse adapter accepts subclass-compatible scalar inputs for
    backward compatibility. This owner boundary is stricter because a caller-
    defined ``str``/``UUID`` subtype could otherwise execute Python behavior when
    the evaluator compares or hashes policy attributes. Locals snapshot each
    immutable value first; the reconstructed exact policy is the only one used by
    authorization.
    """
    tenant_record_id = policy.tenant_record_id
    policy_version_code = policy.policy_version_code
    resource_kind = policy.resource_kind
    purpose_code = policy.purpose_code
    operation_code = policy.operation_code
    required_scope_code = policy.required_scope_code
    permitted_fields = policy.permitted_fields

    _require_operational_uuid("policy tenant_record_id", tenant_record_id)
    for field_name, value in (
        ("policy_version_code", policy_version_code),
        ("resource_kind", resource_kind),
        ("purpose_code", purpose_code),
        ("operation_code", operation_code),
        ("required_scope_code", required_scope_code),
    ):
        if type(value) is not str:
            raise ValueError(f"policy {field_name} must be an exact string.")
    if type(permitted_fields) is not frozenset or any(
        type(value) is not str for value in permitted_fields
    ):
        raise ValueError("policy permitted_fields must contain exact strings in an exact frozenset.")

    return PurposeBoundAccessPolicy(
        tenant_record_id=tenant_record_id,
        policy_version_code=policy_version_code,
        resource_kind=resource_kind,
        purpose_code=purpose_code,
        operation_code=operation_code,
        required_scope_code=required_scope_code,
        permitted_fields=permitted_fields,
    )


@dataclass(frozen=True, slots=True)
class ValidationPrincipal:
    """Authenticated Keyverse identity attributes needed by the validation context.

    The bearer credential itself never enters this value. ``actor_reference`` is
    an opaque namespaced reference and scopes are the already-authenticated token
    scopes supplied by the product authentication boundary.
    """

    tenant_record_id: UUID
    actor_reference: str
    granted_scope_codes: frozenset[str]

    def __post_init__(self) -> None:
        """Reject malformed or mutable identity attributes before authorization."""
        _require_operational_uuid("tenant_record_id", self.tenant_record_id)
        if type(self.actor_reference) is not str or _REFERENCE_PATTERN.fullmatch(self.actor_reference) is None:
            raise ValueError("actor_reference must be an exact namespaced opaque reference.")
        _validate_scope_set(self.granted_scope_codes)


@dataclass(frozen=True, slots=True)
class ValidityStudyRecord:
    """Canonical owner-side projection of one recorded validity-study header.

    This value intentionally contains only fields already represented by the
    protected foundation schema. Predictor, sample, decision-policy and analysis
    protocol versions are not invented here; Issue #234 owns that later scientific
    model increment.
    """

    tenant_record_id: UUID
    validity_study_id: UUID
    criterion_blueprint_id: UUID
    study_status_code: str
    recorded_from: datetime
    recorded_to: datetime | None

    def __post_init__(self) -> None:
        """Detach durable scalar evidence before the application layer exposes it."""
        _require_operational_uuid("tenant_record_id", self.tenant_record_id)
        _require_operational_uuid("validity_study_id", self.validity_study_id)
        _require_operational_uuid("criterion_blueprint_id", self.criterion_blueprint_id)
        _require_code("study_status_code", self.study_status_code)
        recorded_from = _require_aware_datetime("recorded_from", self.recorded_from)
        recorded_to = (
            None
            if self.recorded_to is None
            else _require_aware_datetime("recorded_to", self.recorded_to)
        )
        if recorded_to is not None and recorded_to <= recorded_from:
            raise ValueError("recorded_to must be later than recorded_from.")
        object.__setattr__(self, "recorded_from", recorded_from)
        object.__setattr__(self, "recorded_to", recorded_to)


@dataclass(frozen=True, slots=True)
class ValidityStudyView:
    """Field-minimized authorized view returned to the gateway or role workspace."""

    tenant_record_id: UUID
    validity_study_id: UUID
    fields: tuple[tuple[str, object], ...]


@runtime_checkable
class ValidityStudyReadPort(Protocol):
    """Owner repository contract for one tenant-local validity-study header."""

    def read_validity_study(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
    ) -> ValidityStudyRecord | None:
        """Return one visible owner record or ``None`` without crossing service tables."""
        ...


def read_validity_study(
    *,
    principal: ValidationPrincipal,
    tenant_record_id: UUID,
    validity_study_id: UUID,
    purpose_code: str,
    requested_fields: frozenset[str],
    policy: PurposeBoundAccessPolicy,
    read_port: ValidityStudyReadPort,
) -> ValidityStudyView:
    """Authorize and read one validity-study header through the canonical owner port.

    Authorization is completed before persistence. The persistence result is then
    reconstructed into an exact immutable value and must match the authorized
    tenant/study identity before any field is returned.
    """
    if type(principal) is not ValidationPrincipal:
        raise TypeError("principal must be an exact ValidationPrincipal.")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be an exact PurposeBoundAccessPolicy.")
    if not isinstance(read_port, ValidityStudyReadPort):
        raise TypeError("read_port must implement ValidityStudyReadPort.")

    tenant_id = _require_operational_uuid("tenant_record_id", tenant_record_id)
    study_id = _require_operational_uuid("validity_study_id", validity_study_id)
    purpose = _require_code("purpose_code", purpose_code)
    fields = _validate_requested_fields(requested_fields)
    detached_policy = _detach_policy(policy)

    require_purpose_bound_access(
        request=PurposeBoundAccessRequest(
            tenant_record_id=tenant_id,
            actor_tenant_record_id=principal.tenant_record_id,
            resource_tenant_record_id=tenant_id,
            actor_reference=principal.actor_reference,
            resource_reference=f"{_RESOURCE_KIND}:{study_id}",
            purpose_code=purpose,
            operation_code=_OPERATION,
            resource_kind=_RESOURCE_KIND,
            requested_fields=fields,
            granted_scope_codes=principal.granted_scope_codes,
        ),
        policy=detached_policy,
    )

    persisted = read_port.read_validity_study(
        tenant_record_id=tenant_id,
        validity_study_id=study_id,
    )
    if persisted is None:
        raise ValidityStudyNotFound(str(study_id))
    if type(persisted) is not ValidityStudyRecord:
        raise ValidityStudyIntegrityError("repository returned a non-canonical validity-study record")

    record = ValidityStudyRecord(
        tenant_record_id=persisted.tenant_record_id,
        validity_study_id=persisted.validity_study_id,
        criterion_blueprint_id=persisted.criterion_blueprint_id,
        study_status_code=persisted.study_status_code,
        recorded_from=persisted.recorded_from,
        recorded_to=persisted.recorded_to,
    )
    if record.tenant_record_id != tenant_id or record.validity_study_id != study_id:
        raise ValidityStudyIntegrityError("repository returned a validity-study record for another target")

    values = {
        "criterion_blueprint_id": record.criterion_blueprint_id,
        "study_status_code": record.study_status_code,
        "recorded_from": record.recorded_from,
        "recorded_to": record.recorded_to,
    }
    return ValidityStudyView(
        tenant_record_id=tenant_id,
        validity_study_id=study_id,
        fields=tuple((field_name, values[field_name]) for field_name in sorted(fields)),
    )
