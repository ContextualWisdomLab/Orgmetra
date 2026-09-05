"""Purpose-bound application boundary for the workforce-validation study registry.

This module deliberately stops before PostgreSQL. The protected foundation still
stores validity-study tables in the legacy foundation schema, while
``ARCHITECTURE.md`` assigns persistence ownership to ``workforce_validation``.
The application contract therefore depends on an owner repository port instead
of normalizing direct cross-context SQL into a long-lived service contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
from inspect import getattr_static
import re
from types import FunctionType
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


def _require_operational_uuid(field_name: str, value: object) -> int:
    """Return one inert UUID integer after exact outer and internal-type validation."""
    if type(value) is not UUID:
        raise ValueError(f"{field_name} must be an exact operational UUID.")
    identity = value.int
    if type(identity) is not int or identity <= 0 or identity >= _MAX_UUID_INT:
        raise ValueError(f"{field_name} must be an exact operational UUID.")
    return identity


def _store_operational_uuid(field_name: str, value: object) -> int:
    """Reduce one validated UUID to immutable integer storage without retaining its object alias."""
    return _require_operational_uuid(field_name, value)


def _restore_operational_uuid(field_name: str, value: object) -> UUID:
    """Reconstruct one fresh UUID from immutable internal integer storage."""
    if type(value) is not int or value <= 0 or value >= _MAX_UUID_INT:
        raise ValueError(f"{field_name} must be an exact operational UUID.")
    return UUID(int=value)


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
    the evaluator compares or hashes policy attributes. Immutable UUID integer
    storage also prevents a retained policy UUID alias from switching the tenant
    after this boundary has accepted it.
    """
    tenant_record_id = policy.tenant_record_id
    policy_version_code = policy.policy_version_code
    resource_kind = policy.resource_kind
    purpose_code = policy.purpose_code
    operation_code = policy.operation_code
    required_scope_code = policy.required_scope_code
    permitted_fields = policy.permitted_fields

    tenant_identity = _store_operational_uuid("policy tenant_record_id", tenant_record_id)
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
        tenant_record_id=_restore_operational_uuid("policy tenant_record_id", tenant_identity),
        policy_version_code=policy_version_code,
        resource_kind=resource_kind,
        purpose_code=purpose_code,
        operation_code=operation_code,
        required_scope_code=required_scope_code,
        permitted_fields=permitted_fields,
    )


class ValidationPrincipal(tuple):
    """Structurally immutable authenticated Keyverse attributes for validation reads.

    The bearer credential itself never enters this value. Tuple-backed storage
    keeps only immutable UUID integer evidence plus immutable actor/scope values,
    so retained UUID references cannot rewrite tenant identity after validation.
    """

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        actor_reference: str,
        granted_scope_codes: frozenset[str],
    ) -> ValidationPrincipal:
        """Validate exact identity evidence before creating the immutable principal."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        if type(actor_reference) is not str or _REFERENCE_PATTERN.fullmatch(actor_reference) is None:
            raise ValueError("actor_reference must be an exact namespaced opaque reference.")
        scope_codes = _validate_scope_set(granted_scope_codes)
        return tuple.__new__(cls, (tenant_identity, actor_reference, scope_codes))

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh authenticated tenant identity."""
        return _restore_operational_uuid("tenant_record_id", self[0])

    @property
    def actor_reference(self) -> str:
        """Return the opaque authenticated actor reference."""
        return self[1]

    @property
    def granted_scope_codes(self) -> frozenset[str]:
        """Return the immutable authenticated scope set."""
        return self[2]


class ValidityStudyRecord(tuple):
    """Structurally immutable owner projection of one recorded validity-study header.

    The tuple-backed representation stores UUIDs as immutable integers, preventing
    a repository adapter that retains accepted UUID objects from rewriting durable
    study identity through ``object.__setattr__`` after construction. Only fields
    already represented by the protected foundation schema are carried here.
    Predictor, sample, decision-policy and analysis-protocol versions remain a
    later scientific-model increment owned by Issue #234.
    """

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        criterion_blueprint_id: UUID,
        study_status_code: str,
        recorded_from: datetime,
        recorded_to: datetime | None,
    ) -> ValidityStudyRecord:
        """Validate and detach durable scalars before creating the immutable tuple."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
        criterion_identity = _store_operational_uuid(
            "criterion_blueprint_id", criterion_blueprint_id
        )
        status_code = _require_code("study_status_code", study_status_code)
        recorded_start = _require_aware_datetime("recorded_from", recorded_from)
        recorded_end = (
            None
            if recorded_to is None
            else _require_aware_datetime("recorded_to", recorded_to)
        )
        if recorded_end is not None and recorded_end <= recorded_start:
            raise ValueError("recorded_to must be later than recorded_from.")
        return tuple.__new__(
            cls,
            (
                tenant_identity,
                study_identity,
                criterion_identity,
                status_code,
                recorded_start,
                recorded_end,
            ),
        )

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh tenant identity for this validity study."""
        return _restore_operational_uuid("tenant_record_id", self[0])

    @property
    def validity_study_id(self) -> UUID:
        """Return a fresh stable validity-study identity."""
        return _restore_operational_uuid("validity_study_id", self[1])

    @property
    def criterion_blueprint_id(self) -> UUID:
        """Return a fresh criterion-blueprint identity linked to the study header."""
        return _restore_operational_uuid("criterion_blueprint_id", self[2])

    @property
    def study_status_code(self) -> str:
        """Return the governed study lifecycle status code."""
        return self[3]

    @property
    def recorded_from(self) -> datetime:
        """Return the exact UTC instant when this version became recorded truth."""
        return self[4]

    @property
    def recorded_to(self) -> datetime | None:
        """Return the exact UTC close instant when present."""
        return self[5]


def _store_view_fields(fields: tuple[tuple[str, object], ...]) -> tuple[tuple[str, object], ...]:
    """Store UUID-valued projection fields without retaining mutable UUID object aliases."""
    return tuple(
        (
            field_name,
            _store_operational_uuid(field_name, value)
            if field_name == "criterion_blueprint_id"
            else value,
        )
        for field_name, value in fields
    )


def _restore_view_fields(fields: tuple[tuple[str, object], ...]) -> tuple[tuple[str, object], ...]:
    """Return a public projection with fresh UUID objects for UUID-valued fields."""
    return tuple(
        (
            field_name,
            _restore_operational_uuid(field_name, value)
            if field_name == "criterion_blueprint_id"
            else value,
        )
        for field_name, value in fields
    )


class ValidityStudyView(tuple):
    """Structurally immutable field-minimized view returned after authorization.

    Tuple-backed storage keeps target UUIDs and UUID-valued projected evidence as
    immutable integers, so downstream gateway, audit, or workspace code cannot
    rewrite authorized identity through retained UUID objects. The public
    constructor is deliberately non-issuing: callers obtain this data-only
    projection from ``read_validity_study`` and must re-authorize consequential
    actions rather than treating the Python runtime type as a durable credential.
    """

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        fields: tuple[tuple[str, object], ...],
    ) -> ValidityStudyView:
        """Reject public construction so only the authorized read path issues views."""
        raise TypeError("ValidityStudyView is issued only by read_validity_study.")

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh tenant identity authorized for this view."""
        return _restore_operational_uuid("tenant_record_id", self[0])

    @property
    def validity_study_id(self) -> UUID:
        """Return a fresh validity-study identity authorized for this view."""
        return _restore_operational_uuid("validity_study_id", self[1])

    @property
    def fields(self) -> tuple[tuple[str, object], ...]:
        """Return ordered field-minimized evidence with fresh UUID-valued projections."""
        return _restore_view_fields(self[2])


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


_PROTOCOL_READ_CAPABILITY = getattr_static(ValidityStudyReadPort, "read_validity_study")


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

    Authorization is completed before persistence. The exact ordinary repository
    method is captured inertly before authorization and that same function is
    invoked after authorization, so dynamic instance lookup cannot switch the
    validated capability. Immutable integer snapshots preserve the authorized
    target across the executable repository call. The persistence result is
    reconstructed into an exact immutable value and must match those snapshots
    before any field is returned.
    """
    if type(principal) is not ValidationPrincipal:
        raise TypeError("principal must be an exact ValidationPrincipal.")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be an exact PurposeBoundAccessPolicy.")
    read_capability = getattr_static(type(read_port), "read_validity_study", None)
    if type(read_capability) is not FunctionType or read_capability is _PROTOCOL_READ_CAPABILITY:
        raise TypeError("read_port must expose a statically callable read_validity_study.")

    detached_principal = ValidationPrincipal(
        tenant_record_id=principal.tenant_record_id,
        actor_reference=principal.actor_reference,
        granted_scope_codes=principal.granted_scope_codes,
    )
    tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
    study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
    tenant_id = _restore_operational_uuid("tenant_record_id", tenant_identity)
    study_id = _restore_operational_uuid("validity_study_id", study_identity)
    purpose = _require_code("purpose_code", purpose_code)
    fields = _validate_requested_fields(requested_fields)
    detached_policy = _detach_policy(policy)

    require_purpose_bound_access(
        request=PurposeBoundAccessRequest(
            tenant_record_id=tenant_id,
            actor_tenant_record_id=detached_principal.tenant_record_id,
            resource_tenant_record_id=tenant_id,
            actor_reference=detached_principal.actor_reference,
            resource_reference=f"{_RESOURCE_KIND}:{study_id}",
            purpose_code=purpose,
            operation_code=_OPERATION,
            resource_kind=_RESOURCE_KIND,
            requested_fields=fields,
            granted_scope_codes=detached_principal.granted_scope_codes,
        ),
        policy=detached_policy,
    )

    persisted = read_capability(
        read_port,
        tenant_record_id=_restore_operational_uuid("tenant_record_id", tenant_identity),
        validity_study_id=_restore_operational_uuid("validity_study_id", study_identity),
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
    if (
        _store_operational_uuid("record tenant_record_id", record.tenant_record_id)
        != tenant_identity
        or _store_operational_uuid("record validity_study_id", record.validity_study_id)
        != study_identity
    ):
        raise ValidityStudyIntegrityError("repository returned a validity-study record for another target")

    values = {
        "criterion_blueprint_id": record.criterion_blueprint_id,
        "study_status_code": record.study_status_code,
        "recorded_from": record.recorded_from,
        "recorded_to": record.recorded_to,
    }
    projected_fields = tuple((field_name, values[field_name]) for field_name in sorted(fields))
    return tuple.__new__(
        ValidityStudyView,
        (
            tenant_identity,
            study_identity,
            _store_view_fields(projected_fields),
        ),
    )
