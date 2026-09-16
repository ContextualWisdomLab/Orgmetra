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


def _positive_integer(value: object, field_name: str) -> None:
    """Require a strict positive integer without accepting booleans."""
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")


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
        if self.input_weight_artifact_digest == self.output_weight_artifact_digest:
            raise ValueError(
                "output_weight_artifact_digest must identify the transformed weight artifact"
            )

    def to_dict(self) -> dict[str, object]:
        """Return canonical adjustment fields without row-level weight values."""
        return {
            "adjustment_code": self.adjustment_code,
            "configuration_digest": self.configuration_digest,
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
    target_population_reference: str
    target_population_digest: str
    analysis_unit_code: str
    analysis_window_reference: str
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
            "evidence_version": self.evidence_version,
            "final_weight_artifact_digest": self.final_weight_artifact_digest,
            "receipt_reference": self.receipt_reference,
            "sampling_design_receipt_digest": self.sampling_design_receipt_digest,
            "source_universe_receipt_digest": self.source_universe_receipt_digest,
            "target_population_digest": self.target_population_digest,
            "target_population_reference": self.target_population_reference,
            "tenant_record_id": self.tenant_record_id,
        }
        if self.supersedes_receipt_digest is not None:
            payload["supersedes_receipt_digest"] = self.supersedes_receipt_digest
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical receipt bytes."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


__all__ = ["AnalysisWeightAdjustment", "FinalAnalysisWeightReceipt"]
