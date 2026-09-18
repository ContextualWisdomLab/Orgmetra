"""Immutable provenance for final point-estimation weight construction.

This module records only versioned scientific lineage and digests. It never
stores row-level weight values or copies auxiliary calibration attributes into
Orgmetra's validity-analysis boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json

from .handoff import (
    _canonical_timestamp,
    _freeze_timestamp,
    _validate_code,
    _validate_digest,
    _validate_operational_uuid,
    _validate_reference,
)

_CALIBRATION_TERMINATION_CODES = frozenset({"converged", "fallback_applied"})
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


def _positive_integer(value: object, field_name: str) -> None:
    """Require a strict positive integer without accepting booleans."""
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")


@dataclass(frozen=True, slots=True, repr=False)
class NonresponseAdjustmentReceipt:
    """Bind one nonresponse adjustment to explicit disposition-aware evidence."""

    tenant_record_id: str
    receipt_reference: str
    response_disposition_receipt_reference: str
    response_disposition_receipt_version: int
    response_disposition_receipt_digest: str
    adjustment_population_digest: str
    method_reference: str
    method_version: int
    configuration_digest: str
    ineligible_treatment_code: str
    unknown_treatment_code: str
    unavailable_treatment_code: str
    input_weight_artifact_digest: str
    output_weight_artifact_digest: str
    constructed_at: datetime
    evidence_version: int = 1

    def __post_init__(self) -> None:
        """Reject undocumented filters or mutable nonresponse evidence."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.receipt_reference,
            "nonresponse_adjustment_receipt",
            "receipt_reference",
        )
        _validate_reference(
            self.response_disposition_receipt_reference,
            "response_disposition_receipt",
            "response_disposition_receipt_reference",
        )
        _positive_integer(
            self.response_disposition_receipt_version,
            "response_disposition_receipt_version",
        )
        for field_name in (
            "response_disposition_receipt_digest",
            "adjustment_population_digest",
            "configuration_digest",
            "input_weight_artifact_digest",
            "output_weight_artifact_digest",
        ):
            _validate_digest(getattr(self, field_name), field_name)
        _validate_reference(self.method_reference, "weight_method", "method_reference")
        _positive_integer(self.method_version, "method_version")
        for field_name in (
            "ineligible_treatment_code",
            "unknown_treatment_code",
            "unavailable_treatment_code",
        ):
            _validate_code(getattr(self, field_name), field_name)
        if self.input_weight_artifact_digest == self.output_weight_artifact_digest:
            raise ValueError(
                "output_weight_artifact_digest must identify the adjusted weight artifact"
            )
        constructed_at = _freeze_timestamp(self.constructed_at, "constructed_at")
        if type(self.evidence_version) is not int or self.evidence_version != 1:
            raise ValueError("evidence_version must remain 1")
        object.__setattr__(self, "constructed_at", constructed_at)

    def __repr__(self) -> str:
        """Return a value-minimized representation for routine logs."""
        return "NonresponseAdjustmentReceipt(<redacted>)"

    def canonical_json(self) -> str:
        """Return deterministic disposition-aware provenance without source attributes."""
        payload = {
            "adjustment_population_digest": self.adjustment_population_digest,
            "configuration_digest": self.configuration_digest,
            "constructed_at": _canonical_timestamp(self.constructed_at, "constructed_at"),
            "evidence_version": self.evidence_version,
            "ineligible_treatment_code": self.ineligible_treatment_code,
            "input_weight_artifact_digest": self.input_weight_artifact_digest,
            "method_reference": self.method_reference,
            "method_version": self.method_version,
            "output_weight_artifact_digest": self.output_weight_artifact_digest,
            "receipt_reference": self.receipt_reference,
            "response_disposition_receipt_digest": self.response_disposition_receipt_digest,
            "response_disposition_receipt_reference": self.response_disposition_receipt_reference,
            "response_disposition_receipt_version": self.response_disposition_receipt_version,
            "tenant_record_id": self.tenant_record_id,
            "unavailable_treatment_code": self.unavailable_treatment_code,
            "unknown_treatment_code": self.unknown_treatment_code,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical receipt bytes."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True, repr=False)
class CalibrationAdjustmentReceipt:
    """Bind calibration to owner authority, benchmark authority, and termination evidence."""

    tenant_record_id: str
    receipt_reference: str
    target_population_digest: str
    analysis_window_reference: str
    auxiliary_authority_reference: str
    auxiliary_projection_reference: str
    auxiliary_projection_version: int
    auxiliary_projection_digest: str
    auxiliary_purpose_reference: str
    auxiliary_purpose_digest: str
    auxiliary_owner_contract_reference: str
    auxiliary_owner_contract_version: int
    auxiliary_owner_contract_digest: str
    auxiliary_authorization_receipt_reference: str
    auxiliary_authorization_receipt_digest: str
    auxiliary_scientific_use_receipt_reference: str
    auxiliary_scientific_use_receipt_digest: str
    auxiliary_scientific_use_at: datetime
    benchmark_receipt_reference: str
    benchmark_receipt_version: int
    benchmark_receipt_digest: str
    benchmark_owner_contract_reference: str
    benchmark_owner_contract_version: int
    benchmark_owner_contract_digest: str
    benchmark_reference_at: datetime
    algorithm_reference: str
    algorithm_version: int
    constraints_digest: str
    applied_constraints_digest: str
    termination_code: str
    input_weight_artifact_digest: str
    output_weight_artifact_digest: str
    constructed_at: datetime
    fallback_reason_code: str | None = None
    fallback_rule_reference: str | None = None
    fallback_rule_digest: str | None = None
    fallback_algorithm_reference: str | None = None
    fallback_algorithm_version: int | None = None
    fallback_configuration_digest: str | None = None
    evidence_version: int = 1

    def __post_init__(self) -> None:
        """Fail closed on floating authority, benchmark time, hidden fallback, or nonconvergence."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.receipt_reference,
            "calibration_adjustment_receipt",
            "receipt_reference",
        )
        _validate_reference(
            self.analysis_window_reference,
            "analysis_window",
            "analysis_window_reference",
        )
        _validate_reference(
            self.auxiliary_authority_reference,
            "scientific_auxiliary_authority",
            "auxiliary_authority_reference",
        )
        _validate_reference(
            self.auxiliary_projection_reference,
            "calibration_auxiliary_projection",
            "auxiliary_projection_reference",
        )
        _positive_integer(
            self.auxiliary_projection_version,
            "auxiliary_projection_version",
        )
        _validate_reference(
            self.auxiliary_purpose_reference,
            "scientific_data_use_purpose",
            "auxiliary_purpose_reference",
        )
        _validate_reference(
            self.auxiliary_owner_contract_reference,
            "released_owner_contract",
            "auxiliary_owner_contract_reference",
        )
        _positive_integer(
            self.auxiliary_owner_contract_version,
            "auxiliary_owner_contract_version",
        )
        _validate_reference(
            self.auxiliary_authorization_receipt_reference,
            "scientific_data_authorization",
            "auxiliary_authorization_receipt_reference",
        )
        _validate_reference(
            self.auxiliary_scientific_use_receipt_reference,
            "scientific_use_receipt",
            "auxiliary_scientific_use_receipt_reference",
        )
        _validate_reference(
            self.benchmark_receipt_reference,
            "calibration_benchmark_receipt",
            "benchmark_receipt_reference",
        )
        _positive_integer(self.benchmark_receipt_version, "benchmark_receipt_version")
        _validate_reference(
            self.benchmark_owner_contract_reference,
            "released_owner_contract",
            "benchmark_owner_contract_reference",
        )
        _positive_integer(
            self.benchmark_owner_contract_version,
            "benchmark_owner_contract_version",
        )
        _validate_reference(
            self.algorithm_reference,
            "calibration_algorithm",
            "algorithm_reference",
        )
        for field_name in (
            "target_population_digest",
            "auxiliary_projection_digest",
            "auxiliary_purpose_digest",
            "auxiliary_owner_contract_digest",
            "auxiliary_authorization_receipt_digest",
            "auxiliary_scientific_use_receipt_digest",
            "benchmark_receipt_digest",
            "benchmark_owner_contract_digest",
            "constraints_digest",
            "applied_constraints_digest",
            "input_weight_artifact_digest",
            "output_weight_artifact_digest",
        ):
            _validate_digest(getattr(self, field_name), field_name)
        _positive_integer(self.algorithm_version, "algorithm_version")
        if (
            type(self.termination_code) is not str
            or self.termination_code not in _CALIBRATION_TERMINATION_CODES
        ):
            raise ValueError("termination_code must be converged or fallback_applied")
        fallback_fields = (
            self.fallback_reason_code,
            self.fallback_rule_reference,
            self.fallback_rule_digest,
            self.fallback_algorithm_reference,
            self.fallback_algorithm_version,
            self.fallback_configuration_digest,
        )
        if self.termination_code == "fallback_applied":
            if any(value is None for value in fallback_fields):
                raise ValueError(
                    "fallback reason, rule, algorithm, version, and configuration evidence "
                    "are required for fallback_applied"
                )
            _validate_code(self.fallback_reason_code, "fallback_reason_code")
            _validate_reference(
                self.fallback_rule_reference,
                "calibration_fallback_rule",
                "fallback_rule_reference",
            )
            _validate_digest(self.fallback_rule_digest, "fallback_rule_digest")
            _validate_reference(
                self.fallback_algorithm_reference,
                "calibration_algorithm",
                "fallback_algorithm_reference",
            )
            _positive_integer(
                self.fallback_algorithm_version,
                "fallback_algorithm_version",
            )
            _validate_digest(
                self.fallback_configuration_digest,
                "fallback_configuration_digest",
            )
        else:
            if self.applied_constraints_digest != self.constraints_digest:
                raise ValueError(
                    "changed applied calibration constraints require explicit fallback provenance"
                )
            if any(value is not None for value in fallback_fields):
                raise ValueError("fallback evidence must be absent when calibration converged")
        if self.input_weight_artifact_digest == self.output_weight_artifact_digest:
            raise ValueError(
                "output_weight_artifact_digest must identify the calibrated weight artifact"
            )
        scientific_use_at = _freeze_timestamp(
            self.auxiliary_scientific_use_at,
            "auxiliary_scientific_use_at",
        )
        benchmark_reference_at = _freeze_timestamp(
            self.benchmark_reference_at,
            "benchmark_reference_at",
        )
        constructed_at = _freeze_timestamp(self.constructed_at, "constructed_at")
        if scientific_use_at > constructed_at:
            raise ValueError("auxiliary_scientific_use_at cannot be later than constructed_at")
        if benchmark_reference_at > constructed_at:
            raise ValueError("benchmark_reference_at cannot be later than constructed_at")
        if type(self.evidence_version) is not int or self.evidence_version != 1:
            raise ValueError("evidence_version must remain 1")
        object.__setattr__(self, "auxiliary_scientific_use_at", scientific_use_at)
        object.__setattr__(self, "benchmark_reference_at", benchmark_reference_at)
        object.__setattr__(self, "constructed_at", constructed_at)

    def __repr__(self) -> str:
        """Return a value-minimized representation for routine logs."""
        return "CalibrationAdjustmentReceipt(<redacted>)"

    def canonical_json(self) -> str:
        """Return deterministic purpose-bound provenance without auxiliary values."""
        payload: dict[str, object] = {
            "algorithm_reference": self.algorithm_reference,
            "algorithm_version": self.algorithm_version,
            "analysis_window_reference": self.analysis_window_reference,
            "applied_constraints_digest": self.applied_constraints_digest,
            "auxiliary_authority_reference": self.auxiliary_authority_reference,
            "auxiliary_authorization_receipt_digest": self.auxiliary_authorization_receipt_digest,
            "auxiliary_authorization_receipt_reference": self.auxiliary_authorization_receipt_reference,
            "auxiliary_owner_contract_digest": self.auxiliary_owner_contract_digest,
            "auxiliary_owner_contract_reference": self.auxiliary_owner_contract_reference,
            "auxiliary_owner_contract_version": self.auxiliary_owner_contract_version,
            "auxiliary_projection_digest": self.auxiliary_projection_digest,
            "auxiliary_projection_reference": self.auxiliary_projection_reference,
            "auxiliary_projection_version": self.auxiliary_projection_version,
            "auxiliary_purpose_digest": self.auxiliary_purpose_digest,
            "auxiliary_purpose_reference": self.auxiliary_purpose_reference,
            "auxiliary_scientific_use_at": _canonical_timestamp(
                self.auxiliary_scientific_use_at,
                "auxiliary_scientific_use_at",
            ),
            "auxiliary_scientific_use_receipt_digest": self.auxiliary_scientific_use_receipt_digest,
            "auxiliary_scientific_use_receipt_reference": self.auxiliary_scientific_use_receipt_reference,
            "benchmark_owner_contract_digest": self.benchmark_owner_contract_digest,
            "benchmark_owner_contract_reference": self.benchmark_owner_contract_reference,
            "benchmark_owner_contract_version": self.benchmark_owner_contract_version,
            "benchmark_receipt_digest": self.benchmark_receipt_digest,
            "benchmark_receipt_reference": self.benchmark_receipt_reference,
            "benchmark_receipt_version": self.benchmark_receipt_version,
            "benchmark_reference_at": _canonical_timestamp(
                self.benchmark_reference_at,
                "benchmark_reference_at",
            ),
            "constraints_digest": self.constraints_digest,
            "constructed_at": _canonical_timestamp(self.constructed_at, "constructed_at"),
            "evidence_version": self.evidence_version,
            "input_weight_artifact_digest": self.input_weight_artifact_digest,
            "output_weight_artifact_digest": self.output_weight_artifact_digest,
            "receipt_reference": self.receipt_reference,
            "target_population_digest": self.target_population_digest,
            "tenant_record_id": self.tenant_record_id,
            "termination_code": self.termination_code,
        }
        if self.fallback_rule_reference is not None:
            payload["fallback_algorithm_reference"] = self.fallback_algorithm_reference
            payload["fallback_algorithm_version"] = self.fallback_algorithm_version
            payload["fallback_configuration_digest"] = self.fallback_configuration_digest
            payload["fallback_reason_code"] = self.fallback_reason_code
            payload["fallback_rule_digest"] = self.fallback_rule_digest
            payload["fallback_rule_reference"] = self.fallback_rule_reference
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical receipt bytes."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True, repr=False)
class TrimmingBoundingAdjustmentReceipt:
    """Bind trimming or bounding to an immutable rule and affected-case evidence."""

    tenant_record_id: str
    receipt_reference: str
    rule_reference: str
    rule_version: int
    rule_configuration_digest: str
    affected_case_occurrence_set_digest: str
    affected_case_count: int
    input_weight_artifact_digest: str
    output_weight_artifact_digest: str
    constructed_at: datetime
    evidence_version: int = 1

    def __post_init__(self) -> None:
        """Reject hidden thresholds, unknown affected cases, or no-op transforms."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.receipt_reference,
            "trimming_bounding_adjustment_receipt",
            "receipt_reference",
        )
        _validate_reference(self.rule_reference, "weight_trimming_rule", "rule_reference")
        _positive_integer(self.rule_version, "rule_version")
        _validate_digest(self.rule_configuration_digest, "rule_configuration_digest")
        _validate_digest(
            self.affected_case_occurrence_set_digest,
            "affected_case_occurrence_set_digest",
        )
        _positive_integer(self.affected_case_count, "affected_case_count")
        _validate_digest(self.input_weight_artifact_digest, "input_weight_artifact_digest")
        _validate_digest(self.output_weight_artifact_digest, "output_weight_artifact_digest")
        if self.input_weight_artifact_digest == self.output_weight_artifact_digest:
            raise ValueError(
                "output_weight_artifact_digest must identify the trimmed or bounded weight artifact"
            )
        constructed_at = _freeze_timestamp(self.constructed_at, "constructed_at")
        if type(self.evidence_version) is not int or self.evidence_version != 1:
            raise ValueError("evidence_version must remain 1")
        object.__setattr__(self, "constructed_at", constructed_at)

    def __repr__(self) -> str:
        """Return a value-minimized representation for routine logs."""
        return "TrimmingBoundingAdjustmentReceipt(<redacted>)"

    def canonical_json(self) -> str:
        """Return deterministic rule provenance without case-level weight values."""
        payload = {
            "affected_case_count": self.affected_case_count,
            "affected_case_occurrence_set_digest": self.affected_case_occurrence_set_digest,
            "constructed_at": _canonical_timestamp(self.constructed_at, "constructed_at"),
            "evidence_version": self.evidence_version,
            "input_weight_artifact_digest": self.input_weight_artifact_digest,
            "output_weight_artifact_digest": self.output_weight_artifact_digest,
            "receipt_reference": self.receipt_reference,
            "rule_configuration_digest": self.rule_configuration_digest,
            "rule_reference": self.rule_reference,
            "rule_version": self.rule_version,
            "tenant_record_id": self.tenant_record_id,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical receipt bytes."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True, repr=False)
class WeightEligibilityReceipt:
    """Bind one final weight artifact to its valid population and reference duration."""

    tenant_record_id: str
    receipt_reference: str
    weight_scope_code: str
    target_population_reference: str
    target_population_digest: str
    reference_duration_reference: str
    reference_duration_digest: str
    eligible_case_set_digest: str
    weight_artifact_digest: str
    constructed_at: datetime
    evidence_version: int = 1

    def __post_init__(self) -> None:
        """Reject ambiguous cross-sectional or longitudinal weight eligibility."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.receipt_reference,
            "weight_eligibility_receipt",
            "receipt_reference",
        )
        if (
            type(self.weight_scope_code) is not str
            or self.weight_scope_code not in _WEIGHT_SCOPE_CODES
        ):
            raise ValueError("weight_scope_code must be cross_sectional or longitudinal")
        _validate_reference(
            self.target_population_reference,
            "analysis_target_population",
            "target_population_reference",
        )
        _validate_digest(self.target_population_digest, "target_population_digest")
        _validate_reference(
            self.reference_duration_reference,
            "analysis_reference_duration",
            "reference_duration_reference",
        )
        for field_name in (
            "reference_duration_digest",
            "eligible_case_set_digest",
            "weight_artifact_digest",
        ):
            _validate_digest(getattr(self, field_name), field_name)
        constructed_at = _freeze_timestamp(self.constructed_at, "constructed_at")
        if type(self.evidence_version) is not int or self.evidence_version != 1:
            raise ValueError("evidence_version must remain 1")
        object.__setattr__(self, "constructed_at", constructed_at)

    def __repr__(self) -> str:
        """Return a value-minimized representation suitable for routine logs."""
        return "WeightEligibilityReceipt(<redacted>)"

    def canonical_json(self) -> str:
        """Return deterministic eligibility provenance without row-level weight values."""
        payload = {
            "constructed_at": _canonical_timestamp(self.constructed_at, "constructed_at"),
            "eligible_case_set_digest": self.eligible_case_set_digest,
            "evidence_version": self.evidence_version,
            "receipt_reference": self.receipt_reference,
            "reference_duration_digest": self.reference_duration_digest,
            "reference_duration_reference": self.reference_duration_reference,
            "target_population_digest": self.target_population_digest,
            "target_population_reference": self.target_population_reference,
            "tenant_record_id": self.tenant_record_id,
            "weight_artifact_digest": self.weight_artifact_digest,
            "weight_scope_code": self.weight_scope_code,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical receipt bytes."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class AnalysisWeightAdjustment:
    """Describe one ordered, digest-linked transformation of analysis weights."""

    sequence_number: int
    adjustment_code: str
    method_reference: str
    method_version: int
    input_weight_artifact_digest: str
    output_weight_artifact_digest: str
    configuration_digest: str
    evidence_receipt_digest: str
    evidence_kind: str

    def __post_init__(self) -> None:
        """Reject unordered, opaque, or unverifiable adjustment evidence."""
        _positive_integer(self.sequence_number, "sequence_number")
        _validate_code(self.adjustment_code, "adjustment_code")
        _validate_reference(self.method_reference, "weight_method", "method_reference")
        _positive_integer(self.method_version, "method_version")
        for field_name in (
            "input_weight_artifact_digest",
            "output_weight_artifact_digest",
            "configuration_digest",
            "evidence_receipt_digest",
        ):
            _validate_digest(getattr(self, field_name), field_name)
        _validate_code(self.evidence_kind, "evidence_kind")
        required_evidence_kind = _SPECIALIZED_EVIDENCE_KIND_BY_ADJUSTMENT_CODE.get(
            self.adjustment_code
        )
        if required_evidence_kind is not None and self.evidence_kind != required_evidence_kind:
            raise ValueError(
                f"{self.adjustment_code} requires evidence_kind {required_evidence_kind}"
            )
        if self.input_weight_artifact_digest == self.output_weight_artifact_digest:
            raise ValueError(
                "output_weight_artifact_digest must identify the transformed weight artifact"
            )

    def to_dict(self) -> dict[str, object]:
        """Return canonical adjustment fields without row-level weight values."""
        return {
            "adjustment_code": self.adjustment_code,
            "configuration_digest": self.configuration_digest,
            "evidence_kind": self.evidence_kind,
            "evidence_receipt_digest": self.evidence_receipt_digest,
            "input_weight_artifact_digest": self.input_weight_artifact_digest,
            "method_reference": self.method_reference,
            "method_version": self.method_version,
            "output_weight_artifact_digest": self.output_weight_artifact_digest,
            "sequence_number": self.sequence_number,
        }


@dataclass(frozen=True, slots=True, repr=False)
class FinalAnalysisWeightReceipt:
    """Bind one estimand to the exact final point-estimation weight lineage used."""

    tenant_record_id: str
    receipt_reference: str
    estimand_reference: str
    estimand_digest: str
    estimand_scope_code: str
    target_population_reference: str
    target_population_digest: str
    analysis_unit_code: str
    analysis_window_reference: str
    reference_duration_reference: str
    reference_duration_digest: str
    eligible_case_set_digest: str
    analytic_case_occurrence_set_digest: str
    source_universe_receipt_digest: str
    sampling_design_receipt_digest: str
    base_weight_method_code: str
    base_weight_method_version: int
    base_weight_evidence_digest: str
    base_weight_artifact_digest: str
    adjustments: tuple[AnalysisWeightAdjustment, ...]
    final_weight_artifact_digest: str
    weight_eligibility: WeightEligibilityReceipt
    analytic_case_count: int
    constructed_at: datetime
    correction_sequence: int = 1
    supersedes_receipt_digest: str | None = None
    evidence_version: int = 1

    def __post_init__(self) -> None:
        """Fail closed unless the complete point-weight construction is reproducible."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.receipt_reference, "analysis_weight_receipt", "receipt_reference"
        )
        _validate_reference(self.estimand_reference, "validation_estimand", "estimand_reference")
        _validate_digest(self.estimand_digest, "estimand_digest")
        if (
            type(self.estimand_scope_code) is not str
            or self.estimand_scope_code not in _WEIGHT_SCOPE_CODES
        ):
            raise ValueError("estimand_scope_code must be cross_sectional or longitudinal")
        _validate_reference(
            self.target_population_reference,
            "analysis_target_population",
            "target_population_reference",
        )
        _validate_digest(self.target_population_digest, "target_population_digest")
        _validate_code(self.analysis_unit_code, "analysis_unit_code")
        _validate_reference(
            self.analysis_window_reference, "analysis_window", "analysis_window_reference"
        )
        _validate_reference(
            self.reference_duration_reference,
            "analysis_reference_duration",
            "reference_duration_reference",
        )
        _validate_digest(self.reference_duration_digest, "reference_duration_digest")
        for field_name in (
            "eligible_case_set_digest",
            "analytic_case_occurrence_set_digest",
            "source_universe_receipt_digest",
            "sampling_design_receipt_digest",
            "base_weight_evidence_digest",
            "base_weight_artifact_digest",
            "final_weight_artifact_digest",
        ):
            _validate_digest(getattr(self, field_name), field_name)
        _validate_code(self.base_weight_method_code, "base_weight_method_code")
        _positive_integer(self.base_weight_method_version, "base_weight_method_version")
        _positive_integer(self.analytic_case_count, "analytic_case_count")
        constructed_at = _freeze_timestamp(self.constructed_at, "constructed_at")
        if type(self.weight_eligibility) is not WeightEligibilityReceipt:
            raise ValueError("weight_eligibility must be a WeightEligibilityReceipt")
        if self.weight_eligibility.tenant_record_id != self.tenant_record_id:
            raise ValueError("weight_eligibility tenant_record_id must match the analysis receipt")
        if self.weight_eligibility.weight_scope_code != self.estimand_scope_code:
            raise ValueError("weight scope must match estimand_scope_code")
        if (
            self.weight_eligibility.target_population_reference
            != self.target_population_reference
            or self.weight_eligibility.target_population_digest != self.target_population_digest
        ):
            raise ValueError("weight target population must match the estimand target population")
        if (
            self.weight_eligibility.reference_duration_reference
            != self.reference_duration_reference
            or self.weight_eligibility.reference_duration_digest != self.reference_duration_digest
        ):
            raise ValueError("weight reference duration must match the estimand reference duration")
        if self.weight_eligibility.eligible_case_set_digest != self.eligible_case_set_digest:
            raise ValueError("weight eligible case set must match the analysis eligible case set")
        if type(self.adjustments) is not tuple:
            raise ValueError("adjustments must be an immutable tuple")

        expected_input = self.base_weight_artifact_digest
        for expected_sequence, adjustment in enumerate(self.adjustments, start=1):
            if type(adjustment) is not AnalysisWeightAdjustment:
                raise ValueError("adjustments must contain AnalysisWeightAdjustment values")
            if adjustment.sequence_number != expected_sequence:
                raise ValueError("adjustments must have contiguous sequence_number values")
            if adjustment.input_weight_artifact_digest != expected_input:
                raise ValueError("adjustment input_weight_artifact_digest breaks the weight chain")
            expected_input = adjustment.output_weight_artifact_digest
        if expected_input != self.final_weight_artifact_digest:
            raise ValueError(
                "final_weight_artifact_digest must equal the ordered adjustment chain output"
            )
        if self.weight_eligibility.weight_artifact_digest != self.final_weight_artifact_digest:
            raise ValueError(
                "weight eligibility must identify the final point-estimation weight artifact"
            )

        _positive_integer(self.correction_sequence, "correction_sequence")
        if self.correction_sequence == 1:
            if self.supersedes_receipt_digest is not None:
                raise ValueError(
                    "supersedes_receipt_digest must be absent for correction_sequence 1"
                )
        else:
            if self.supersedes_receipt_digest is None:
                raise ValueError(
                    "supersedes_receipt_digest is required when correction_sequence exceeds 1"
                )
            _validate_digest(self.supersedes_receipt_digest, "supersedes_receipt_digest")
        if type(self.evidence_version) is not int or self.evidence_version != 1:
            raise ValueError("evidence_version must remain 1")
        object.__setattr__(self, "constructed_at", constructed_at)

    def __repr__(self) -> str:
        """Return a value-minimized representation suitable for routine logs."""
        return "FinalAnalysisWeightReceipt(<redacted>)"

    def canonical_json(self) -> str:
        """Return deterministic provenance JSON without case-level weight values."""
        payload: dict[str, object] = {
            "adjustments": [adjustment.to_dict() for adjustment in self.adjustments],
            "analysis_unit_code": self.analysis_unit_code,
            "analysis_window_reference": self.analysis_window_reference,
            "analytic_case_count": self.analytic_case_count,
            "analytic_case_occurrence_set_digest": self.analytic_case_occurrence_set_digest,
            "base_weight_artifact_digest": self.base_weight_artifact_digest,
            "base_weight_evidence_digest": self.base_weight_evidence_digest,
            "base_weight_method_code": self.base_weight_method_code,
            "base_weight_method_version": self.base_weight_method_version,
            "constructed_at": _canonical_timestamp(self.constructed_at, "constructed_at"),
            "correction_sequence": self.correction_sequence,
            "eligible_case_set_digest": self.eligible_case_set_digest,
            "estimand_digest": self.estimand_digest,
            "estimand_reference": self.estimand_reference,
            "estimand_scope_code": self.estimand_scope_code,
            "evidence_version": self.evidence_version,
            "final_weight_artifact_digest": self.final_weight_artifact_digest,
            "receipt_reference": self.receipt_reference,
            "reference_duration_digest": self.reference_duration_digest,
            "reference_duration_reference": self.reference_duration_reference,
            "sampling_design_receipt_digest": self.sampling_design_receipt_digest,
            "source_universe_receipt_digest": self.source_universe_receipt_digest,
            "target_population_digest": self.target_population_digest,
            "target_population_reference": self.target_population_reference,
            "tenant_record_id": self.tenant_record_id,
            "weight_eligibility_receipt_digest": self.weight_eligibility.sha256_digest(),
        }
        if self.supersedes_receipt_digest is not None:
            payload["supersedes_receipt_digest"] = self.supersedes_receipt_digest
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical receipt bytes."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


__all__ = [
    "AnalysisWeightAdjustment",
    "CalibrationAdjustmentReceipt",
    "FinalAnalysisWeightReceipt",
    "NonresponseAdjustmentReceipt",
    "TrimmingBoundingAdjustmentReceipt",
    "WeightEligibilityReceipt",
]
