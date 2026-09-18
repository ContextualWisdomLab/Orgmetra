"""Corroborate released typed calibration-adjustment evidence through an owner port.

This application boundary binds the exact calibration receipt that produced a
point-weight artifact to its target population, analysis window, purpose-bound
auxiliary authority, benchmark authority, and primary or fallback generating
method. It does not copy auxiliary values, benchmark totals, protected
attributes, or row-level weights. Durable PostgreSQL/release resolution remains
a persistence-owner task after this service reaches protected truth.
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

_RESOURCE_KIND = "calibration_adjustment_authority"
_OPERATION = "read"
_TERMINATION_CODES = frozenset({"converged", "fallback_applied"})
_READ_FIELDS = frozenset(
    {
        "calibration_receipt_reference",
        "calibration_receipt_digest",
        "evidence_version",
        "target_population_digest",
        "analysis_window_reference",
        "auxiliary_authority_reference",
        "auxiliary_projection_reference",
        "auxiliary_projection_version",
        "auxiliary_projection_digest",
        "auxiliary_purpose_reference",
        "auxiliary_purpose_digest",
        "auxiliary_owner_contract_reference",
        "auxiliary_owner_contract_version",
        "auxiliary_owner_contract_digest",
        "auxiliary_authorization_receipt_reference",
        "auxiliary_authorization_receipt_digest",
        "auxiliary_scientific_use_receipt_reference",
        "auxiliary_scientific_use_receipt_digest",
        "auxiliary_scientific_use_at",
        "benchmark_receipt_reference",
        "benchmark_receipt_version",
        "benchmark_receipt_digest",
        "benchmark_owner_contract_reference",
        "benchmark_owner_contract_version",
        "benchmark_owner_contract_digest",
        "benchmark_reference_at",
        "algorithm_reference",
        "algorithm_version",
        "constraints_digest",
        "termination_code",
        "input_weight_artifact_digest",
        "output_weight_artifact_digest",
        "constructed_at",
        "fallback_reason_code",
        "fallback_rule_reference",
        "fallback_rule_digest",
        "fallback_algorithm_reference",
        "fallback_algorithm_version",
        "fallback_configuration_digest",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
    }
)


class CalibrationAdjustmentAuthorityNotFound(LookupError):
    """Indicate that no released owner evidence corroborates the calibration receipt."""


class CalibrationAdjustmentAuthorityIntegrityError(RuntimeError):
    """Indicate that owner evidence cannot corroborate the requested calibration."""


def _require_termination_code(value: object) -> str:
    """Require an explicit successful-primary or explicit-fallback outcome."""
    if type(value) is not str or value not in _TERMINATION_CODES:
        raise ValueError("termination_code must be converged or fallback_applied.")
    return value


class CalibrationAdjustmentAuthorityRecord(tuple):
    """Immutable owner projection for one released typed calibration receipt."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        calibration_receipt_reference: str,
        calibration_receipt_digest: str,
        evidence_version: int,
        target_population_digest: str,
        analysis_window_reference: str,
        auxiliary_authority_reference: str,
        auxiliary_projection_reference: str,
        auxiliary_projection_version: int,
        auxiliary_projection_digest: str,
        auxiliary_purpose_reference: str,
        auxiliary_purpose_digest: str,
        auxiliary_owner_contract_reference: str,
        auxiliary_owner_contract_version: int,
        auxiliary_owner_contract_digest: str,
        auxiliary_authorization_receipt_reference: str,
        auxiliary_authorization_receipt_digest: str,
        auxiliary_scientific_use_receipt_reference: str,
        auxiliary_scientific_use_receipt_digest: str,
        auxiliary_scientific_use_at: datetime,
        benchmark_receipt_reference: str,
        benchmark_receipt_version: int,
        benchmark_receipt_digest: str,
        benchmark_owner_contract_reference: str,
        benchmark_owner_contract_version: int,
        benchmark_owner_contract_digest: str,
        benchmark_reference_at: datetime,
        algorithm_reference: str,
        algorithm_version: int,
        constraints_digest: str,
        termination_code: str,
        input_weight_artifact_digest: str,
        output_weight_artifact_digest: str,
        constructed_at: datetime,
        fallback_reason_code: str | None,
        fallback_rule_reference: str | None,
        fallback_rule_digest: str | None,
        fallback_algorithm_reference: str | None,
        fallback_algorithm_version: int | None,
        fallback_configuration_digest: str | None,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
        owner_contract_released_at: datetime,
        released_at: datetime,
    ) -> CalibrationAdjustmentAuthorityRecord:
        """Validate and detach the receipt-level scientific authority."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
        receipt_ref = _require_reference(
            "calibration_receipt_reference",
            calibration_receipt_reference,
            "calibration_adjustment_receipt",
        )
        receipt_digest = _require_digest(
            "calibration_receipt_digest", calibration_receipt_digest
        )
        version = _require_positive_integer("evidence_version", evidence_version)
        if version != 1:
            raise ValueError("evidence_version must remain 1.")
        target_digest = _require_digest(
            "target_population_digest", target_population_digest
        )
        analysis_window_ref = _require_reference(
            "analysis_window_reference",
            analysis_window_reference,
            "analysis_window",
        )
        auxiliary_authority_ref = _require_reference(
            "auxiliary_authority_reference",
            auxiliary_authority_reference,
            "scientific_auxiliary_authority",
        )
        auxiliary_projection_ref = _require_reference(
            "auxiliary_projection_reference",
            auxiliary_projection_reference,
            "calibration_auxiliary_projection",
        )
        auxiliary_projection_ver = _require_positive_integer(
            "auxiliary_projection_version", auxiliary_projection_version
        )
        projection_digest = _require_digest(
            "auxiliary_projection_digest", auxiliary_projection_digest
        )
        auxiliary_purpose_ref = _require_reference(
            "auxiliary_purpose_reference",
            auxiliary_purpose_reference,
            "scientific_data_use_purpose",
        )
        auxiliary_purpose_evidence = _require_digest(
            "auxiliary_purpose_digest", auxiliary_purpose_digest
        )
        auxiliary_owner_ref = _require_reference(
            "auxiliary_owner_contract_reference",
            auxiliary_owner_contract_reference,
            "released_owner_contract",
        )
        auxiliary_owner_ver = _require_positive_integer(
            "auxiliary_owner_contract_version", auxiliary_owner_contract_version
        )
        auxiliary_owner_evidence = _require_digest(
            "auxiliary_owner_contract_digest", auxiliary_owner_contract_digest
        )
        auxiliary_authorization_ref = _require_reference(
            "auxiliary_authorization_receipt_reference",
            auxiliary_authorization_receipt_reference,
            "scientific_data_authorization",
        )
        auxiliary_authorization_evidence = _require_digest(
            "auxiliary_authorization_receipt_digest",
            auxiliary_authorization_receipt_digest,
        )
        auxiliary_use_ref = _require_reference(
            "auxiliary_scientific_use_receipt_reference",
            auxiliary_scientific_use_receipt_reference,
            "scientific_use_receipt",
        )
        auxiliary_use_evidence = _require_digest(
            "auxiliary_scientific_use_receipt_digest",
            auxiliary_scientific_use_receipt_digest,
        )
        auxiliary_use_at = _require_aware_datetime(
            "auxiliary_scientific_use_at", auxiliary_scientific_use_at
        )
        benchmark_ref = _require_reference(
            "benchmark_receipt_reference",
            benchmark_receipt_reference,
            "calibration_benchmark_receipt",
        )
        benchmark_version = _require_positive_integer(
            "benchmark_receipt_version", benchmark_receipt_version
        )
        benchmark_digest = _require_digest(
            "benchmark_receipt_digest", benchmark_receipt_digest
        )
        benchmark_owner_ref = _require_reference(
            "benchmark_owner_contract_reference",
            benchmark_owner_contract_reference,
            "released_owner_contract",
        )
        benchmark_owner_ver = _require_positive_integer(
            "benchmark_owner_contract_version", benchmark_owner_contract_version
        )
        benchmark_owner_evidence = _require_digest(
            "benchmark_owner_contract_digest", benchmark_owner_contract_digest
        )
        benchmark_at = _require_aware_datetime(
            "benchmark_reference_at", benchmark_reference_at
        )
        algorithm_ref = _require_reference(
            "algorithm_reference", algorithm_reference, "calibration_algorithm"
        )
        algorithm_ver = _require_positive_integer("algorithm_version", algorithm_version)
        constraints = _require_digest("constraints_digest", constraints_digest)
        termination = _require_termination_code(termination_code)
        input_digest = _require_digest(
            "input_weight_artifact_digest", input_weight_artifact_digest
        )
        output_digest = _require_digest(
            "output_weight_artifact_digest", output_weight_artifact_digest
        )
        if input_digest == output_digest:
            raise ValueError(
                "output_weight_artifact_digest must identify the calibrated weight artifact."
            )
        constructed = _require_aware_datetime("constructed_at", constructed_at)
        if auxiliary_use_at > constructed:
            raise ValueError(
                "auxiliary_scientific_use_at cannot be later than constructed_at."
            )
        if benchmark_at > constructed:
            raise ValueError("benchmark_reference_at cannot be later than constructed_at.")

        fallback_values = (
            fallback_reason_code,
            fallback_rule_reference,
            fallback_rule_digest,
            fallback_algorithm_reference,
            fallback_algorithm_version,
            fallback_configuration_digest,
        )
        if termination == "fallback_applied":
            if any(value is None for value in fallback_values):
                raise ValueError(
                    "fallback reason, rule, algorithm, version, and configuration evidence "
                    "are required for fallback_applied."
                )
            fallback_reason = _require_code("fallback_reason_code", fallback_reason_code)
            fallback_rule_ref = _require_reference(
                "fallback_rule_reference",
                fallback_rule_reference,
                "calibration_fallback_rule",
            )
            fallback_rule_evidence = _require_digest(
                "fallback_rule_digest", fallback_rule_digest
            )
            fallback_algorithm_ref = _require_reference(
                "fallback_algorithm_reference",
                fallback_algorithm_reference,
                "calibration_algorithm",
            )
            fallback_algorithm_ver = _require_positive_integer(
                "fallback_algorithm_version", fallback_algorithm_version
            )
            fallback_configuration = _require_digest(
                "fallback_configuration_digest", fallback_configuration_digest
            )
        else:
            if any(value is not None for value in fallback_values):
                raise ValueError("fallback evidence must be absent when calibration converged.")
            fallback_reason = None
            fallback_rule_ref = None
            fallback_rule_evidence = None
            fallback_algorithm_ref = None
            fallback_algorithm_ver = None
            fallback_configuration = None

        owner_ref = _require_reference(
            "owner_contract_reference", owner_contract_reference, "released_owner_contract"
        )
        owner_version = _require_positive_integer(
            "owner_contract_version", owner_contract_version
        )
        owner_digest = _require_digest("owner_contract_digest", owner_contract_digest)
        owner_released = _require_aware_datetime(
            "owner_contract_released_at", owner_contract_released_at
        )
        release_instant = _require_aware_datetime("released_at", released_at)
        if release_instant < constructed:
            raise ValueError("released_at cannot precede constructed_at.")
        if owner_released > release_instant:
            raise ValueError(
                "owner_contract_released_at cannot be later than released_at."
            )

        return tuple.__new__(
            cls,
            (
                tenant_identity,
                study_identity,
                receipt_ref,
                receipt_digest,
                version,
                projection_digest,
                benchmark_digest,
                algorithm_ref,
                algorithm_ver,
                constraints,
                termination,
                input_digest,
                output_digest,
                constructed,
                fallback_reason,
                fallback_rule_ref,
                fallback_rule_evidence,
                fallback_algorithm_ref,
                fallback_algorithm_ver,
                fallback_configuration,
                owner_ref,
                owner_version,
                owner_digest,
                owner_released,
                release_instant,
                target_digest,
                analysis_window_ref,
                auxiliary_authority_ref,
                auxiliary_projection_ref,
                auxiliary_projection_ver,
                auxiliary_purpose_ref,
                auxiliary_purpose_evidence,
                auxiliary_owner_ref,
                auxiliary_owner_ver,
                auxiliary_owner_evidence,
                auxiliary_authorization_ref,
                auxiliary_authorization_evidence,
                auxiliary_use_ref,
                auxiliary_use_evidence,
                auxiliary_use_at,
                benchmark_ref,
                benchmark_version,
                benchmark_owner_ref,
                benchmark_owner_ver,
                benchmark_owner_evidence,
                benchmark_at,
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
    def calibration_receipt_reference(self) -> str:
        """Return the typed calibration-adjustment receipt reference."""
        return self[2]

    @property
    def calibration_receipt_digest(self) -> str:
        """Return the exact calibration-adjustment receipt digest."""
        return self[3]

    @property
    def evidence_version(self) -> int:
        """Return the receipt evidence version."""
        return self[4]

    @property
    def auxiliary_projection_digest(self) -> str:
        """Return the purpose-limited auxiliary projection digest used by the receipt."""
        return self[5]

    @property
    def benchmark_receipt_digest(self) -> str:
        """Return the benchmark receipt digest used by the receipt."""
        return self[6]

    @property
    def algorithm_reference(self) -> str:
        """Return the primary calibration algorithm reference."""
        return self[7]

    @property
    def algorithm_version(self) -> int:
        """Return the primary calibration algorithm version."""
        return self[8]

    @property
    def constraints_digest(self) -> str:
        """Return the immutable calibration constraints digest."""
        return self[9]

    @property
    def termination_code(self) -> str:
        """Return whether the primary method converged or fallback produced weights."""
        return self[10]

    @property
    def input_weight_artifact_digest(self) -> str:
        """Return the input weight artifact digest."""
        return self[11]

    @property
    def output_weight_artifact_digest(self) -> str:
        """Return the calibrated output weight artifact digest."""
        return self[12]

    @property
    def constructed_at(self) -> datetime:
        """Return when the typed calibration receipt was constructed."""
        return self[13]

    @property
    def fallback_reason_code(self) -> str | None:
        """Return the primary failure reason when fallback produced the weights."""
        return self[14]

    @property
    def fallback_rule_reference(self) -> str | None:
        """Return the immutable fallback-rule reference when fallback was applied."""
        return self[15]

    @property
    def fallback_rule_digest(self) -> str | None:
        """Return the immutable fallback-rule digest when fallback was applied."""
        return self[16]

    @property
    def fallback_algorithm_reference(self) -> str | None:
        """Return the actual algorithm that produced fallback weights."""
        return self[17]

    @property
    def fallback_algorithm_version(self) -> int | None:
        """Return the actual fallback algorithm version."""
        return self[18]

    @property
    def fallback_configuration_digest(self) -> str | None:
        """Return the actual fallback configuration digest when fallback was applied."""
        return self[19]

    @property
    def owner_contract_reference(self) -> str:
        """Return the released application owner-contract reference."""
        return self[20]

    @property
    def owner_contract_version(self) -> int:
        """Return the released application owner-contract version."""
        return self[21]

    @property
    def owner_contract_digest(self) -> str:
        """Return the released application owner-contract digest."""
        return self[22]

    @property
    def owner_contract_released_at(self) -> datetime:
        """Return when the governing application owner contract became authority."""
        return self[23]

    @property
    def released_at(self) -> datetime:
        """Return when this typed calibration evidence became released authority."""
        return self[24]

    @property
    def target_population_digest(self) -> str:
        """Return the exact target population governed by the calibration receipt."""
        return self[25]

    @property
    def analysis_window_reference(self) -> str:
        """Return the analysis window governed by the calibration receipt."""
        return self[26]

    @property
    def auxiliary_authority_reference(self) -> str:
        """Return the scientific auxiliary-authority reference."""
        return self[27]

    @property
    def auxiliary_projection_reference(self) -> str:
        """Return the exact purpose-limited auxiliary projection reference."""
        return self[28]

    @property
    def auxiliary_projection_version(self) -> int:
        """Return the exact purpose-limited auxiliary projection version."""
        return self[29]

    @property
    def auxiliary_purpose_reference(self) -> str:
        """Return the scientific data-use purpose reference."""
        return self[30]

    @property
    def auxiliary_purpose_digest(self) -> str:
        """Return the scientific data-use purpose digest."""
        return self[31]

    @property
    def auxiliary_owner_contract_reference(self) -> str:
        """Return the auxiliary owner's released contract reference."""
        return self[32]

    @property
    def auxiliary_owner_contract_version(self) -> int:
        """Return the auxiliary owner's released contract version."""
        return self[33]

    @property
    def auxiliary_owner_contract_digest(self) -> str:
        """Return the auxiliary owner's released contract digest."""
        return self[34]

    @property
    def auxiliary_authorization_receipt_reference(self) -> str:
        """Return the purpose-bound auxiliary authorization receipt reference."""
        return self[35]

    @property
    def auxiliary_authorization_receipt_digest(self) -> str:
        """Return the purpose-bound auxiliary authorization receipt digest."""
        return self[36]

    @property
    def auxiliary_scientific_use_receipt_reference(self) -> str:
        """Return the scientific-use receipt reference."""
        return self[37]

    @property
    def auxiliary_scientific_use_receipt_digest(self) -> str:
        """Return the scientific-use receipt digest."""
        return self[38]

    @property
    def auxiliary_scientific_use_at(self) -> datetime:
        """Return the exact scientific-use instant committed by the receipt."""
        return self[39]

    @property
    def benchmark_receipt_reference(self) -> str:
        """Return the exact calibration benchmark receipt reference."""
        return self[40]

    @property
    def benchmark_receipt_version(self) -> int:
        """Return the exact calibration benchmark receipt version."""
        return self[41]

    @property
    def benchmark_owner_contract_reference(self) -> str:
        """Return the benchmark owner's released contract reference."""
        return self[42]

    @property
    def benchmark_owner_contract_version(self) -> int:
        """Return the benchmark owner's released contract version."""
        return self[43]

    @property
    def benchmark_owner_contract_digest(self) -> str:
        """Return the benchmark owner's released contract digest."""
        return self[44]

    @property
    def benchmark_reference_at(self) -> datetime:
        """Return the exact benchmark reference instant committed by the receipt."""
        return self[45]


class CalibrationAdjustmentAuthorityView(tuple):
    """Field-minimized typed calibration evidence issued only after authorization."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        fields: tuple[tuple[str, object], ...],
    ) -> CalibrationAdjustmentAuthorityView:
        """Reject direct construction; only the resolver may issue this view."""
        raise TypeError(
            "CalibrationAdjustmentAuthorityView is issued only by "
            "resolve_calibration_adjustment_authority."
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
        """Return immutable typed calibration provenance without source values."""
        return self[2]


@runtime_checkable
class CalibrationAdjustmentAuthorityReadPort(Protocol):
    """Owner read contract for released typed calibration-adjustment evidence."""

    def read_calibration_adjustment_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        calibration_receipt_reference: str,
        calibration_receipt_digest: str,
        evidence_version: int,
        target_population_digest: str,
        analysis_window_reference: str,
        auxiliary_authority_reference: str,
        auxiliary_projection_reference: str,
        auxiliary_projection_version: int,
        auxiliary_projection_digest: str,
        auxiliary_purpose_reference: str,
        auxiliary_purpose_digest: str,
        auxiliary_owner_contract_reference: str,
        auxiliary_owner_contract_version: int,
        auxiliary_owner_contract_digest: str,
        auxiliary_authorization_receipt_reference: str,
        auxiliary_authorization_receipt_digest: str,
        auxiliary_scientific_use_receipt_reference: str,
        auxiliary_scientific_use_receipt_digest: str,
        auxiliary_scientific_use_at: datetime,
        benchmark_receipt_reference: str,
        benchmark_receipt_version: int,
        benchmark_receipt_digest: str,
        benchmark_owner_contract_reference: str,
        benchmark_owner_contract_version: int,
        benchmark_owner_contract_digest: str,
        benchmark_reference_at: datetime,
        algorithm_reference: str,
        algorithm_version: int,
        constraints_digest: str,
        termination_code: str,
        input_weight_artifact_digest: str,
        output_weight_artifact_digest: str,
        constructed_at: datetime,
        fallback_reason_code: str | None,
        fallback_rule_reference: str | None,
        fallback_rule_digest: str | None,
        fallback_algorithm_reference: str | None,
        fallback_algorithm_version: int | None,
        fallback_configuration_digest: str | None,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
    ) -> CalibrationAdjustmentAuthorityRecord | None:
        """Return matching released typed calibration evidence or ``None``."""
        ...


_PROTOCOL_READ_CAPABILITY = getattr_static(
    CalibrationAdjustmentAuthorityReadPort, "read_calibration_adjustment_authority"
)


def _coordinate_tuple(record: CalibrationAdjustmentAuthorityRecord) -> tuple[object, ...]:
    """Return caller-known coordinates, excluding owner-resolved release instants."""
    return record[:23] + record[25:46]


def resolve_calibration_adjustment_authority(
    *,
    principal: ValidationPrincipal,
    tenant_record_id: UUID,
    validity_study_id: UUID,
    calibration_receipt_reference: str,
    calibration_receipt_digest: str,
    evidence_version: int,
    target_population_digest: str,
    analysis_window_reference: str,
    auxiliary_authority_reference: str,
    auxiliary_projection_reference: str,
    auxiliary_projection_version: int,
    auxiliary_projection_digest: str,
    auxiliary_purpose_reference: str,
    auxiliary_purpose_digest: str,
    auxiliary_owner_contract_reference: str,
    auxiliary_owner_contract_version: int,
    auxiliary_owner_contract_digest: str,
    auxiliary_authorization_receipt_reference: str,
    auxiliary_authorization_receipt_digest: str,
    auxiliary_scientific_use_receipt_reference: str,
    auxiliary_scientific_use_receipt_digest: str,
    auxiliary_scientific_use_at: datetime,
    benchmark_receipt_reference: str,
    benchmark_receipt_version: int,
    benchmark_receipt_digest: str,
    benchmark_owner_contract_reference: str,
    benchmark_owner_contract_version: int,
    benchmark_owner_contract_digest: str,
    benchmark_reference_at: datetime,
    algorithm_reference: str,
    algorithm_version: int,
    constraints_digest: str,
    termination_code: str,
    input_weight_artifact_digest: str,
    output_weight_artifact_digest: str,
    constructed_at: datetime,
    fallback_reason_code: str | None,
    fallback_rule_reference: str | None,
    fallback_rule_digest: str | None,
    fallback_algorithm_reference: str | None,
    fallback_algorithm_version: int | None,
    fallback_configuration_digest: str | None,
    owner_contract_reference: str,
    owner_contract_version: int,
    owner_contract_digest: str,
    used_at: datetime,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    read_port: CalibrationAdjustmentAuthorityReadPort,
) -> CalibrationAdjustmentAuthorityView:
    """Authorize then corroborate the exact released calibration receipt."""
    if type(principal) is not ValidationPrincipal:
        raise TypeError("principal must be an exact ValidationPrincipal.")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be an exact PurposeBoundAccessPolicy.")
    read_capability = getattr_static(
        type(read_port), "read_calibration_adjustment_authority", None
    )
    if (
        type(read_capability) is not FunctionType
        or read_capability is _PROTOCOL_READ_CAPABILITY
    ):
        raise TypeError(
            "read_port must expose a statically callable "
            "read_calibration_adjustment_authority."
        )

    detached_principal = ValidationPrincipal(
        tenant_record_id=principal.tenant_record_id,
        actor_reference=principal.actor_reference,
        granted_scope_codes=principal.granted_scope_codes,
    )
    requested = CalibrationAdjustmentAuthorityRecord(
        tenant_record_id=tenant_record_id,
        validity_study_id=validity_study_id,
        calibration_receipt_reference=calibration_receipt_reference,
        calibration_receipt_digest=calibration_receipt_digest,
        evidence_version=evidence_version,
        target_population_digest=target_population_digest,
        analysis_window_reference=analysis_window_reference,
        auxiliary_authority_reference=auxiliary_authority_reference,
        auxiliary_projection_reference=auxiliary_projection_reference,
        auxiliary_projection_version=auxiliary_projection_version,
        auxiliary_projection_digest=auxiliary_projection_digest,
        auxiliary_purpose_reference=auxiliary_purpose_reference,
        auxiliary_purpose_digest=auxiliary_purpose_digest,
        auxiliary_owner_contract_reference=auxiliary_owner_contract_reference,
        auxiliary_owner_contract_version=auxiliary_owner_contract_version,
        auxiliary_owner_contract_digest=auxiliary_owner_contract_digest,
        auxiliary_authorization_receipt_reference=auxiliary_authorization_receipt_reference,
        auxiliary_authorization_receipt_digest=auxiliary_authorization_receipt_digest,
        auxiliary_scientific_use_receipt_reference=auxiliary_scientific_use_receipt_reference,
        auxiliary_scientific_use_receipt_digest=auxiliary_scientific_use_receipt_digest,
        auxiliary_scientific_use_at=auxiliary_scientific_use_at,
        benchmark_receipt_reference=benchmark_receipt_reference,
        benchmark_receipt_version=benchmark_receipt_version,
        benchmark_receipt_digest=benchmark_receipt_digest,
        benchmark_owner_contract_reference=benchmark_owner_contract_reference,
        benchmark_owner_contract_version=benchmark_owner_contract_version,
        benchmark_owner_contract_digest=benchmark_owner_contract_digest,
        benchmark_reference_at=benchmark_reference_at,
        algorithm_reference=algorithm_reference,
        algorithm_version=algorithm_version,
        constraints_digest=constraints_digest,
        termination_code=termination_code,
        input_weight_artifact_digest=input_weight_artifact_digest,
        output_weight_artifact_digest=output_weight_artifact_digest,
        constructed_at=constructed_at,
        fallback_reason_code=fallback_reason_code,
        fallback_rule_reference=fallback_rule_reference,
        fallback_rule_digest=fallback_rule_digest,
        fallback_algorithm_reference=fallback_algorithm_reference,
        fallback_algorithm_version=fallback_algorithm_version,
        fallback_configuration_digest=fallback_configuration_digest,
        owner_contract_reference=owner_contract_reference,
        owner_contract_version=owner_contract_version,
        owner_contract_digest=owner_contract_digest,
        owner_contract_released_at=constructed_at,
        released_at=constructed_at,
    )
    tenant_id = requested.tenant_record_id
    study_id = requested.validity_study_id
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
        tenant_record_id=requested.tenant_record_id,
        validity_study_id=requested.validity_study_id,
        calibration_receipt_reference=requested.calibration_receipt_reference,
        calibration_receipt_digest=requested.calibration_receipt_digest,
        evidence_version=requested.evidence_version,
        target_population_digest=requested.target_population_digest,
        analysis_window_reference=requested.analysis_window_reference,
        auxiliary_authority_reference=requested.auxiliary_authority_reference,
        auxiliary_projection_reference=requested.auxiliary_projection_reference,
        auxiliary_projection_version=requested.auxiliary_projection_version,
        auxiliary_projection_digest=requested.auxiliary_projection_digest,
        auxiliary_purpose_reference=requested.auxiliary_purpose_reference,
        auxiliary_purpose_digest=requested.auxiliary_purpose_digest,
        auxiliary_owner_contract_reference=requested.auxiliary_owner_contract_reference,
        auxiliary_owner_contract_version=requested.auxiliary_owner_contract_version,
        auxiliary_owner_contract_digest=requested.auxiliary_owner_contract_digest,
        auxiliary_authorization_receipt_reference=requested.auxiliary_authorization_receipt_reference,
        auxiliary_authorization_receipt_digest=requested.auxiliary_authorization_receipt_digest,
        auxiliary_scientific_use_receipt_reference=requested.auxiliary_scientific_use_receipt_reference,
        auxiliary_scientific_use_receipt_digest=requested.auxiliary_scientific_use_receipt_digest,
        auxiliary_scientific_use_at=requested.auxiliary_scientific_use_at,
        benchmark_receipt_reference=requested.benchmark_receipt_reference,
        benchmark_receipt_version=requested.benchmark_receipt_version,
        benchmark_receipt_digest=requested.benchmark_receipt_digest,
        benchmark_owner_contract_reference=requested.benchmark_owner_contract_reference,
        benchmark_owner_contract_version=requested.benchmark_owner_contract_version,
        benchmark_owner_contract_digest=requested.benchmark_owner_contract_digest,
        benchmark_reference_at=requested.benchmark_reference_at,
        algorithm_reference=requested.algorithm_reference,
        algorithm_version=requested.algorithm_version,
        constraints_digest=requested.constraints_digest,
        termination_code=requested.termination_code,
        input_weight_artifact_digest=requested.input_weight_artifact_digest,
        output_weight_artifact_digest=requested.output_weight_artifact_digest,
        constructed_at=requested.constructed_at,
        fallback_reason_code=requested.fallback_reason_code,
        fallback_rule_reference=requested.fallback_rule_reference,
        fallback_rule_digest=requested.fallback_rule_digest,
        fallback_algorithm_reference=requested.fallback_algorithm_reference,
        fallback_algorithm_version=requested.fallback_algorithm_version,
        fallback_configuration_digest=requested.fallback_configuration_digest,
        owner_contract_reference=requested.owner_contract_reference,
        owner_contract_version=requested.owner_contract_version,
        owner_contract_digest=requested.owner_contract_digest,
    )
    if persisted is None:
        raise CalibrationAdjustmentAuthorityNotFound(str(study_id))
    if type(persisted) is not CalibrationAdjustmentAuthorityRecord:
        raise CalibrationAdjustmentAuthorityIntegrityError(
            "owner port returned non-canonical calibration-adjustment authority evidence"
        )

    record = CalibrationAdjustmentAuthorityRecord(
        tenant_record_id=persisted.tenant_record_id,
        validity_study_id=persisted.validity_study_id,
        calibration_receipt_reference=persisted.calibration_receipt_reference,
        calibration_receipt_digest=persisted.calibration_receipt_digest,
        evidence_version=persisted.evidence_version,
        target_population_digest=persisted.target_population_digest,
        analysis_window_reference=persisted.analysis_window_reference,
        auxiliary_authority_reference=persisted.auxiliary_authority_reference,
        auxiliary_projection_reference=persisted.auxiliary_projection_reference,
        auxiliary_projection_version=persisted.auxiliary_projection_version,
        auxiliary_projection_digest=persisted.auxiliary_projection_digest,
        auxiliary_purpose_reference=persisted.auxiliary_purpose_reference,
        auxiliary_purpose_digest=persisted.auxiliary_purpose_digest,
        auxiliary_owner_contract_reference=persisted.auxiliary_owner_contract_reference,
        auxiliary_owner_contract_version=persisted.auxiliary_owner_contract_version,
        auxiliary_owner_contract_digest=persisted.auxiliary_owner_contract_digest,
        auxiliary_authorization_receipt_reference=persisted.auxiliary_authorization_receipt_reference,
        auxiliary_authorization_receipt_digest=persisted.auxiliary_authorization_receipt_digest,
        auxiliary_scientific_use_receipt_reference=persisted.auxiliary_scientific_use_receipt_reference,
        auxiliary_scientific_use_receipt_digest=persisted.auxiliary_scientific_use_receipt_digest,
        auxiliary_scientific_use_at=persisted.auxiliary_scientific_use_at,
        benchmark_receipt_reference=persisted.benchmark_receipt_reference,
        benchmark_receipt_version=persisted.benchmark_receipt_version,
        benchmark_receipt_digest=persisted.benchmark_receipt_digest,
        benchmark_owner_contract_reference=persisted.benchmark_owner_contract_reference,
        benchmark_owner_contract_version=persisted.benchmark_owner_contract_version,
        benchmark_owner_contract_digest=persisted.benchmark_owner_contract_digest,
        benchmark_reference_at=persisted.benchmark_reference_at,
        algorithm_reference=persisted.algorithm_reference,
        algorithm_version=persisted.algorithm_version,
        constraints_digest=persisted.constraints_digest,
        termination_code=persisted.termination_code,
        input_weight_artifact_digest=persisted.input_weight_artifact_digest,
        output_weight_artifact_digest=persisted.output_weight_artifact_digest,
        constructed_at=persisted.constructed_at,
        fallback_reason_code=persisted.fallback_reason_code,
        fallback_rule_reference=persisted.fallback_rule_reference,
        fallback_rule_digest=persisted.fallback_rule_digest,
        fallback_algorithm_reference=persisted.fallback_algorithm_reference,
        fallback_algorithm_version=persisted.fallback_algorithm_version,
        fallback_configuration_digest=persisted.fallback_configuration_digest,
        owner_contract_reference=persisted.owner_contract_reference,
        owner_contract_version=persisted.owner_contract_version,
        owner_contract_digest=persisted.owner_contract_digest,
        owner_contract_released_at=persisted.owner_contract_released_at,
        released_at=persisted.released_at,
    )
    if _coordinate_tuple(record) != _coordinate_tuple(requested):
        raise CalibrationAdjustmentAuthorityIntegrityError(
            "released calibration-adjustment authority does not match requested coordinates"
        )
    if record.released_at > use_instant:
        raise CalibrationAdjustmentAuthorityIntegrityError(
            "calibration-adjustment evidence must be released before scientific use"
        )

    fields: tuple[tuple[str, object], ...] = (
        ("algorithm_reference", record.algorithm_reference),
        ("algorithm_version", record.algorithm_version),
        ("analysis_window_reference", record.analysis_window_reference),
        ("auxiliary_authority_reference", record.auxiliary_authority_reference),
        ("auxiliary_authorization_receipt_digest", record.auxiliary_authorization_receipt_digest),
        ("auxiliary_authorization_receipt_reference", record.auxiliary_authorization_receipt_reference),
        ("auxiliary_owner_contract_digest", record.auxiliary_owner_contract_digest),
        ("auxiliary_owner_contract_reference", record.auxiliary_owner_contract_reference),
        ("auxiliary_owner_contract_version", record.auxiliary_owner_contract_version),
        ("auxiliary_projection_digest", record.auxiliary_projection_digest),
        ("auxiliary_projection_reference", record.auxiliary_projection_reference),
        ("auxiliary_projection_version", record.auxiliary_projection_version),
        ("auxiliary_purpose_digest", record.auxiliary_purpose_digest),
        ("auxiliary_purpose_reference", record.auxiliary_purpose_reference),
        ("auxiliary_scientific_use_at", record.auxiliary_scientific_use_at),
        ("auxiliary_scientific_use_receipt_digest", record.auxiliary_scientific_use_receipt_digest),
        ("auxiliary_scientific_use_receipt_reference", record.auxiliary_scientific_use_receipt_reference),
        ("benchmark_owner_contract_digest", record.benchmark_owner_contract_digest),
        ("benchmark_owner_contract_reference", record.benchmark_owner_contract_reference),
        ("benchmark_owner_contract_version", record.benchmark_owner_contract_version),
        ("benchmark_receipt_digest", record.benchmark_receipt_digest),
        ("benchmark_receipt_reference", record.benchmark_receipt_reference),
        ("benchmark_receipt_version", record.benchmark_receipt_version),
        ("benchmark_reference_at", record.benchmark_reference_at),
        ("calibration_receipt_digest", record.calibration_receipt_digest),
        ("calibration_receipt_reference", record.calibration_receipt_reference),
        ("constraints_digest", record.constraints_digest),
        ("constructed_at", record.constructed_at),
        ("evidence_version", record.evidence_version),
        ("input_weight_artifact_digest", record.input_weight_artifact_digest),
        ("output_weight_artifact_digest", record.output_weight_artifact_digest),
        ("owner_contract_digest", record.owner_contract_digest),
        ("owner_contract_reference", record.owner_contract_reference),
        ("owner_contract_released_at", record.owner_contract_released_at),
        ("owner_contract_version", record.owner_contract_version),
        ("released_at", record.released_at),
        ("target_population_digest", record.target_population_digest),
        ("termination_code", record.termination_code),
    )
    if record.termination_code == "fallback_applied":
        fields += (
            ("fallback_algorithm_reference", record.fallback_algorithm_reference),
            ("fallback_algorithm_version", record.fallback_algorithm_version),
            ("fallback_configuration_digest", record.fallback_configuration_digest),
            ("fallback_reason_code", record.fallback_reason_code),
            ("fallback_rule_digest", record.fallback_rule_digest),
            ("fallback_rule_reference", record.fallback_rule_reference),
        )
    return tuple.__new__(
        CalibrationAdjustmentAuthorityView,
        (
            _store_operational_uuid("tenant_record_id", tenant_id),
            _store_operational_uuid("validity_study_id", study_id),
            fields,
        ),
    )
