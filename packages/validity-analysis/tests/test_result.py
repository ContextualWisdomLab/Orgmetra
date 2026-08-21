"""Regression tests for the bounded numerical result contract."""

from dataclasses import asdict, replace
from datetime import datetime, timezone
import json

import pytest

from orgmetra_validity_analysis import (
    ConvergenceDiagnostics,
    MissingnessSummary,
    REVIEWED_FAST_MLSIRM_REVISION,
    ValidationAnalysisResult,
)

TENANT = "10000000-0000-7000-8000-000000000001"
RESULT = "validation_analysis_result:11111111-1111-4111-8111-111111111111"
HANDOFF_DIGEST = "a" * 64
PROVENANCE_DIGEST = "b" * 64
COMPLETED_AT = datetime(2026, 8, 21, 7, 10, 11, 123456, tzinfo=timezone.utc)


def missingness() -> MissingnessSummary:
    """Return one realistic aggregate-only missingness summary."""
    return MissingnessSummary(
        total_observations=12,
        complete_observations=10,
        missing_predictor_observations=1,
        missing_criterion_observations=1,
    )


def convergence(*, converged: bool = True) -> ConvergenceDiagnostics:
    """Return one converged or explicitly nonconverged diagnostic record."""
    return ConvergenceDiagnostics(
        converged=converged,
        iterations=42,
        objective_value=-12.5,
        maximum_gradient=0.0001,
        failure_code=None if converged else "maximum_iterations",
    )


def result(**overrides: object) -> ValidationAnalysisResult:
    """Build one valid result envelope and apply targeted test overrides."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "result_reference": RESULT,
        "handoff_digest": HANDOFF_DIGEST,
        "provenance_digest": PROVENANCE_DIGEST,
        "fast_mlsirm_revision": REVIEWED_FAST_MLSIRM_REVISION,
        "model_code": "mlsirm_criterion_related",
        "backend": "rust_cpu",
        "precision": "f64",
        "effect_estimate": 0.42,
        "uncertainty_lower": 0.10,
        "uncertainty_upper": 0.70,
        "sample_size": 12,
        "missingness_summary": missingness(),
        "convergence_diagnostics": convergence(),
        "completed_at": COMPLETED_AT,
    }
    values.update(overrides)
    return ValidationAnalysisResult(**values)


def test_aggregate_evidence_is_deterministic_and_redacted() -> None:
    """Serialize only aggregate evidence and preserve exact replay bytes."""
    candidate = result()
    payload = json.loads(candidate.canonical_json())

    assert payload["tenant_record_id"] == TENANT
    assert payload["backend"] == "rust_cpu"
    assert payload["precision"] == "f64"
    assert payload["execution_state"] == "completed"
    assert payload["result_authority"] == "scientific_evidence_only"
    assert payload["missingness_summary"]["total_observations"] == 12
    assert payload["convergence_diagnostics"]["converged"] is True
    assert "person_record" not in candidate.canonical_json()
    assert repr(candidate) == "ValidationAnalysisResult(<redacted>)"
    assert len(candidate.sha256_digest()) == 64
    assert candidate.canonical_json() == result().canonical_json()


def test_gpu_and_nonconverged_result_are_explicitly_typed() -> None:
    """Record GPU provenance and a typed nonconvergence state without promotion."""
    candidate = result(
        backend="rust_gpu",
        precision="f32",
        convergence_diagnostics=convergence(converged=False),
    )
    payload = json.loads(candidate.canonical_json())
    assert payload["backend"] == "rust_gpu"
    assert payload["precision"] == "f32"
    assert payload["convergence_diagnostics"]["failure_code"] == "maximum_iterations"


@pytest.mark.parametrize(
    "bad",
    [
        {"total_observations": True},
        {"total_observations": -1},
        {"total_observations": 0},
        {"complete_observations": 13},
        {"missing_predictor_observations": 13},
        {"missing_criterion_observations": 13},
    ],
)
def test_missingness_rejects_invalid_counts(bad: dict[str, object]) -> None:
    """Reject booleans, negative counts, empty samples, and impossible totals."""
    values = asdict(missingness())
    values.update(bad)
    with pytest.raises(ValueError):
        MissingnessSummary(**values)


@pytest.mark.parametrize("bad", [True, 0, -1])
def test_positive_integer_validation_rejects_nonpositive_values(bad: object) -> None:
    """Exercise strict sample and iteration bounds."""
    with pytest.raises(ValueError, match="positive integer"):
        ConvergenceDiagnostics(True, bad, -1.0, 0.1)
    with pytest.raises(ValueError, match="positive integer"):
        result(sample_size=bad)


@pytest.mark.parametrize("bad", [True, "0.1", float("nan"), float("inf")])
def test_numeric_fields_reject_boolean_text_and_nonfinite_values(bad: object) -> None:
    """Do not accept values that cannot be represented as finite scientific evidence."""
    with pytest.raises(ValueError, match="finite number"):
        ConvergenceDiagnostics(True, 1, bad, 0.1)
    with pytest.raises(ValueError, match="finite number"):
        result(effect_estimate=bad)


def test_negative_gradient_and_invalid_convergence_states_fail_closed() -> None:
    """Require explicit and internally consistent convergence diagnostics."""
    with pytest.raises(ValueError, match="non-negative"):
        ConvergenceDiagnostics(True, 1, 1.0, -0.1)
    with pytest.raises(ValueError, match="boolean"):
        ConvergenceDiagnostics(1, 1, 1.0, 0.1)
    with pytest.raises(ValueError, match="absent"):
        ConvergenceDiagnostics(True, 1, 1.0, 0.1, "failed_fit")
    with pytest.raises(ValueError, match="required"):
        ConvergenceDiagnostics(False, 1, 1.0, 0.1)
    with pytest.raises(ValueError, match="required"):
        ConvergenceDiagnostics(False, 1, 1.0, 0.1, "")


@pytest.mark.parametrize(
    "field,bad,match",
    [
        ("backend", "numpy", "backend"),
        ("precision", "float16", "precision"),
        ("uncertainty_lower", 0.8, "uncertainty_lower"),
        ("uncertainty_upper", 0.0, "uncertainty_lower"),
        ("effect_estimate", 0.8, "effect_estimate"),
        ("sample_size", 11, "sample_size"),
        ("result_authority", "employment_decision", "result_authority"),
        ("execution_state", "not_executed", "execution_state"),
        ("contains_raw_person_level_values", True, "raw person-level"),
        ("human_review_required", False, "human review"),
        ("evidence_version", 2, "evidence_version"),
    ],
)
def test_result_invariants_cannot_be_weakened(field: str, bad: object, match: str) -> None:
    """Reject malformed intervals, lineage, or governance flags."""
    with pytest.raises(ValueError, match=match):
        replace(result(), **{field: bad})


def test_result_requires_canonical_timestamp_and_aggregate_types() -> None:
    """Reject a naive completion time and non-summary diagnostic objects."""
    with pytest.raises(ValueError, match="requested_at"):
        result(completed_at=datetime(2026, 8, 21, 7, 10))
    with pytest.raises(ValueError, match="missingness_summary"):
        result(missingness_summary=object())
    with pytest.raises(ValueError, match="convergence_diagnostics"):
        result(convergence_diagnostics=object())
