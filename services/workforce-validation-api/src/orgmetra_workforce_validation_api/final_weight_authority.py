"""Corroborate the complete released final analysis-weight construction.

This application boundary verifies the scientific coordinates needed to reproduce
one final point-estimation weight receipt without importing mutable validity-
analysis source, copying row-level weights, or querying foreign application
tables. Durable persistence remains the responsibility of the owner adapter.
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

_RESOURCE_KIND = "final_analysis_weight_authority"
_OPERATION = "read"
_FINAL_ANALYSIS_WEIGHT_VIEW_ISSUANCE_MARKER = object()
_WEIGHT_SCOPE_CODES = frozenset({"cross_sectional", "longitudinal"})
_SPECIALIZED_EVIDENCE_KIND_BY_ADJUSTMENT_CODE = {
    "nonresponse_adjustment": "nonresponse_adjustment_receipt",
    "calibration_adjustment": "calibration_adjustment_receipt",
    "raking_adjustment": "calibration_adjustment_receipt",
    "poststratification_adjustment": "calibration_adjustment_receipt",
    "weight_trimming_adjustment": "trimming_bounding_adjustment_receipt",
    "weight_bounding_adjustment": "trimming_bounding_adjustment_receipt",
    "weight_winsorization_adjustment": "trimming_bounding_adjustment_receipt",
}
_READ_FIELDS = frozenset(
    {
        "analysis_weight_receipt_reference",
        "analysis_weight_receipt_digest",
        "evidence_version",
        "estimand_reference",
        "estimand_digest",
        "estimand_scope_code",
        "target_population_reference",
        "target_population_digest",
        "analysis_unit_code",
        "analysis_window_reference",
        "reference_duration_reference",
        "reference_duration_digest",
        "eligible_case_set_digest",
        "analytic_case_occurrence_set_digest",
        "source_universe_receipt_reference",
        "source_universe_receipt_version",
        "source_universe_receipt_digest",
        "sampling_design_receipt_reference",
        "sampling_design_receipt_version",
        "sampling_design_receipt_digest",
        "base_weight_method_code",
        "base_weight_method_version",
        "base_weight_evidence_digest",
        "base_weight_artifact_digest",
        "adjustments",
        "final_weight_artifact_digest",
        "weight_eligibility_receipt_reference",
        "weight_eligibility_receipt_digest",
        "analytic_case_count",
        "constructed_at",
        "correction_sequence",
        "supersedes_receipt_digest",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
    }
)


class FinalAnalysisWeightAuthorityNotFound(LookupError):
    """Indicate that no released owner evidence corroborates the final-weight receipt."""


class FinalAnalysisWeightAuthorityIntegrityError(RuntimeError):
    """Indicate that owner evidence cannot corroborate the requested final-weight lineage."""


def _require_weight_scope(value: object) -> str:
    """Require explicit cross-sectional or longitudinal estimand semantics."""
    if type(value) is not str or value not in _WEIGHT_SCOPE_CODES:
        raise ValueError("estimand_scope_code must be cross_sectional or longitudinal.")
    return value


class FinalWeightAdjustmentCoordinate(tuple):
    """Immutable, value-minimized coordinate for one ordered weight transform."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        sequence_number: int,
        adjustment_code: str,
        method_reference: str,
        method_version: int,
        input_weight_artifact_digest: str,
        output_weight_artifact_digest: str,
        configuration_digest: str,
        evidence_receipt_digest: str,
        evidence_kind: str,
    ) -> FinalWeightAdjustmentCoordinate:
        """Validate one transform without storing case-level weight values."""
        sequence = _require_positive_integer("sequence_number", sequence_number)
        code = _require_code("adjustment_code", adjustment_code)
        method_ref = _require_reference("method_reference", method_reference, "weight_method")
        method_ver = _require_positive_integer("method_version", method_version)
        input_digest = _require_digest(
            "input_weight_artifact_digest", input_weight_artifact_digest
        )
        output_digest = _require_digest(
            "output_weight_artifact_digest", output_weight_artifact_digest
        )
        config_digest = _require_digest("configuration_digest", configuration_digest)
        evidence_digest = _require_digest("evidence_receipt_digest", evidence_receipt_digest)
        kind = _require_code("evidence_kind", evidence_kind)
        required_kind = _SPECIALIZED_EVIDENCE_KIND_BY_ADJUSTMENT_CODE.get(code)
        if required_kind is not None and kind != required_kind:
            raise ValueError(f"{code} requires evidence_kind {required_kind}.")
        if input_digest == output_digest:
            raise ValueError(
                "output_weight_artifact_digest must identify the transformed weight artifact."
            )
        return tuple.__new__(
            cls,
            (
                sequence,
                code,
                method_ref,
                method_ver,
                input_digest,
                output_digest,
                config_digest,
                evidence_digest,
                kind,
            ),
        )

    @property
    def sequence_number(self) -> int:
        """Return the one-based transform order."""
        return self[0]

    @property
    def adjustment_code(self) -> str:
        """Return the controlled adjustment code."""
        return self[1]

    @property
    def method_reference(self) -> str:
        """Return the controlled weight-method reference."""
        return self[2]

    @property
    def method_version(self) -> int:
        """Return the positive weight-method version."""
        return self[3]

    @property
    def input_weight_artifact_digest(self) -> str:
        """Return the transform input artifact digest."""
        return self[4]

    @property
    def output_weight_artifact_digest(self) -> str:
        """Return the transform output artifact digest."""
        return self[5]

    @property
    def configuration_digest(self) -> str:
        """Return the immutable transform configuration digest."""
        return self[6]

    @property
    def evidence_receipt_digest(self) -> str:
        """Return the immutable supporting evidence-receipt digest."""
        return self[7]

    @property
    def evidence_kind(self) -> str:
        """Return the typed supporting evidence kind."""
        return self[8]


class FinalAnalysisWeightAuthorityRecord(tuple):
    """Immutable owner projection for one complete released final-weight receipt."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        analysis_weight_receipt_reference: str,
        analysis_weight_receipt_digest: str,
        evidence_version: int,
        estimand_reference: str,
        estimand_digest: str,
        estimand_scope_code: str,
        target_population_reference: str,
        target_population_digest: str,
        analysis_unit_code: str,
        analysis_window_reference: str,
        reference_duration_reference: str,
        reference_duration_digest: str,
        eligible_case_set_digest: str,
        analytic_case_occurrence_set_digest: str,
        source_universe_receipt_reference: str,
        source_universe_receipt_version: int,
        source_universe_receipt_digest: str,
        sampling_design_receipt_reference: str,
        sampling_design_receipt_version: int,
        sampling_design_receipt_digest: str,
        base_weight_method_code: str,
        base_weight_method_version: int,
        base_weight_evidence_digest: str,
        base_weight_artifact_digest: str,
        adjustments: tuple[FinalWeightAdjustmentCoordinate, ...],
        final_weight_artifact_digest: str,
        weight_eligibility_receipt_reference: str,
        weight_eligibility_receipt_digest: str,
        analytic_case_count: int,
        constructed_at: datetime,
        correction_sequence: int,
        supersedes_receipt_digest: str | None,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
        owner_contract_released_at: datetime,
        released_at: datetime,
        superseded_at: datetime | None = None,
    ) -> FinalAnalysisWeightAuthorityRecord:
        """Validate and detach the complete scientific point-weight lineage."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
        receipt_ref = _require_reference(
            "analysis_weight_receipt_reference",
            analysis_weight_receipt_reference,
            "analysis_weight_receipt",
        )
        receipt_digest = _require_digest(
            "analysis_weight_receipt_digest", analysis_weight_receipt_digest
        )
        version = _require_positive_integer("evidence_version", evidence_version)
        if version != 1:
            raise ValueError("evidence_version must remain 1.")
        estimand_ref = _require_reference(
            "estimand_reference", estimand_reference, "validation_estimand"
        )
        estimand_evidence = _require_digest("estimand_digest", estimand_digest)
        scope = _require_weight_scope(estimand_scope_code)
        target_ref = _require_reference(
            "target_population_reference",
            target_population_reference,
            "analysis_target_population",
        )
        target_digest = _require_digest(
            "target_population_digest", target_population_digest
        )
        unit_code = _require_code("analysis_unit_code", analysis_unit_code)
        window_ref = _require_reference(
            "analysis_window_reference", analysis_window_reference, "analysis_window"
        )
        duration_ref = _require_reference(
            "reference_duration_reference",
            reference_duration_reference,
            "analysis_reference_duration",
        )
        duration_digest = _require_digest(
            "reference_duration_digest", reference_duration_digest
        )
        eligible_digest = _require_digest(
            "eligible_case_set_digest", eligible_case_set_digest
        )
        analytic_digest = _require_digest(
            "analytic_case_occurrence_set_digest", analytic_case_occurrence_set_digest
        )
        source_ref = _require_reference(
            "source_universe_receipt_reference",
            source_universe_receipt_reference,
            "source_universe_receipt",
        )
        source_version = _require_positive_integer(
            "source_universe_receipt_version", source_universe_receipt_version
        )
        source_digest = _require_digest(
            "source_universe_receipt_digest", source_universe_receipt_digest
        )
        sampling_ref = _require_reference(
            "sampling_design_receipt_reference",
            sampling_design_receipt_reference,
            "sampling_design_receipt",
        )
        sampling_version = _require_positive_integer(
            "sampling_design_receipt_version", sampling_design_receipt_version
        )
        sampling_digest = _require_digest(
            "sampling_design_receipt_digest", sampling_design_receipt_digest
        )
        base_method = _require_code("base_weight_method_code", base_weight_method_code)
        base_method_version_value = _require_positive_integer(
            "base_weight_method_version", base_weight_method_version
        )
        base_evidence = _require_digest(
            "base_weight_evidence_digest", base_weight_evidence_digest
        )
        base_artifact = _require_digest(
            "base_weight_artifact_digest", base_weight_artifact_digest
        )
        if type(adjustments) is not tuple:
            raise ValueError("adjustments must be an immutable tuple.")
        detached_adjustments: list[FinalWeightAdjustmentCoordinate] = []
        expected_input = base_artifact
        for expected_sequence, adjustment in enumerate(adjustments, start=1):
            if type(adjustment) is not FinalWeightAdjustmentCoordinate:
                raise ValueError(
                    "adjustments must contain exact FinalWeightAdjustmentCoordinate values."
                )
            if adjustment.sequence_number != expected_sequence:
                raise ValueError("adjustments must have contiguous sequence_number values.")
            if adjustment.input_weight_artifact_digest != expected_input:
                raise ValueError(
                    "adjustment input_weight_artifact_digest breaks the weight chain."
                )
            detached = FinalWeightAdjustmentCoordinate(
                sequence_number=adjustment.sequence_number,
                adjustment_code=adjustment.adjustment_code,
                method_reference=adjustment.method_reference,
                method_version=adjustment.method_version,
                input_weight_artifact_digest=adjustment.input_weight_artifact_digest,
                output_weight_artifact_digest=adjustment.output_weight_artifact_digest,
                configuration_digest=adjustment.configuration_digest,
                evidence_receipt_digest=adjustment.evidence_receipt_digest,
                evidence_kind=adjustment.evidence_kind,
            )
            detached_adjustments.append(detached)
            expected_input = detached.output_weight_artifact_digest
        final_artifact = _require_digest(
            "final_weight_artifact_digest", final_weight_artifact_digest
        )
        if expected_input != final_artifact:
            raise ValueError(
                "final_weight_artifact_digest must equal the ordered adjustment chain output."
            )
        eligibility_ref = _require_reference(
            "weight_eligibility_receipt_reference",
            weight_eligibility_receipt_reference,
            "weight_eligibility_receipt",
        )
        eligibility_digest = _require_digest(
            "weight_eligibility_receipt_digest", weight_eligibility_receipt_digest
        )
        case_count = _require_positive_integer("analytic_case_count", analytic_case_count)
        constructed = _require_aware_datetime("constructed_at", constructed_at)
        correction = _require_positive_integer("correction_sequence", correction_sequence)
        supersedes_digest: str | None
        if correction == 1:
            if supersedes_receipt_digest is not None:
                raise ValueError(
                    "supersedes_receipt_digest must be absent for correction_sequence 1."
                )
            supersedes_digest = None
        else:
            if supersedes_receipt_digest is None:
                raise ValueError(
                    "supersedes_receipt_digest is required when correction_sequence exceeds 1."
                )
            supersedes_digest = _require_digest(
                "supersedes_receipt_digest", supersedes_receipt_digest
            )
            if supersedes_digest == receipt_digest:
                raise ValueError("a final analysis-weight receipt cannot supersede itself.")
        owner_ref = _require_reference(
            "owner_contract_reference", owner_contract_reference, "released_owner_contract"
        )
        owner_version = _require_positive_integer(
            "owner_contract_version", owner_contract_version
        )
        owner_digest = _require_digest("owner_contract_digest", owner_contract_digest)
        owner_release_instant = _require_aware_datetime(
            "owner_contract_released_at", owner_contract_released_at
        )
        release_instant = _require_aware_datetime("released_at", released_at)
        if release_instant < constructed:
            raise ValueError("released_at cannot precede constructed_at.")
        if owner_release_instant > release_instant:
            raise ValueError(
                "owner contract must be released no later than the final analysis-weight authority"
            )
        supersession_instant = None
        if superseded_at is not None:
            supersession_instant = _require_aware_datetime("superseded_at", superseded_at)
            if supersession_instant <= release_instant:
                raise ValueError("superseded_at must be later than released_at")

        fields: tuple[tuple[str, object], ...] = (
            ("adjustments", tuple(detached_adjustments)),
            ("analysis_unit_code", unit_code),
            ("analysis_weight_receipt_digest", receipt_digest),
            ("analysis_weight_receipt_reference", receipt_ref),
            ("analysis_window_reference", window_ref),
            ("analytic_case_count", case_count),
            ("analytic_case_occurrence_set_digest", analytic_digest),
            ("base_weight_artifact_digest", base_artifact),
            ("base_weight_evidence_digest", base_evidence),
            ("base_weight_method_code", base_method),
            ("base_weight_method_version", base_method_version_value),
            ("constructed_at", constructed),
            ("correction_sequence", correction),
            ("eligible_case_set_digest", eligible_digest),
            ("estimand_digest", estimand_evidence),
            ("estimand_reference", estimand_ref),
            ("estimand_scope_code", scope),
            ("evidence_version", version),
            ("final_weight_artifact_digest", final_artifact),
            ("owner_contract_digest", owner_digest),
            ("owner_contract_reference", owner_ref),
            ("owner_contract_version", owner_version),
            ("reference_duration_digest", duration_digest),
            ("reference_duration_reference", duration_ref),
            ("sampling_design_receipt_digest", sampling_digest),
            ("sampling_design_receipt_reference", sampling_ref),
            ("sampling_design_receipt_version", sampling_version),
            ("source_universe_receipt_digest", source_digest),
            ("source_universe_receipt_reference", source_ref),
            ("source_universe_receipt_version", source_version),
            ("supersedes_receipt_digest", supersedes_digest),
            ("target_population_digest", target_digest),
            ("target_population_reference", target_ref),
            ("weight_eligibility_receipt_digest", eligibility_digest),
            ("weight_eligibility_receipt_reference", eligibility_ref),
        )
        return tuple.__new__(
            cls,
            (
                tenant_identity,
                study_identity,
                fields,
                release_instant,
                owner_release_instant,
                supersession_instant,
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
    def fields(self) -> tuple[tuple[str, object], ...]:
        """Return immutable scientific coordinates without row-level weights."""
        return self[2]

    @property
    def released_at(self) -> datetime:
        """Return the owner-resolved release instant."""
        return self[3]

    @property
    def owner_contract_released_at(self) -> datetime:
        """Return when the governing owner contract became released authority."""
        return self[4]

    @property
    def superseded_at(self) -> datetime | None:
        """Return the exclusive owner-resolved cutover instant, when one exists."""
        return self[5]


class FinalAnalysisWeightAuthorityView:
    """Sealed field-minimized final-weight evidence issued only after authorization."""

    __slots__ = ("_tenant_identity", "_study_identity", "_fields", "_issuance_marker")

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        fields: tuple[tuple[str, object], ...],
    ) -> FinalAnalysisWeightAuthorityView:
        """Reject public construction; the resolver is the only supported issuer."""
        raise TypeError(
            "FinalAnalysisWeightAuthorityView is issued only by "
            "resolve_final_analysis_weight_authority."
        )

    def __setattr__(self, name: str, value: object) -> None:
        """Keep ordinary callers from mutating issued projection state."""
        raise AttributeError("FinalAnalysisWeightAuthorityView is immutable.")

    def __delattr__(self, name: str) -> None:
        """Keep ordinary callers from deleting issued projection state."""
        raise AttributeError("FinalAnalysisWeightAuthorityView is immutable.")

    def _require_issued(self) -> None:
        """Reject exact-runtime allocations not sealed by the resolver."""
        try:
            marker = object.__getattribute__(self, "_issuance_marker")
        except AttributeError as exc:
            raise FinalAnalysisWeightAuthorityIntegrityError(
                "final analysis-weight view was not issued by "
                "resolve_final_analysis_weight_authority"
            ) from exc
        if marker is not _FINAL_ANALYSIS_WEIGHT_VIEW_ISSUANCE_MARKER:
            raise FinalAnalysisWeightAuthorityIntegrityError(
                "final analysis-weight view was not issued by "
                "resolve_final_analysis_weight_authority"
            )

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh authorized tenant identity."""
        self._require_issued()
        return _restore_operational_uuid(
            "tenant_record_id", object.__getattribute__(self, "_tenant_identity")
        )

    @property
    def validity_study_id(self) -> UUID:
        """Return a fresh authorized validity-study identity."""
        self._require_issued()
        return _restore_operational_uuid(
            "validity_study_id", object.__getattribute__(self, "_study_identity")
        )

    @property
    def fields(self) -> tuple[tuple[str, object], ...]:
        """Return immutable final-weight provenance."""
        self._require_issued()
        return object.__getattribute__(self, "_fields")


@runtime_checkable
class FinalAnalysisWeightAuthorityReadPort(Protocol):
    """Owner read contract for one released final analysis-weight receipt."""

    def read_final_analysis_weight_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        analysis_weight_receipt_reference: str,
        analysis_weight_receipt_digest: str,
        evidence_version: int,
        estimand_reference: str,
        estimand_digest: str,
        estimand_scope_code: str,
        target_population_reference: str,
        target_population_digest: str,
        analysis_unit_code: str,
        analysis_window_reference: str,
        reference_duration_reference: str,
        reference_duration_digest: str,
        eligible_case_set_digest: str,
        analytic_case_occurrence_set_digest: str,
        source_universe_receipt_reference: str,
        source_universe_receipt_version: int,
        source_universe_receipt_digest: str,
        sampling_design_receipt_reference: str,
        sampling_design_receipt_version: int,
        sampling_design_receipt_digest: str,
        base_weight_method_code: str,
        base_weight_method_version: int,
        base_weight_evidence_digest: str,
        base_weight_artifact_digest: str,
        adjustments: tuple[FinalWeightAdjustmentCoordinate, ...],
        final_weight_artifact_digest: str,
        weight_eligibility_receipt_reference: str,
        weight_eligibility_receipt_digest: str,
        analytic_case_count: int,
        constructed_at: datetime,
        correction_sequence: int,
        supersedes_receipt_digest: str | None,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
    ) -> FinalAnalysisWeightAuthorityRecord | None:
        """Return matching released final-weight evidence or ``None``."""
        ...


_PROTOCOL_READ_CAPABILITY = getattr_static(
    FinalAnalysisWeightAuthorityReadPort, "read_final_analysis_weight_authority"
)


def resolve_final_analysis_weight_authority(
    *,
    principal: ValidationPrincipal,
    tenant_record_id: UUID,
    validity_study_id: UUID,
    analysis_weight_receipt_reference: str,
    analysis_weight_receipt_digest: str,
    evidence_version: int,
    estimand_reference: str,
    estimand_digest: str,
    estimand_scope_code: str,
    target_population_reference: str,
    target_population_digest: str,
    analysis_unit_code: str,
    analysis_window_reference: str,
    reference_duration_reference: str,
    reference_duration_digest: str,
    eligible_case_set_digest: str,
    analytic_case_occurrence_set_digest: str,
    source_universe_receipt_reference: str,
    source_universe_receipt_version: int,
    source_universe_receipt_digest: str,
    sampling_design_receipt_reference: str,
    sampling_design_receipt_version: int,
    sampling_design_receipt_digest: str,
    base_weight_method_code: str,
    base_weight_method_version: int,
    base_weight_evidence_digest: str,
    base_weight_artifact_digest: str,
    adjustments: tuple[FinalWeightAdjustmentCoordinate, ...],
    final_weight_artifact_digest: str,
    weight_eligibility_receipt_reference: str,
    weight_eligibility_receipt_digest: str,
    analytic_case_count: int,
    constructed_at: datetime,
    correction_sequence: int,
    supersedes_receipt_digest: str | None,
    owner_contract_reference: str,
    owner_contract_version: int,
    owner_contract_digest: str,
    used_at: datetime,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    read_port: FinalAnalysisWeightAuthorityReadPort,
) -> FinalAnalysisWeightAuthorityView:
    """Authorize then corroborate the complete released final-weight lineage."""
    if type(principal) is not ValidationPrincipal:
        raise TypeError("principal must be an exact ValidationPrincipal.")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be an exact PurposeBoundAccessPolicy.")
    read_capability = getattr_static(
        type(read_port), "read_final_analysis_weight_authority", None
    )
    if (
        type(read_capability) is not FunctionType
        or read_capability is _PROTOCOL_READ_CAPABILITY
    ):
        raise TypeError(
            "read_port must expose a statically callable "
            "read_final_analysis_weight_authority."
        )

    requested = FinalAnalysisWeightAuthorityRecord(
        tenant_record_id=tenant_record_id,
        validity_study_id=validity_study_id,
        analysis_weight_receipt_reference=analysis_weight_receipt_reference,
        analysis_weight_receipt_digest=analysis_weight_receipt_digest,
        evidence_version=evidence_version,
        estimand_reference=estimand_reference,
        estimand_digest=estimand_digest,
        estimand_scope_code=estimand_scope_code,
        target_population_reference=target_population_reference,
        target_population_digest=target_population_digest,
        analysis_unit_code=analysis_unit_code,
        analysis_window_reference=analysis_window_reference,
        reference_duration_reference=reference_duration_reference,
        reference_duration_digest=reference_duration_digest,
        eligible_case_set_digest=eligible_case_set_digest,
        analytic_case_occurrence_set_digest=analytic_case_occurrence_set_digest,
        source_universe_receipt_reference=source_universe_receipt_reference,
        source_universe_receipt_version=source_universe_receipt_version,
        source_universe_receipt_digest=source_universe_receipt_digest,
        sampling_design_receipt_reference=sampling_design_receipt_reference,
        sampling_design_receipt_version=sampling_design_receipt_version,
        sampling_design_receipt_digest=sampling_design_receipt_digest,
        base_weight_method_code=base_weight_method_code,
        base_weight_method_version=base_weight_method_version,
        base_weight_evidence_digest=base_weight_evidence_digest,
        base_weight_artifact_digest=base_weight_artifact_digest,
        adjustments=adjustments,
        final_weight_artifact_digest=final_weight_artifact_digest,
        weight_eligibility_receipt_reference=weight_eligibility_receipt_reference,
        weight_eligibility_receipt_digest=weight_eligibility_receipt_digest,
        analytic_case_count=analytic_case_count,
        constructed_at=constructed_at,
        correction_sequence=correction_sequence,
        supersedes_receipt_digest=supersedes_receipt_digest,
        owner_contract_reference=owner_contract_reference,
        owner_contract_version=owner_contract_version,
        owner_contract_digest=owner_contract_digest,
        owner_contract_released_at=constructed_at,
        released_at=constructed_at,
        superseded_at=None,
    )
    tenant_id = requested.tenant_record_id
    study_id = requested.validity_study_id
    requested_values = dict(requested.fields)
    use_instant = _require_aware_datetime("used_at", used_at)
    purpose = _require_code("purpose_code", purpose_code)
    detached_principal = ValidationPrincipal(
        tenant_record_id=principal.tenant_record_id,
        actor_reference=principal.actor_reference,
        granted_scope_codes=principal.granted_scope_codes,
    )
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
        analysis_weight_receipt_reference=requested_values[
            "analysis_weight_receipt_reference"
        ],
        analysis_weight_receipt_digest=requested_values[
            "analysis_weight_receipt_digest"
        ],
        evidence_version=requested_values["evidence_version"],
        estimand_reference=requested_values["estimand_reference"],
        estimand_digest=requested_values["estimand_digest"],
        estimand_scope_code=requested_values["estimand_scope_code"],
        target_population_reference=requested_values["target_population_reference"],
        target_population_digest=requested_values["target_population_digest"],
        analysis_unit_code=requested_values["analysis_unit_code"],
        analysis_window_reference=requested_values["analysis_window_reference"],
        reference_duration_reference=requested_values["reference_duration_reference"],
        reference_duration_digest=requested_values["reference_duration_digest"],
        eligible_case_set_digest=requested_values["eligible_case_set_digest"],
        analytic_case_occurrence_set_digest=requested_values[
            "analytic_case_occurrence_set_digest"
        ],
        source_universe_receipt_reference=requested_values[
            "source_universe_receipt_reference"
        ],
        source_universe_receipt_version=requested_values[
            "source_universe_receipt_version"
        ],
        source_universe_receipt_digest=requested_values[
            "source_universe_receipt_digest"
        ],
        sampling_design_receipt_reference=requested_values[
            "sampling_design_receipt_reference"
        ],
        sampling_design_receipt_version=requested_values[
            "sampling_design_receipt_version"
        ],
        sampling_design_receipt_digest=requested_values[
            "sampling_design_receipt_digest"
        ],
        base_weight_method_code=requested_values["base_weight_method_code"],
        base_weight_method_version=requested_values["base_weight_method_version"],
        base_weight_evidence_digest=requested_values["base_weight_evidence_digest"],
        base_weight_artifact_digest=requested_values["base_weight_artifact_digest"],
        adjustments=requested_values["adjustments"],
        final_weight_artifact_digest=requested_values["final_weight_artifact_digest"],
        weight_eligibility_receipt_reference=requested_values[
            "weight_eligibility_receipt_reference"
        ],
        weight_eligibility_receipt_digest=requested_values[
            "weight_eligibility_receipt_digest"
        ],
        analytic_case_count=requested_values["analytic_case_count"],
        constructed_at=requested_values["constructed_at"],
        correction_sequence=requested_values["correction_sequence"],
        supersedes_receipt_digest=requested_values["supersedes_receipt_digest"],
        owner_contract_reference=requested_values["owner_contract_reference"],
        owner_contract_version=requested_values["owner_contract_version"],
        owner_contract_digest=requested_values["owner_contract_digest"],
    )
    if persisted is None:
        raise FinalAnalysisWeightAuthorityNotFound(str(study_id))
    if type(persisted) is not FinalAnalysisWeightAuthorityRecord:
        raise FinalAnalysisWeightAuthorityIntegrityError(
            "owner port returned non-canonical final analysis-weight authority evidence"
        )

    try:
        record = FinalAnalysisWeightAuthorityRecord(
            tenant_record_id=persisted.tenant_record_id,
            validity_study_id=persisted.validity_study_id,
            owner_contract_released_at=persisted.owner_contract_released_at,
            released_at=persisted.released_at,
            superseded_at=persisted.superseded_at,
            **dict(persisted.fields),
        )
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise FinalAnalysisWeightAuthorityIntegrityError(
            "owner port returned malformed final analysis-weight authority evidence"
        ) from exc
    if record != persisted:
        raise FinalAnalysisWeightAuthorityIntegrityError(
            "owner port returned non-canonical final analysis-weight authority evidence"
        )
    if (
        _store_operational_uuid("record tenant_record_id", record.tenant_record_id)
        != _store_operational_uuid("requested tenant_record_id", requested.tenant_record_id)
        or _store_operational_uuid("record validity_study_id", record.validity_study_id)
        != _store_operational_uuid("requested validity_study_id", requested.validity_study_id)
        or record.fields != requested.fields
    ):
        raise FinalAnalysisWeightAuthorityIntegrityError(
            "released final analysis-weight authority does not match requested coordinates"
        )
    if use_instant < record.released_at:
        raise FinalAnalysisWeightAuthorityIntegrityError(
            "final analysis-weight authority cannot be used before its release instant"
        )
    if record.superseded_at is not None and use_instant >= record.superseded_at:
        raise FinalAnalysisWeightAuthorityIntegrityError(
            "final analysis-weight authority cannot be used at or after supersession"
        )

    values = dict(record.fields)
    values["owner_contract_released_at"] = record.owner_contract_released_at
    values["released_at"] = record.released_at
    values["superseded_at"] = record.superseded_at
    fields = tuple((field_name, values[field_name]) for field_name in sorted(_READ_FIELDS))
    view = object.__new__(FinalAnalysisWeightAuthorityView)
    object.__setattr__(
        view,
        "_tenant_identity",
        _store_operational_uuid("tenant_record_id", record.tenant_record_id),
    )
    object.__setattr__(
        view,
        "_study_identity",
        _store_operational_uuid("validity_study_id", record.validity_study_id),
    )
    object.__setattr__(view, "_fields", fields)
    object.__setattr__(
        view,
        "_issuance_marker",
        _FINAL_ANALYSIS_WEIGHT_VIEW_ISSUANCE_MARKER,
    )
    return view
