"""Correlate final point-weight evidence with the variance design that used it.

This boundary prevents a weighted scientific result from combining a final point
weight with variance or replicate evidence generated from a different analytic
case set, eligibility receipt, correction sequence, or final-weight artifact.
It records only immutable references and digests; durable owner corroboration
remains an application/persistence responsibility.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json

from .handoff import (
    _canonical_timestamp,
    _freeze_timestamp,
    _validate_digest,
    _validate_operational_uuid,
    _validate_reference,
)
from .weights import FinalAnalysisWeightReceipt


def _positive_integer(value: object, field_name: str) -> None:
    """Require an exact positive integer without accepting booleans."""
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")


@dataclass(frozen=True, slots=True, repr=False)
class WeightVarianceCompatibilityReceipt:
    """Bind variance evidence to the exact final point-weight lineage it accompanies."""

    tenant_record_id: str
    receipt_reference: str
    analysis_weight_receipt: FinalAnalysisWeightReceipt
    variance_design_receipt_reference: str
    variance_design_receipt_version: int
    variance_design_receipt_digest: str
    variance_analysis_weight_receipt_digest: str
    variance_analytic_case_occurrence_set_digest: str
    variance_weight_eligibility_receipt_digest: str
    variance_weight_correction_sequence: int
    variance_final_weight_artifact_digest: str
    constructed_at: datetime
    evidence_version: int = 1

    def __post_init__(self) -> None:
        """Reject variance evidence produced from any different point-weight basis."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.receipt_reference,
            "weight_variance_compatibility_receipt",
            "receipt_reference",
        )
        if type(self.analysis_weight_receipt) is not FinalAnalysisWeightReceipt:
            raise ValueError(
                "analysis_weight_receipt must be a FinalAnalysisWeightReceipt"
            )
        if self.analysis_weight_receipt.tenant_record_id != self.tenant_record_id:
            raise ValueError(
                "analysis_weight_receipt tenant_record_id must match the compatibility receipt"
            )
        _validate_reference(
            self.variance_design_receipt_reference,
            "variance_design_receipt",
            "variance_design_receipt_reference",
        )
        _positive_integer(
            self.variance_design_receipt_version,
            "variance_design_receipt_version",
        )
        for field_name in (
            "variance_design_receipt_digest",
            "variance_analysis_weight_receipt_digest",
            "variance_analytic_case_occurrence_set_digest",
            "variance_weight_eligibility_receipt_digest",
            "variance_final_weight_artifact_digest",
        ):
            _validate_digest(getattr(self, field_name), field_name)
        _positive_integer(
            self.variance_weight_correction_sequence,
            "variance_weight_correction_sequence",
        )

        analysis_weight_digest = self.analysis_weight_receipt.sha256_digest()
        if self.variance_design_receipt_digest == analysis_weight_digest:
            raise ValueError(
                "variance_design_receipt_digest must identify evidence distinct from the analysis weight receipt"
            )
        if self.variance_analysis_weight_receipt_digest != analysis_weight_digest:
            raise ValueError(
                "variance evidence analysis weight receipt must match the exact point-weight receipt"
            )
        if (
            self.variance_analytic_case_occurrence_set_digest
            != self.analysis_weight_receipt.analytic_case_occurrence_set_digest
        ):
            raise ValueError(
                "variance evidence analytic case occurrence set must match the point-weight receipt"
            )
        if (
            self.variance_weight_eligibility_receipt_digest
            != self.analysis_weight_receipt.weight_eligibility.sha256_digest()
        ):
            raise ValueError(
                "variance evidence weight eligibility must match the point-weight receipt"
            )
        if (
            self.variance_weight_correction_sequence
            != self.analysis_weight_receipt.correction_sequence
        ):
            raise ValueError(
                "variance evidence correction sequence must match the point-weight receipt"
            )
        if (
            self.variance_final_weight_artifact_digest
            != self.analysis_weight_receipt.final_weight_artifact_digest
        ):
            raise ValueError(
                "variance evidence final weight artifact must match the point-weight receipt"
            )

        constructed_at = _freeze_timestamp(self.constructed_at, "constructed_at")
        if constructed_at < self.analysis_weight_receipt.constructed_at:
            raise ValueError(
                "constructed_at cannot precede the analysis weight receipt"
            )
        if type(self.evidence_version) is not int or self.evidence_version != 1:
            raise ValueError("evidence_version must remain 1")
        object.__setattr__(self, "constructed_at", constructed_at)

    def __repr__(self) -> str:
        """Return a value-minimized representation suitable for routine logs."""
        return "WeightVarianceCompatibilityReceipt(<redacted>)"

    def canonical_json(self) -> str:
        """Return deterministic correlation evidence without weight values."""
        payload = {
            "analysis_weight_receipt_digest": self.analysis_weight_receipt.sha256_digest(),
            "constructed_at": _canonical_timestamp(self.constructed_at, "constructed_at"),
            "evidence_version": self.evidence_version,
            "receipt_reference": self.receipt_reference,
            "tenant_record_id": self.tenant_record_id,
            "variance_analysis_weight_receipt_digest": (
                self.variance_analysis_weight_receipt_digest
            ),
            "variance_analytic_case_occurrence_set_digest": (
                self.variance_analytic_case_occurrence_set_digest
            ),
            "variance_design_receipt_digest": self.variance_design_receipt_digest,
            "variance_design_receipt_reference": self.variance_design_receipt_reference,
            "variance_design_receipt_version": self.variance_design_receipt_version,
            "variance_final_weight_artifact_digest": (
                self.variance_final_weight_artifact_digest
            ),
            "variance_weight_correction_sequence": (
                self.variance_weight_correction_sequence
            ),
            "variance_weight_eligibility_receipt_digest": (
                self.variance_weight_eligibility_receipt_digest
            ),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical compatibility receipt bytes."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


__all__ = ["WeightVarianceCompatibilityReceipt"]
