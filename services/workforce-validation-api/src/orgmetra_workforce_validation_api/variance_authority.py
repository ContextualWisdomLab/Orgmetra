"""Corroborate point-weight and variance-design compatibility through an owner port.

This application boundary keeps released sampling, point-weight, and variance
coordinates correlated without importing mutable scientific-package source or
copying row-level weights, replicate vectors, frame variables, or protected
attributes. The persistence child must later back the port with released,
versioned owner evidence.
"""

from __future__ import annotations

from datetime import datetime
from inspect import getattr_static
import re
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

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$")
_RESOURCE_KIND = "weight_variance_authority"
_OPERATION = "read"
_VARIANCE_EVIDENCE_MODES = frozenset(
    {
        "joint_inclusion",
        "reproducible_design_algorithm",
        "replicate_weights",
        "approximation",
    }
)
_VARIANCE_SEMANTICS = frozenset({"exact", "approximate"})
_READ_FIELDS = frozenset(
    {
        "authority_reference",
        "sampling_receipt_reference",
        "sampling_receipt_version",
        "sampling_receipt_digest",
        "analysis_weight_receipt_digest",
        "analytic_case_occurrence_set_digest",
        "weight_eligibility_receipt_digest",
        "weight_correction_sequence",
        "final_weight_artifact_digest",
        "variance_design_receipt_reference",
        "variance_design_receipt_version",
        "variance_design_receipt_digest",
        "variance_method_reference",
        "variance_method_version",
        "variance_evidence_mode",
        "variance_semantics",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "released_at",
    }
)


class WeightVarianceAuthorityNotFound(LookupError):
    """Indicate that no owner evidence corroborates the requested compatibility tuple."""


class WeightVarianceAuthorityIntegrityError(RuntimeError):
    """Indicate that owner evidence cannot support the requested scientific binding."""


def _require_reference(field_name: str, value: object, namespace: str) -> str:
    """Require one exact opaque namespaced evidence reference."""
    if (
        type(value) is not str
        or _REFERENCE_PATTERN.fullmatch(value) is None
        or value.partition(":")[0] != namespace
    ):
        raise ValueError(f"{field_name} must be an exact {namespace}: opaque reference.")
    return value


def _require_digest(field_name: str, value: object) -> str:
    """Require lowercase SHA-256 evidence rather than caller-readable source content."""
    if type(value) is not str or _DIGEST_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex.")
    return value


def _require_positive_integer(field_name: str, value: object) -> int:
    """Require a strict positive integer contract version without accepting booleans."""
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


def _require_variance_evidence_mode(value: object) -> str:
    """Require one controlled #406 variance-evidence strategy identifier."""
    if type(value) is not str or value not in _VARIANCE_EVIDENCE_MODES:
        raise ValueError("variance_evidence_mode must be a supported controlled value.")
    return value


def _require_variance_semantics(value: object) -> str:
    """Require explicit exact-versus-approximate uncertainty semantics."""
    if type(value) is not str or value not in _VARIANCE_SEMANTICS:
        raise ValueError("variance_semantics must be exact or approximate.")
    return value


class WeightVarianceAuthorityRecord(tuple):
    """Immutable owner projection proving point/variance evidence compatibility."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        authority_reference: str,
        sampling_receipt_reference: str,
        sampling_receipt_version: int,
        sampling_receipt_digest: str,
        analysis_weight_receipt_digest: str,
        analytic_case_occurrence_set_digest: str,
        weight_eligibility_receipt_digest: str,
        weight_correction_sequence: int,
        final_weight_artifact_digest: str,
        variance_design_receipt_reference: str,
        variance_design_receipt_version: int,
        variance_design_receipt_digest: str,
        variance_method_reference: str,
        variance_method_version: int,
        variance_evidence_mode: str,
        variance_semantics: str,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
        released_at: datetime,
    ) -> WeightVarianceAuthorityRecord:
        """Validate and detach the minimum immutable compatibility coordinates."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
        authority_ref = _require_reference(
            "authority_reference", authority_reference, "variance_compatibility_authority"
        )
        sampling_ref = _require_reference(
            "sampling_receipt_reference", sampling_receipt_reference, "sampling_design_receipt"
        )
        sampling_version = _require_positive_integer(
            "sampling_receipt_version", sampling_receipt_version
        )
        sampling_digest = _require_digest("sampling_receipt_digest", sampling_receipt_digest)
        point_digest = _require_digest(
            "analysis_weight_receipt_digest", analysis_weight_receipt_digest
        )
        case_digest = _require_digest(
            "analytic_case_occurrence_set_digest", analytic_case_occurrence_set_digest
        )
        eligibility_digest = _require_digest(
            "weight_eligibility_receipt_digest", weight_eligibility_receipt_digest
        )
        correction_sequence = _require_positive_integer(
            "weight_correction_sequence", weight_correction_sequence
        )
        final_digest = _require_digest("final_weight_artifact_digest", final_weight_artifact_digest)
        variance_ref = _require_reference(
            "variance_design_receipt_reference",
            variance_design_receipt_reference,
            "variance_design_receipt",
        )
        variance_version = _require_positive_integer(
            "variance_design_receipt_version", variance_design_receipt_version
        )
        variance_digest = _require_digest(
            "variance_design_receipt_digest", variance_design_receipt_digest
        )
        if variance_digest == point_digest:
            raise ValueError(
                "variance_design_receipt_digest must identify evidence distinct from the analysis weight receipt."
            )
        method_ref = _require_reference(
            "variance_method_reference", variance_method_reference, "variance_method"
        )
        method_version = _require_positive_integer("variance_method_version", variance_method_version)
        evidence_mode = _require_variance_evidence_mode(variance_evidence_mode)
        semantics = _require_variance_semantics(variance_semantics)
        if evidence_mode == "approximation" and semantics != "approximate":
            raise ValueError("approximation evidence must declare approximate variance semantics.")
        owner_ref = _require_reference(
            "owner_contract_reference", owner_contract_reference, "released_owner_contract"
        )
        owner_version = _require_positive_integer("owner_contract_version", owner_contract_version)
        owner_digest = _require_digest("owner_contract_digest", owner_contract_digest)
        release_instant = _require_aware_datetime("released_at", released_at)
        return tuple.__new__(
            cls,
            (
                tenant_identity,
                study_identity,
                authority_ref,
                sampling_ref,
                sampling_version,
                sampling_digest,
                point_digest,
                case_digest,
                eligibility_digest,
                correction_sequence,
                final_digest,
                variance_ref,
                variance_version,
                variance_digest,
                method_ref,
                method_version,
                evidence_mode,
                semantics,
                owner_ref,
                owner_version,
                owner_digest,
                release_instant,
            ),
        )

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh tenant identity for the authority evidence."""
        return _restore_operational_uuid("tenant_record_id", self[0])

    @property
    def validity_study_id(self) -> UUID:
        """Return a fresh validity-study identity for the authority evidence."""
        return _restore_operational_uuid("validity_study_id", self[1])

    @property
    def authority_reference(self) -> str:
        """Return the opaque compatibility-authority reference."""
        return self[2]

    @property
    def sampling_receipt_reference(self) -> str:
        """Return the released #405 sampling receipt reference."""
        return self[3]

    @property
    def sampling_receipt_version(self) -> int:
        """Return the released sampling receipt version."""
        return self[4]

    @property
    def sampling_receipt_digest(self) -> str:
        """Return the released sampling receipt digest."""
        return self[5]

    @property
    def analysis_weight_receipt_digest(self) -> str:
        """Return the exact final point-weight receipt digest."""
        return self[6]

    @property
    def analytic_case_occurrence_set_digest(self) -> str:
        """Return the exact ordered analytic-case occurrence-set digest."""
        return self[7]

    @property
    def weight_eligibility_receipt_digest(self) -> str:
        """Return the exact point-weight eligibility receipt digest."""
        return self[8]

    @property
    def weight_correction_sequence(self) -> int:
        """Return the append-only point-weight correction sequence."""
        return self[9]

    @property
    def final_weight_artifact_digest(self) -> str:
        """Return the final point-weight artifact digest used by variance evidence."""
        return self[10]

    @property
    def variance_design_receipt_reference(self) -> str:
        """Return the released #406 variance-design receipt reference."""
        return self[11]

    @property
    def variance_design_receipt_version(self) -> int:
        """Return the released variance-design receipt version."""
        return self[12]

    @property
    def variance_design_receipt_digest(self) -> str:
        """Return the released variance-design receipt digest."""
        return self[13]

    @property
    def variance_method_reference(self) -> str:
        """Return the controlled variance-method reference."""
        return self[14]

    @property
    def variance_method_version(self) -> int:
        """Return the controlled variance-method version."""
        return self[15]

    @property
    def variance_evidence_mode(self) -> str:
        """Return the controlled #406 evidence strategy."""
        return self[16]

    @property
    def variance_semantics(self) -> str:
        """Return exact-versus-approximate uncertainty semantics."""
        return self[17]

    @property
    def owner_contract_reference(self) -> str:
        """Return the released owner-contract reference."""
        return self[18]

    @property
    def owner_contract_version(self) -> int:
        """Return the positive released owner-contract version."""
        return self[19]

    @property
    def owner_contract_digest(self) -> str:
        """Return the immutable released owner-contract digest."""
        return self[20]

    @property
    def released_at(self) -> datetime:
        """Return the owner-resolved release instant for this authority evidence."""
        return self[21]


class WeightVarianceAuthorityView(tuple):
    """Field-minimized compatibility evidence issued only after authorization."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        fields: tuple[tuple[str, object], ...],
    ) -> WeightVarianceAuthorityView:
        """Reject public construction; the resolver is the only supported issuer."""
        raise TypeError(
            "WeightVarianceAuthorityView is issued only by resolve_weight_variance_authority."
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
class WeightVarianceAuthorityReadPort(Protocol):
    """Owner read contract for released #405/#406/#407 compatibility evidence."""

    def read_weight_variance_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        sampling_receipt_reference: str,
        sampling_receipt_version: int,
        sampling_receipt_digest: str,
        analysis_weight_receipt_digest: str,
        variance_design_receipt_reference: str,
        variance_design_receipt_version: int,
        variance_design_receipt_digest: str,
        owner_contract_reference: str,
        owner_contract_version: int,
    ) -> WeightVarianceAuthorityRecord | None:
        """Return matching released authority evidence or ``None`` through an owner ACL."""
        ...


_PROTOCOL_READ_CAPABILITY = getattr_static(
    WeightVarianceAuthorityReadPort, "read_weight_variance_authority"
)


def resolve_weight_variance_authority(
    *,
    principal: ValidationPrincipal,
    tenant_record_id: UUID,
    validity_study_id: UUID,
    sampling_receipt_reference: str,
    sampling_receipt_version: int,
    sampling_receipt_digest: str,
    analysis_weight_receipt_digest: str,
    analytic_case_occurrence_set_digest: str,
    weight_eligibility_receipt_digest: str,
    weight_correction_sequence: int,
    final_weight_artifact_digest: str,
    variance_design_receipt_reference: str,
    variance_design_receipt_version: int,
    variance_design_receipt_digest: str,
    variance_method_reference: str,
    variance_method_version: int,
    variance_evidence_mode: str,
    variance_semantics: str,
    owner_contract_reference: str,
    owner_contract_version: int,
    used_at: datetime,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    read_port: WeightVarianceAuthorityReadPort,
) -> WeightVarianceAuthorityView:
    """Authorize then corroborate one released point-weight/variance compatibility tuple."""
    if type(principal) is not ValidationPrincipal:
        raise TypeError("principal must be an exact ValidationPrincipal.")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be an exact PurposeBoundAccessPolicy.")
    read_capability = getattr_static(type(read_port), "read_weight_variance_authority", None)
    if type(read_capability) is not FunctionType or read_capability is _PROTOCOL_READ_CAPABILITY:
        raise TypeError(
            "read_port must expose a statically callable read_weight_variance_authority."
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
    sampling_ref = _require_reference(
        "sampling_receipt_reference", sampling_receipt_reference, "sampling_design_receipt"
    )
    sampling_version = _require_positive_integer(
        "sampling_receipt_version", sampling_receipt_version
    )
    sampling_digest = _require_digest("sampling_receipt_digest", sampling_receipt_digest)
    point_digest = _require_digest("analysis_weight_receipt_digest", analysis_weight_receipt_digest)
    case_digest = _require_digest(
        "analytic_case_occurrence_set_digest", analytic_case_occurrence_set_digest
    )
    eligibility_digest = _require_digest(
        "weight_eligibility_receipt_digest", weight_eligibility_receipt_digest
    )
    correction_sequence = _require_positive_integer(
        "weight_correction_sequence", weight_correction_sequence
    )
    final_digest = _require_digest("final_weight_artifact_digest", final_weight_artifact_digest)
    variance_ref = _require_reference(
        "variance_design_receipt_reference",
        variance_design_receipt_reference,
        "variance_design_receipt",
    )
    variance_version = _require_positive_integer(
        "variance_design_receipt_version", variance_design_receipt_version
    )
    variance_digest = _require_digest(
        "variance_design_receipt_digest", variance_design_receipt_digest
    )
    if variance_digest == point_digest:
        raise ValueError(
            "variance_design_receipt_digest must identify evidence distinct from the analysis weight receipt."
        )
    method_ref = _require_reference(
        "variance_method_reference", variance_method_reference, "variance_method"
    )
    method_version = _require_positive_integer("variance_method_version", variance_method_version)
    evidence_mode = _require_variance_evidence_mode(variance_evidence_mode)
    semantics = _require_variance_semantics(variance_semantics)
    if evidence_mode == "approximation" and semantics != "approximate":
        raise ValueError("approximation evidence must declare approximate variance semantics.")
    owner_ref = _require_reference(
        "owner_contract_reference", owner_contract_reference, "released_owner_contract"
    )
    owner_version = _require_positive_integer("owner_contract_version", owner_contract_version)
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
        sampling_receipt_reference=sampling_ref,
        sampling_receipt_version=sampling_version,
        sampling_receipt_digest=sampling_digest,
        analysis_weight_receipt_digest=point_digest,
        variance_design_receipt_reference=variance_ref,
        variance_design_receipt_version=variance_version,
        variance_design_receipt_digest=variance_digest,
        owner_contract_reference=owner_ref,
        owner_contract_version=owner_version,
    )
    if persisted is None:
        raise WeightVarianceAuthorityNotFound(str(study_id))
    if type(persisted) is not WeightVarianceAuthorityRecord:
        raise WeightVarianceAuthorityIntegrityError(
            "owner port returned non-canonical point-weight/variance authority evidence"
        )

    record = WeightVarianceAuthorityRecord(
        tenant_record_id=persisted.tenant_record_id,
        validity_study_id=persisted.validity_study_id,
        authority_reference=persisted.authority_reference,
        sampling_receipt_reference=persisted.sampling_receipt_reference,
        sampling_receipt_version=persisted.sampling_receipt_version,
        sampling_receipt_digest=persisted.sampling_receipt_digest,
        analysis_weight_receipt_digest=persisted.analysis_weight_receipt_digest,
        analytic_case_occurrence_set_digest=persisted.analytic_case_occurrence_set_digest,
        weight_eligibility_receipt_digest=persisted.weight_eligibility_receipt_digest,
        weight_correction_sequence=persisted.weight_correction_sequence,
        final_weight_artifact_digest=persisted.final_weight_artifact_digest,
        variance_design_receipt_reference=persisted.variance_design_receipt_reference,
        variance_design_receipt_version=persisted.variance_design_receipt_version,
        variance_design_receipt_digest=persisted.variance_design_receipt_digest,
        variance_method_reference=persisted.variance_method_reference,
        variance_method_version=persisted.variance_method_version,
        variance_evidence_mode=persisted.variance_evidence_mode,
        variance_semantics=persisted.variance_semantics,
        owner_contract_reference=persisted.owner_contract_reference,
        owner_contract_version=persisted.owner_contract_version,
        owner_contract_digest=persisted.owner_contract_digest,
        released_at=persisted.released_at,
    )
    if (
        _store_operational_uuid("record tenant_record_id", record.tenant_record_id)
        != tenant_identity
        or _store_operational_uuid("record validity_study_id", record.validity_study_id)
        != study_identity
        or record.sampling_receipt_reference != sampling_ref
        or record.sampling_receipt_version != sampling_version
        or record.sampling_receipt_digest != sampling_digest
        or record.analysis_weight_receipt_digest != point_digest
        or record.analytic_case_occurrence_set_digest != case_digest
        or record.weight_eligibility_receipt_digest != eligibility_digest
        or record.weight_correction_sequence != correction_sequence
        or record.final_weight_artifact_digest != final_digest
        or record.variance_design_receipt_reference != variance_ref
        or record.variance_design_receipt_version != variance_version
        or record.variance_design_receipt_digest != variance_digest
        or record.variance_method_reference != method_ref
        or record.variance_method_version != method_version
        or record.variance_evidence_mode != evidence_mode
        or record.variance_semantics != semantics
        or record.owner_contract_reference != owner_ref
        or record.owner_contract_version != owner_version
    ):
        raise WeightVarianceAuthorityIntegrityError(
            "owner evidence does not match the requested point-weight/variance compatibility"
        )
    if use_instant < record.released_at:
        raise WeightVarianceAuthorityIntegrityError(
            "weight/variance authority cannot be used before its owner-resolved release instant"
        )

    values = {
        "authority_reference": record.authority_reference,
        "sampling_receipt_reference": record.sampling_receipt_reference,
        "sampling_receipt_version": record.sampling_receipt_version,
        "sampling_receipt_digest": record.sampling_receipt_digest,
        "analysis_weight_receipt_digest": record.analysis_weight_receipt_digest,
        "analytic_case_occurrence_set_digest": record.analytic_case_occurrence_set_digest,
        "weight_eligibility_receipt_digest": record.weight_eligibility_receipt_digest,
        "weight_correction_sequence": record.weight_correction_sequence,
        "final_weight_artifact_digest": record.final_weight_artifact_digest,
        "variance_design_receipt_reference": record.variance_design_receipt_reference,
        "variance_design_receipt_version": record.variance_design_receipt_version,
        "variance_design_receipt_digest": record.variance_design_receipt_digest,
        "variance_method_reference": record.variance_method_reference,
        "variance_method_version": record.variance_method_version,
        "variance_evidence_mode": record.variance_evidence_mode,
        "variance_semantics": record.variance_semantics,
        "owner_contract_reference": record.owner_contract_reference,
        "owner_contract_version": record.owner_contract_version,
        "owner_contract_digest": record.owner_contract_digest,
        "released_at": record.released_at,
    }
    fields = tuple((field_name, values[field_name]) for field_name in sorted(_READ_FIELDS))
    return tuple.__new__(WeightVarianceAuthorityView, (tenant_identity, study_identity, fields))
