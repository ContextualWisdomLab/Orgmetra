"""RED contract for binding weighted scientific results to exact weight evidence."""

from datetime import datetime, timezone

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
WEIGHT_DIGEST = "c" * 64
VARIANCE_DIGEST = "d" * 64


def result(**overrides: object) -> ValidationAnalysisResult:
    """Build one bounded validity result with targeted inference overrides."""
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
        "missingness_summary": MissingnessSummary(
            total_observations=12,
            complete_observations=10,
            missing_predictor_observations=1,
            missing_criterion_observations=1,
        ),
        "convergence_diagnostics": ConvergenceDiagnostics(
            converged=True,
            iterations=42,
            objective_value=-12.5,
            maximum_gradient=0.0001,
        ),
        "completed_at": datetime(2026, 9, 17, 4, 10, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return ValidationAnalysisResult(**values)


def test_weighted_result_binds_point_and_variance_receipts_separately() -> None:
    """Require exact point-weight and variance evidence on weighted inference."""
    candidate = result(
        point_estimation_mode="weighted_design_based",
        analysis_weight_receipt_digest=WEIGHT_DIGEST,
        variance_design_receipt_digest=VARIANCE_DIGEST,
    )
    payload = candidate.canonical_json()
    assert '"point_estimation_mode":"weighted_design_based"' in payload
    assert f'"analysis_weight_receipt_digest":"{WEIGHT_DIGEST}"' in payload
    assert f'"variance_design_receipt_digest":"{VARIANCE_DIGEST}"' in payload


@pytest.mark.parametrize(
    "overrides,match",
    [
        (
            {
                "point_estimation_mode": "weighted_design_based",
                "analysis_weight_receipt_digest": None,
                "variance_design_receipt_digest": VARIANCE_DIGEST,
            },
            "analysis_weight_receipt_digest",
        ),
        (
            {
                "point_estimation_mode": "weighted_design_based",
                "analysis_weight_receipt_digest": WEIGHT_DIGEST,
                "variance_design_receipt_digest": None,
            },
            "variance_design_receipt_digest",
        ),
        (
            {
                "point_estimation_mode": "unweighted",
                "analysis_weight_receipt_digest": WEIGHT_DIGEST,
            },
            "unweighted",
        ),
        ({"point_estimation_mode": "opaque_weighted"}, "point_estimation_mode"),
    ],
)
def test_result_rejects_unverifiable_weight_binding(
    overrides: dict[str, object], match: str
) -> None:
    """Fail closed when result and point/variance weight provenance disagree."""
    with pytest.raises(ValueError, match=match):
        result(**overrides)
