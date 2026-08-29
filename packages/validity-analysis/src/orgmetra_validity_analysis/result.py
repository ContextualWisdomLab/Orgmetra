"""Validate one immutable numerical result returned by the approved worker.

Orgmetra does not fit a model in this package. It accepts only a bounded,
digest-linked result envelope from the pinned ``fast-mlsirm`` worker so that
nonconverged or malformed output cannot be presented as an employment
decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from math import isfinite
from numbers import Real

from .handoff import (
    _canonical_timestamp,
    _validate_code,
    _validate_digest,
    _validate_kernel_revision,
    _validate_operational_uuid,
    _validate_reference,
)

_RESULT_AUTHORITY = "scientific_evidence_only"
_EXECUTION_STATE = "completed"
_ALLOWED_BACKENDS = frozenset({"rust_cpu", "rust_gpu"})
_ALLOWED_PRECISIONS = frozenset({"f64", "f32"})


def _validate_nonnegative_integer(value: object, field_name: str) -> None:
    """Require a real non-negative integer without accepting booleans."""
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")


def _validate_positive_integer(value: object, field_name: str) -> None:
    """Require a real positive integer without accepting booleans."""
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")


def _finite_number(value: object, field_name: str) -> float:
    """Return one finite real number and reject booleans or non-numeric text."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{field_name} must be a finite number")
    number = float(value)
    if not isfinite(number):
        raise ValueError(f"{field_name} must be a finite number")
    return number


@dataclass(frozen=True, slots=True)
class MissingnessSummary:
    """Describe missingness counts without carrying person-level observations."""

    total_observations: int
    complete_observations: int
    missing_predictor_observations: int
    missing_criterion_observations: int

    def __post_init__(self) -> None:
        """Reject impossible counts before a result can be correlated."""
        for field_name in (
            "total_observations",
            "complete_observations",
            "missing_predictor_observations",
            "missing_criterion_observations",
        ):
            _validate_nonnegative_integer(getattr(self, field_name), field_name)
        if self.total_observations == 0:
            raise ValueError("total_observations must be positive")
        if self.complete_observations > self.total_observations:
            raise ValueError("complete_observations cannot exceed total_observations")
        if self.missing_predictor_observations > self.total_observations:
            raise ValueError("missing_predictor_observations cannot exceed total_observations")
        if self.missing_criterion_observations > self.total_observations:
            raise ValueError("missing_criterion_observations cannot exceed total_observations")
        if self.complete_observations + self.missing_predictor_observations > self.total_observations:
            raise ValueError(
                "complete_observations and missing_predictor_observations cannot overlap"
            )
        if self.complete_observations + self.missing_criterion_observations > self.total_observations:
            raise ValueError(
                "complete_observations and missing_criterion_observations cannot overlap"
            )

    def to_dict(self) -> dict[str, int]:
        """Return deterministic count fields for the canonical result JSON."""
        return {
            "complete_observations": self.complete_observations,
            "missing_criterion_observations": self.missing_criterion_observations,
            "missing_predictor_observations": self.missing_predictor_observations,
            "total_observations": self.total_observations,
        }


@dataclass(frozen=True, slots=True)
class ConvergenceDiagnostics:
    """Record convergence evidence while preserving an explicit failure state."""

    converged: bool
    iterations: int
    objective_value: Real
    maximum_gradient: Real
    failure_code: str | None = None

    def __post_init__(self) -> None:
        """Require diagnostics that distinguish convergence from a failed fit."""
        if type(self.converged) is not bool:
            raise ValueError("converged must be a boolean")
        _validate_positive_integer(self.iterations, "iterations")
        _finite_number(self.objective_value, "objective_value")
        gradient = _finite_number(self.maximum_gradient, "maximum_gradient")
        if gradient < 0:
            raise ValueError("maximum_gradient must be non-negative")
        if self.converged and self.failure_code is not None:
            raise ValueError("failure_code must be absent for a converged result")
        if not self.converged and (
            not isinstance(self.failure_code, str) or not self.failure_code
        ):
            raise ValueError("failure_code is required for a nonconverged result")
        if self.failure_code is not None:
            _validate_code(self.failure_code, "failure_code")

    def to_dict(self) -> dict[str, object]:
        """Return deterministic convergence fields for the canonical result JSON."""
        payload: dict[str, object] = {
            "converged": self.converged,
            "iterations": self.iterations,
            "maximum_gradient": float(self.maximum_gradient),
            "objective_value": float(self.objective_value),
        }
        if self.failure_code is not None:
            payload["failure_code"] = self.failure_code
        return payload


@dataclass(frozen=True, slots=True, repr=False)
class ValidationAnalysisResult:
    """Immutable, digest-linked scientific evidence returned by the offline worker."""

    tenant_record_id: str
    result_reference: str
    handoff_digest: str
    provenance_digest: str
    fast_mlsirm_revision: str
    model_code: str
    backend: str
    precision: str
    effect_estimate: Real
    uncertainty_lower: Real
    uncertainty_upper: Real
    sample_size: int
    missingness_summary: MissingnessSummary
    convergence_diagnostics: ConvergenceDiagnostics
    completed_at: datetime
    result_authority: str = _RESULT_AUTHORITY
    execution_state: str = _EXECUTION_STATE
    contains_raw_person_level_values: bool = False
    human_review_required: bool = True
    evidence_version: int = 1

    def __post_init__(self) -> None:
        """Fail closed on malformed, unlinked, or decision-like result data."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(self.result_reference, "validation_analysis_result", "result_reference")
        _validate_digest(self.handoff_digest, "handoff_digest")
        _validate_digest(self.provenance_digest, "provenance_digest")
        _validate_kernel_revision(self.fast_mlsirm_revision)
        _validate_code(self.model_code, "model_code")
        if self.backend not in _ALLOWED_BACKENDS:
            raise ValueError("backend must be rust_cpu or rust_gpu")
        if self.precision not in _ALLOWED_PRECISIONS:
            raise ValueError("precision must be f64 or f32")
        estimate = _finite_number(self.effect_estimate, "effect_estimate")
        lower = _finite_number(self.uncertainty_lower, "uncertainty_lower")
        upper = _finite_number(self.uncertainty_upper, "uncertainty_upper")
        if lower > upper:
            raise ValueError("uncertainty_lower cannot exceed uncertainty_upper")
        if not lower <= estimate <= upper:
            raise ValueError("effect_estimate must be inside the uncertainty interval")
        _validate_positive_integer(self.sample_size, "sample_size")
        if type(self.missingness_summary) is not MissingnessSummary:
            raise ValueError("missingness_summary must be a MissingnessSummary")
        if type(self.convergence_diagnostics) is not ConvergenceDiagnostics:
            raise ValueError("convergence_diagnostics must be ConvergenceDiagnostics")
        if self.sample_size != self.missingness_summary.total_observations:
            raise ValueError("sample_size must match total_observations")
        _canonical_timestamp(self.completed_at)
        if self.result_authority != _RESULT_AUTHORITY:
            raise ValueError("result_authority must remain scientific_evidence_only")
        if self.execution_state != _EXECUTION_STATE:
            raise ValueError("execution_state must remain completed")
        if self.contains_raw_person_level_values is not False:
            raise ValueError("result must not contain raw person-level values")
        if self.human_review_required is not True:
            raise ValueError("human review is mandatory for validity interpretation")
        if type(self.evidence_version) is not int or self.evidence_version != 1:
            raise ValueError("evidence_version must remain 1")

    def __repr__(self) -> str:
        """Return a redacted representation suitable for routine application logs."""
        return "ValidationAnalysisResult(<redacted>)"

    def canonical_json(self) -> str:
        """Return deterministic, non-person-level JSON for audit correlation."""
        payload = {
            "backend": self.backend,
            "completed_at": _canonical_timestamp(self.completed_at),
            "contains_raw_person_level_values": self.contains_raw_person_level_values,
            "convergence_diagnostics": self.convergence_diagnostics.to_dict(),
            "effect_estimate": float(self.effect_estimate),
            "evidence_version": self.evidence_version,
            "execution_state": self.execution_state,
            "fast_mlsirm_revision": self.fast_mlsirm_revision,
            "handoff_digest": self.handoff_digest,
            "human_review_required": self.human_review_required,
            "missingness_summary": self.missingness_summary.to_dict(),
            "model_code": self.model_code,
            "precision": self.precision,
            "provenance_digest": self.provenance_digest,
            "result_authority": self.result_authority,
            "result_reference": self.result_reference,
            "sample_size": self.sample_size,
            "tenant_record_id": self.tenant_record_id,
            "uncertainty_lower": float(self.uncertainty_lower),
            "uncertainty_upper": float(self.uncertainty_upper),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical result bytes."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


__all__ = ["ConvergenceDiagnostics", "MissingnessSummary", "ValidationAnalysisResult"]
