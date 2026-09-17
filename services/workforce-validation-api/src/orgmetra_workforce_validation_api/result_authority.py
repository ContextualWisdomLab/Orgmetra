"""Corroborate released validation-result evidence through an owner port.

This application boundary binds one immutable validation result to the exact
point-weight/variance compatibility evidence it claims to use. It keeps the
scientific leaf non-authorizing: only ``verification_pending`` or
``not_verifiable`` may cross this owner boundary, and durable PostgreSQL/release
resolution remains a child persistence responsibility after this service lands.
"""

from __future__ import annotations

from datetime import datetime
from inspect import getattr_static
from types import FunctionType
from typing import Protocol, runtime_checkable
from uuid import UUID

from orgmetra_keyverse_adapter import (
    PurposeBoundAccessPolicy,
    PurposeBoundAccessRequest,
    require_purpose_bound_access,
)

from .registry import (
    ValidationPrincipal,
    _detach_policy,
    _require_aware_datetime,
    _require_code,
    _restore_operational_uuid,
    _store_operational_uuid,
)
from .scientific_authority import (
    _require_digest,
    _require_positive_integer,
    _require_reference,
)

_RESOURCE_KIND = "validation_result_authority"
_OPERATION = "read"
_VERIFICATION_STATUSES = frozenset({"verification_pending", "not_verifiable"})
_READ_FIELDS = frozenset(
    {
        "result_reference",
        "result_digest",
        "compatibility_receipt_reference",
        "compatibility_receipt_digest",
        "analysis_weight_receipt_digest",
        "variance_design_receipt_digest",
        "verification_status",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "released_at",
    }
)


class ValidationResultAuthorityNotFound(LookupError):
    """Indicate that no released owner evidence corroborates the result tuple."""


class ValidationResultAuthorityIntegrityError(RuntimeError):
    """Indicate that released owner evidence cannot support the requested result."""


def _require_verification_status(value: object) -> str:
    """Require one explicit non-authorizing result verification state."""
    if type(value) is not str or value not in _VERIFICATION_STATUSES:
        raise ValueError(
            "verification_status must be verification_pending or not_verifiable."
        )
    return value


class ValidationResultAuthorityRecord(tuple):
    """Immutable owner projection binding result, weight, and variance evidence."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        result_reference: str,
        result_digest: str,
        compatibility_receipt_reference: str,
        compatibility_receipt_digest: str,
        analysis_weight_receipt_digest: str,
        variance_design_receipt_digest: str,
        verification_status: str,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
        released_at: datetime,
    ) -> ValidationResultAuthorityRecord:
        """Validate and detach the minimum released result-provenance coordinates."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
        result_ref = _require_reference(
            "result_reference", result_reference, "validation_analysis_result"
        )
        result_evidence_digest = _require_digest("result_digest", result_digest)
        compatibility_ref = _require_reference(
            "compatibility_receipt_reference",
            compatibility_receipt_reference,
            "weight_variance_compatibility_receipt",
        )
        compatibility_digest = _require_digest(
            "compatibility_receipt_digest", compatibility_receipt_digest
        )
        point_digest = _require_digest(
            "analysis_weight_receipt_digest", analysis_weight_receipt_digest
        )
        variance_digest = _require_digest(
            "variance_design_receipt_digest", variance_design_receipt_digest
        )
        if len(
            {
                result_evidence_digest,
                compatibility_digest,
                point_digest,
                variance_digest,
            }
        ) != 4:
            raise ValueError(
                "result, compatibility, analysis-weight, and variance evidence must be distinct."
            )
        status = _require_verification_status(verification_status)
        owner_ref = _require_reference(
            "owner_contract_reference", owner_contract_reference, "released_owner_contract"
        )
        owner_version = _require_positive_integer(
            "owner_contract_version", owner_contract_version
        )
        owner_digest = _require_digest("owner_contract_digest", owner_contract_digest)
        release_instant = _require_aware_datetime("released_at", released_at)
        return tuple.__new__(
            cls,
            (
                tenant_identity,
                study_identity,
                result_ref,
                result_evidence_digest,
                compatibility_ref,
                compatibility_digest,
                point_digest,
                variance_digest,
                status,
                owner_ref,
                owner_version,
                owner_digest,
                release_instant,
            ),
        )

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh tenant identity for this released evidence."""
        return _restore_operational_uuid("tenant_record_id", self[0])

    @property
    def validity_study_id(self) -> UUID:
        """Return a fresh validity-study identity for this released evidence."""
        return _restore_operational_uuid("validity_study_id", self[1])

    @property
    def result_reference(self) -> str:
        """Return the immutable scientific result reference."""
        return self[2]

    @property
    def result_digest(self) -> str:
        """Return the digest of the exact scientific result bytes."""
        return self[3]

    @property
    def compatibility_receipt_reference(self) -> str:
        """Return the exact point-weight/variance compatibility receipt reference."""
        return self[4]

    @property
    def compatibility_receipt_digest(self) -> str:
        """Return the exact compatibility receipt digest."""
        return self[5]

    @property
    def analysis_weight_receipt_digest(self) -> str:
        """Return the final point-estimation weight receipt digest."""
        return self[6]

    @property
    def variance_design_receipt_digest(self) -> str:
        """Return the distinct variance-design receipt digest."""
        return self[7]

    @property
    def verification_status(self) -> str:
        """Return the non-authorizing scientific verification state."""
        return self[8]

    @property
    def owner_contract_reference(self) -> str:
        """Return the released owner-contract reference."""
        return self[9]

    @property
    def owner_contract_version(self) -> int:
        """Return the positive released owner-contract version."""
        return self[10]

    @property
    def owner_contract_digest(self) -> str:
        """Return the immutable released owner-contract digest."""
        return self[11]

    @property
    def released_at(self) -> datetime:
        """Return when this result-authority evidence became released."""
        return self[12]


class ValidationResultAuthorityView(tuple):
    """Field-minimized released result evidence issued only after authorization."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        fields: tuple[tuple[str, object], ...],
    ) -> ValidationResultAuthorityView:
        """Reject direct construction; only the resolver may issue this view."""
        raise TypeError(
            "ValidationResultAuthorityView is issued only by "
            "resolve_validation_result_authority."
        )

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh authorized tenant identity."""
        return _restore_operational_uuid("tenant_record_id", self[0])

    @property
    def validity_study_id(self) -> UUID:
        """Return a fresh authorized validity-study identity."""
        return _restore_operational_uuid("validity_study_id", self[1])

    @property
    def fields(self) -> tuple[tuple[str, object], ...]:
        """Return immutable corroborating fields without row-level scientific data."""
        return self[2]


@runtime_checkable
class ValidationResultAuthorityReadPort(Protocol):
    """Owner read contract for released result-to-weight/variance evidence."""

    def read_validation_result_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        result_reference: str,
        result_digest: str,
        compatibility_receipt_reference: str,
        compatibility_receipt_digest: str,
        analysis_weight_receipt_digest: str,
        variance_design_receipt_digest: str,
        verification_status: str,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
    ) -> ValidationResultAuthorityRecord | None:
        """Return matching released evidence or ``None`` through an owner ACL."""
        ...


_PROTOCOL_READ_CAPABILITY = getattr_static(
    ValidationResultAuthorityReadPort, "read_validation_result_authority"
)


def resolve_validation_result_authority(
    *,
    principal: ValidationPrincipal,
    tenant_record_id: UUID,
    validity_study_id: UUID,
    result_reference: str,
    result_digest: str,
    compatibility_receipt_reference: str,
    compatibility_receipt_digest: str,
    analysis_weight_receipt_digest: str,
    variance_design_receipt_digest: str,
    verification_status: str,
    owner_contract_reference: str,
    owner_contract_version: int,
    owner_contract_digest: str,
    used_at: datetime,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    read_port: ValidationResultAuthorityReadPort,
) -> ValidationResultAuthorityView:
    """Authorize then corroborate one exact released scientific-result binding."""
    if type(principal) is not ValidationPrincipal:
        raise TypeError("principal must be an exact ValidationPrincipal.")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be an exact PurposeBoundAccessPolicy.")
    read_capability = getattr_static(
        type(read_port), "read_validation_result_authority", None
    )
    if (
        type(read_capability) is not FunctionType
        or read_capability is _PROTOCOL_READ_CAPABILITY
    ):
        raise TypeError(
            "read_port must expose a statically callable "
            "read_validation_result_authority."
        )

    detached_principal = ValidationPrincipal(
        tenant_record_id=principal.tenant_record_id,
        actor_reference=principal.actor_reference,
        granted_scope_codes=principal.granted_scope_codes,
    )
    tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
    study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
    tenant_id = _restore_operational_uuid("tenant_record_id", tenant_identity)
    study_id = _restore_operational_uuid("validity_study_id", study_identity)
    result_ref = _require_reference(
        "result_reference", result_reference, "validation_analysis_result"
    )
    result_evidence_digest = _require_digest("result_digest", result_digest)
    compatibility_ref = _require_reference(
        "compatibility_receipt_reference",
        compatibility_receipt_reference,
        "weight_variance_compatibility_receipt",
    )
    compatibility_digest = _require_digest(
        "compatibility_receipt_digest", compatibility_receipt_digest
    )
    point_digest = _require_digest(
        "analysis_weight_receipt_digest", analysis_weight_receipt_digest
    )
    variance_digest = _require_digest(
        "variance_design_receipt_digest", variance_design_receipt_digest
    )
    if len(
        {result_evidence_digest, compatibility_digest, point_digest, variance_digest}
    ) != 4:
        raise ValueError(
            "result, compatibility, analysis-weight, and variance evidence must be distinct."
        )
    status = _require_verification_status(verification_status)
    owner_ref = _require_reference(
        "owner_contract_reference", owner_contract_reference, "released_owner_contract"
    )
    owner_version = _require_positive_integer(
        "owner_contract_version", owner_contract_version
    )
    owner_digest = _require_digest("owner_contract_digest", owner_contract_digest)
    use_instant = _require_aware_datetime("used_at", used_at)
    purpose = _require_code("purpose_code", purpose_code)
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
            requested_fields=_READ_FIELDS,
            granted_scope_codes=detached_principal.granted_scope_codes,
        ),
        policy=detached_policy,
    )

    persisted = read_capability(
        read_port,
        tenant_record_id=_restore_operational_uuid("tenant_record_id", tenant_identity),
        validity_study_id=_restore_operational_uuid("validity_study_id", study_identity),
        result_reference=result_ref,
        result_digest=result_evidence_digest,
        compatibility_receipt_reference=compatibility_ref,
        compatibility_receipt_digest=compatibility_digest,
        analysis_weight_receipt_digest=point_digest,
        variance_design_receipt_digest=variance_digest,
        verification_status=status,
        owner_contract_reference=owner_ref,
        owner_contract_version=owner_version,
        owner_contract_digest=owner_digest,
    )
    if persisted is None:
        raise ValidationResultAuthorityNotFound(str(study_id))
    if type(persisted) is not ValidationResultAuthorityRecord:
        raise ValidationResultAuthorityIntegrityError(
            "owner port returned non-canonical validation-result authority evidence"
        )

    record = ValidationResultAuthorityRecord(
        tenant_record_id=persisted.tenant_record_id,
        validity_study_id=persisted.validity_study_id,
        result_reference=persisted.result_reference,
        result_digest=persisted.result_digest,
        compatibility_receipt_reference=persisted.compatibility_receipt_reference,
        compatibility_receipt_digest=persisted.compatibility_receipt_digest,
        analysis_weight_receipt_digest=persisted.analysis_weight_receipt_digest,
        variance_design_receipt_digest=persisted.variance_design_receipt_digest,
        verification_status=persisted.verification_status,
        owner_contract_reference=persisted.owner_contract_reference,
        owner_contract_version=persisted.owner_contract_version,
        owner_contract_digest=persisted.owner_contract_digest,
        released_at=persisted.released_at,
    )
    requested_identity = (
        tenant_identity,
        study_identity,
        result_ref,
        result_evidence_digest,
        compatibility_ref,
        compatibility_digest,
        point_digest,
        variance_digest,
        status,
        owner_ref,
        owner_version,
        owner_digest,
    )
    record_identity = (
        _store_operational_uuid("record tenant_record_id", record.tenant_record_id),
        _store_operational_uuid("record validity_study_id", record.validity_study_id),
        record.result_reference,
        record.result_digest,
        record.compatibility_receipt_reference,
        record.compatibility_receipt_digest,
        record.analysis_weight_receipt_digest,
        record.variance_design_receipt_digest,
        record.verification_status,
        record.owner_contract_reference,
        record.owner_contract_version,
        record.owner_contract_digest,
    )
    if record_identity != requested_identity:
        raise ValidationResultAuthorityIntegrityError(
            "owner evidence does not match the requested validation-result binding"
        )
    if use_instant < record.released_at:
        raise ValidationResultAuthorityIntegrityError(
            "validation-result authority cannot be used before its release instant"
        )

    values = {
        "result_reference": record.result_reference,
        "result_digest": record.result_digest,
        "compatibility_receipt_reference": record.compatibility_receipt_reference,
        "compatibility_receipt_digest": record.compatibility_receipt_digest,
        "analysis_weight_receipt_digest": record.analysis_weight_receipt_digest,
        "variance_design_receipt_digest": record.variance_design_receipt_digest,
        "verification_status": record.verification_status,
        "owner_contract_reference": record.owner_contract_reference,
        "owner_contract_version": record.owner_contract_version,
        "owner_contract_digest": record.owner_contract_digest,
        "released_at": record.released_at,
    }
    fields = tuple((field_name, values[field_name]) for field_name in sorted(_READ_FIELDS))
    return tuple.__new__(
        ValidationResultAuthorityView,
        (tenant_identity, study_identity, fields),
    )
