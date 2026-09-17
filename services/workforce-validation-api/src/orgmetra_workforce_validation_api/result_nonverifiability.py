"""Represent released non-authorizing outcomes when result evidence cannot be verified.

This application boundary exists for #407 RED 12: absence or failed reproducibility
of required point-weight/compatibility/variance evidence must become explicit
``not_verifiable`` owner evidence rather than an exception that callers can
misinterpret as scientific GREEN. Durable PostgreSQL resolution remains a child
persistence responsibility after the canonical service owner lands.
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

_RESOURCE_KIND = "validation_result_nonverifiability"
_OPERATION = "read"
_VERIFICATION_STATUS = "not_verifiable"
_FAILED_REFERENCE_KIND_BY_EVIDENCE_KIND = {
    "analysis_weight_receipt": "analysis_weight_receipt",
    "weight_variance_compatibility_receipt": "weight_variance_compatibility_receipt",
    "variance_design_receipt": "variance_design_receipt",
}
_FAILURE_MODES = frozenset({"missing", "non_reproducible"})
_READ_FIELDS = frozenset(
    {
        "result_reference",
        "result_digest",
        "verification_status",
        "failed_evidence_kind",
        "failure_mode",
        "failed_evidence_reference",
        "failed_evidence_digest",
        "failed_evidence_released_at",
        "verification_attempt_reference",
        "verification_attempt_digest",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "evaluated_at",
        "released_at",
        "superseded_at",
    }
)


class ValidationResultNonVerifiabilityNotFound(LookupError):
    """Indicate that no released owner outcome corroborates the requested failure."""


class ValidationResultNonVerifiabilityIntegrityError(RuntimeError):
    """Indicate that released owner outcome evidence is inconsistent or malformed."""


def _require_failed_evidence_kind(value: object) -> str:
    """Require one supported scientific evidence family."""
    if type(value) is not str or value not in _FAILED_REFERENCE_KIND_BY_EVIDENCE_KIND:
        raise ValueError(
            "failed_evidence_kind must be analysis_weight_receipt, "
            "weight_variance_compatibility_receipt, or variance_design_receipt."
        )
    return value


def _require_failure_mode(value: object) -> str:
    """Require a missing or non-reproducible evidence outcome."""
    if type(value) is not str or value not in _FAILURE_MODES:
        raise ValueError("failure_mode must be missing or non_reproducible.")
    return value


class ValidationResultNonVerifiabilityRecord(tuple):
    """Immutable owner projection for one released ``not_verifiable`` outcome."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        result_reference: str,
        result_digest: str,
        failed_evidence_kind: str,
        failure_mode: str,
        failed_evidence_reference: str | None,
        failed_evidence_digest: str | None,
        verification_attempt_reference: str,
        verification_attempt_digest: str,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
        owner_contract_released_at: datetime,
        evaluated_at: datetime,
        released_at: datetime,
        superseded_at: datetime | None = None,
        failed_evidence_released_at: datetime | None = None,
    ) -> ValidationResultNonVerifiabilityRecord:
        """Validate a reproducible failure explanation and its authority chronology."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
        result_ref = _require_reference(
            "result_reference", result_reference, "validation_analysis_result"
        )
        result_evidence_digest = _require_digest("result_digest", result_digest)
        evidence_kind = _require_failed_evidence_kind(failed_evidence_kind)
        mode = _require_failure_mode(failure_mode)

        failed_reference: str | None
        failed_digest: str | None
        failed_release: datetime | None
        if mode == "missing":
            if (
                failed_evidence_reference is not None
                or failed_evidence_digest is not None
                or failed_evidence_released_at is not None
            ):
                raise ValueError(
                    "failed evidence reference, digest, and release chronology must be absent "
                    "when evidence is missing."
                )
            failed_reference = None
            failed_digest = None
            failed_release = None
        else:
            if failed_evidence_reference is None or failed_evidence_digest is None:
                raise ValueError(
                    "failed evidence reference and digest are required for non_reproducible evidence."
                )
            if failed_evidence_released_at is None:
                raise ValueError(
                    "failed_evidence_released_at is required for non_reproducible evidence."
                )
            failed_reference = _require_reference(
                "failed_evidence_reference",
                failed_evidence_reference,
                _FAILED_REFERENCE_KIND_BY_EVIDENCE_KIND[evidence_kind],
            )
            failed_digest = _require_digest(
                "failed_evidence_digest", failed_evidence_digest
            )
            failed_release = _require_aware_datetime(
                "failed_evidence_released_at", failed_evidence_released_at
            )

        attempt_ref = _require_reference(
            "verification_attempt_reference",
            verification_attempt_reference,
            "validation_evidence_verification_attempt",
        )
        attempt_digest = _require_digest(
            "verification_attempt_digest", verification_attempt_digest
        )
        owner_ref = _require_reference(
            "owner_contract_reference",
            owner_contract_reference,
            "released_owner_contract",
        )
        owner_version = _require_positive_integer(
            "owner_contract_version", owner_contract_version
        )
        owner_digest = _require_digest("owner_contract_digest", owner_contract_digest)
        owner_released = _require_aware_datetime(
            "owner_contract_released_at", owner_contract_released_at
        )

        digests = [result_evidence_digest, attempt_digest, owner_digest]
        if failed_digest is not None:
            digests.append(failed_digest)
        if len(set(digests)) != len(digests):
            raise ValueError(
                "result, failed-evidence, verification-attempt, and owner-contract "
                "digests must be distinct when present."
            )

        evaluation_instant = _require_aware_datetime("evaluated_at", evaluated_at)
        release_instant = _require_aware_datetime("released_at", released_at)
        if owner_released > evaluation_instant:
            raise ValueError(
                "owner_contract_released_at cannot be later than evaluated_at."
            )
        if failed_release is not None and failed_release > evaluation_instant:
            raise ValueError(
                "failed_evidence_released_at cannot be later than evaluated_at."
            )
        if evaluation_instant > release_instant:
            raise ValueError("evaluated_at cannot be later than released_at.")
        cutover = (
            None
            if superseded_at is None
            else _require_aware_datetime("superseded_at", superseded_at)
        )
        if cutover is not None and cutover <= release_instant:
            raise ValueError(
                "superseded_at must be later than non-verifiability release."
            )

        return tuple.__new__(
            cls,
            (
                tenant_identity,
                study_identity,
                result_ref,
                result_evidence_digest,
                evidence_kind,
                mode,
                failed_reference,
                failed_digest,
                attempt_ref,
                attempt_digest,
                owner_ref,
                owner_version,
                owner_digest,
                owner_released,
                evaluation_instant,
                release_instant,
                cutover,
                failed_release,
            ),
        )

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh tenant identity."""
        return _restore_operational_uuid("tenant_record_id", self[0])

    @property
    def validity_study_id(self) -> UUID:
        """Return a fresh validity-study identity."""
        return _restore_operational_uuid("validity_study_id", self[1])

    @property
    def result_reference(self) -> str:
        """Return the immutable result reference that failed verification."""
        return self[2]

    @property
    def result_digest(self) -> str:
        """Return the exact result digest."""
        return self[3]

    @property
    def verification_status(self) -> str:
        """Return the only state this evidence can authorize."""
        return _VERIFICATION_STATUS

    @property
    def failed_evidence_kind(self) -> str:
        """Return which required evidence family failed verification."""
        return self[4]

    @property
    def failure_mode(self) -> str:
        """Return whether required evidence was missing or non-reproducible."""
        return self[5]

    @property
    def failed_evidence_reference(self) -> str | None:
        """Return the failed evidence reference when a non-reproducible artifact exists."""
        return self[6]

    @property
    def failed_evidence_digest(self) -> str | None:
        """Return the failed evidence digest when a non-reproducible artifact exists."""
        return self[7]

    @property
    def verification_attempt_reference(self) -> str:
        """Return the immutable verification-attempt receipt reference."""
        return self[8]

    @property
    def verification_attempt_digest(self) -> str:
        """Return the immutable verification-attempt receipt digest."""
        return self[9]

    @property
    def owner_contract_reference(self) -> str:
        """Return the released owner-contract reference."""
        return self[10]

    @property
    def owner_contract_version(self) -> int:
        """Return the positive released owner-contract version."""
        return self[11]

    @property
    def owner_contract_digest(self) -> str:
        """Return the immutable released owner-contract digest."""
        return self[12]

    @property
    def owner_contract_released_at(self) -> datetime:
        """Return when the governing owner contract became released authority."""
        return self[13]

    @property
    def evaluated_at(self) -> datetime:
        """Return when the evidence-verification attempt was evaluated."""
        return self[14]

    @property
    def released_at(self) -> datetime:
        """Return when this non-verifiability outcome became released evidence."""
        return self[15]

    @property
    def superseded_at(self) -> datetime | None:
        """Return the exclusive end of this outcome's owner-resolved authority."""
        return self[16]

    @property
    def failed_evidence_released_at(self) -> datetime | None:
        """Return when non-reproducible evidence became available for verification."""
        return self[17]


class ValidationResultNonVerifiabilityView(tuple):
    """Field-minimized non-authorizing outcome issued only after authorization."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        fields: tuple[tuple[str, object], ...],
    ) -> ValidationResultNonVerifiabilityView:
        """Reject public construction; only the resolver may issue this view."""
        raise TypeError(
            "ValidationResultNonVerifiabilityView is issued only by "
            "resolve_validation_result_nonverifiability."
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
        """Return immutable reason/evidence fields without scientific row values."""
        return self[2]


@runtime_checkable
class ValidationResultNonVerifiabilityReadPort(Protocol):
    """Owner read contract for released result non-verifiability evidence."""

    def read_validation_result_nonverifiability(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        result_reference: str,
        result_digest: str,
        failed_evidence_kind: str,
        failure_mode: str,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
    ) -> ValidationResultNonVerifiabilityRecord | None:
        """Return matching released failure evidence or ``None`` through an owner ACL."""
        ...


_PROTOCOL_READ_CAPABILITY = getattr_static(
    ValidationResultNonVerifiabilityReadPort,
    "read_validation_result_nonverifiability",
)


def resolve_validation_result_nonverifiability(
    *,
    principal: ValidationPrincipal,
    tenant_record_id: UUID,
    validity_study_id: UUID,
    result_reference: str,
    result_digest: str,
    failed_evidence_kind: str,
    failure_mode: str,
    owner_contract_reference: str,
    owner_contract_version: int,
    owner_contract_digest: str,
    used_at: datetime,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    read_port: ValidationResultNonVerifiabilityReadPort,
) -> ValidationResultNonVerifiabilityView:
    """Authorize then corroborate one released, explicitly non-authorizing outcome."""
    if type(principal) is not ValidationPrincipal:
        raise TypeError("principal must be an exact ValidationPrincipal.")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be an exact PurposeBoundAccessPolicy.")
    read_capability = getattr_static(
        type(read_port), "read_validation_result_nonverifiability", None
    )
    if (
        type(read_capability) is not FunctionType
        or read_capability is _PROTOCOL_READ_CAPABILITY
    ):
        raise TypeError(
            "read_port must expose a statically callable "
            "read_validation_result_nonverifiability."
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
    evidence_kind = _require_failed_evidence_kind(failed_evidence_kind)
    mode = _require_failure_mode(failure_mode)
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
        failed_evidence_kind=evidence_kind,
        failure_mode=mode,
        owner_contract_reference=owner_ref,
        owner_contract_version=owner_version,
        owner_contract_digest=owner_digest,
    )
    if persisted is None:
        raise ValidationResultNonVerifiabilityNotFound(str(study_id))
    if type(persisted) is not ValidationResultNonVerifiabilityRecord:
        raise ValidationResultNonVerifiabilityIntegrityError(
            "owner port returned non-canonical validation-result non-verifiability evidence"
        )

    record = ValidationResultNonVerifiabilityRecord(
        tenant_record_id=persisted.tenant_record_id,
        validity_study_id=persisted.validity_study_id,
        result_reference=persisted.result_reference,
        result_digest=persisted.result_digest,
        failed_evidence_kind=persisted.failed_evidence_kind,
        failure_mode=persisted.failure_mode,
        failed_evidence_reference=persisted.failed_evidence_reference,
        failed_evidence_digest=persisted.failed_evidence_digest,
        verification_attempt_reference=persisted.verification_attempt_reference,
        verification_attempt_digest=persisted.verification_attempt_digest,
        owner_contract_reference=persisted.owner_contract_reference,
        owner_contract_version=persisted.owner_contract_version,
        owner_contract_digest=persisted.owner_contract_digest,
        owner_contract_released_at=persisted.owner_contract_released_at,
        evaluated_at=persisted.evaluated_at,
        released_at=persisted.released_at,
        superseded_at=persisted.superseded_at,
        failed_evidence_released_at=persisted.failed_evidence_released_at,
    )
    requested_identity = (
        tenant_identity,
        study_identity,
        result_ref,
        result_evidence_digest,
        evidence_kind,
        mode,
        owner_ref,
        owner_version,
        owner_digest,
    )
    record_identity = (
        _store_operational_uuid("record tenant_record_id", record.tenant_record_id),
        _store_operational_uuid("record validity_study_id", record.validity_study_id),
        record.result_reference,
        record.result_digest,
        record.failed_evidence_kind,
        record.failure_mode,
        record.owner_contract_reference,
        record.owner_contract_version,
        record.owner_contract_digest,
    )
    if record_identity != requested_identity:
        raise ValidationResultNonVerifiabilityIntegrityError(
            "owner evidence does not match the requested non-verifiability outcome"
        )
    if use_instant < record.released_at:
        raise ValidationResultNonVerifiabilityIntegrityError(
            "validation-result non-verifiability cannot be used before its release instant"
        )
    if record.superseded_at is not None and use_instant >= record.superseded_at:
        raise ValidationResultNonVerifiabilityIntegrityError(
            "validation-result non-verifiability ended at its owner-resolved supersession instant"
        )

    values = {
        "result_reference": record.result_reference,
        "result_digest": record.result_digest,
        "verification_status": record.verification_status,
        "failed_evidence_kind": record.failed_evidence_kind,
        "failure_mode": record.failure_mode,
        "failed_evidence_reference": record.failed_evidence_reference,
        "failed_evidence_digest": record.failed_evidence_digest,
        "failed_evidence_released_at": record.failed_evidence_released_at,
        "verification_attempt_reference": record.verification_attempt_reference,
        "verification_attempt_digest": record.verification_attempt_digest,
        "owner_contract_reference": record.owner_contract_reference,
        "owner_contract_version": record.owner_contract_version,
        "owner_contract_digest": record.owner_contract_digest,
        "owner_contract_released_at": record.owner_contract_released_at,
        "evaluated_at": record.evaluated_at,
        "released_at": record.released_at,
        "superseded_at": record.superseded_at,
    }
    fields = tuple((field_name, values[field_name]) for field_name in sorted(_READ_FIELDS))
    return tuple.__new__(
        ValidationResultNonVerifiabilityView,
        (tenant_identity, study_identity, fields),
    )
