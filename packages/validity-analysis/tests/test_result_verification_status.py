"""Regression coverage for non-authorizing scientific verification status."""

from datetime import datetime, timezone
import json

from orgmetra_validity_analysis import (
    ConvergenceDiagnostics,
    MissingnessSummary,
    REVIEWED_FAST_MLSIRM_REVISION,
    ValidationAnalysisResult,
)


def _result(*, converged: bool) -> ValidationAnalysisResult:
    """Build one aggregate-only result with an explicit convergence outcome."""
    return ValidationAnalysisResult(
        tenant_record_id="10000000-0000-7000-8000-000000000001",
        result_reference="validation_analysis_result:77777777-7777-4777-8777-777777777777",
        handoff_digest="a" * 64,
        provenance_digest="b" * 64,
        fast_mlsirm_revision=REVIEWED_FAST_MLSIRM_REVISION,
        model_code="mlsirm_criterion_related",
        backend="rust_cpu",
        precision="f64",
        effect_estimate=0.42,
        uncertainty_lower=0.10,
        uncertainty_upper=0.70,
        sample_size=12,
        missingness_summary=MissingnessSummary(
            total_observations=12,
            complete_observations=10,
            missing_predictor_observations=1,
            missing_criterion_observations=1,
        ),
        convergence_diagnostics=ConvergenceDiagnostics(
            converged=converged,
            iterations=42,
            objective_value=-12.5,
            maximum_gradient=0.0001,
            failure_code=None if converged else "maximum_iterations",
        ),
        completed_at=datetime(2026, 9, 17, 5, 30, tzinfo=timezone.utc),
    )


def test_converged_result_is_explicitly_verified() -> None:
    candidate = _result(converged=True)

    assert candidate.verification_status == "verified"
    assert json.loads(candidate.canonical_json())["verification_status"] == "verified"


def test_nonconverged_result_is_explicitly_not_verifiable() -> None:
    candidate = _result(converged=False)

    assert candidate.verification_status == "not_verifiable"
    payload = json.loads(candidate.canonical_json())
    assert payload["verification_status"] == "not_verifiable"
    assert payload["execution_state"] == "completed"
    assert payload["convergence_diagnostics"]["failure_code"] == "maximum_iterations"
