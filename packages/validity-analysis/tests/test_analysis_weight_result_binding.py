"""Regression contract for binding weighted results to exact weight evidence."""

from datetime import datetime, timezone

import pytest

from orgmetra_validity_analysis import (
    ConvergenceDiagnostics,
    FinalAnalysisWeightReceipt,
    MissingnessSummary,
    REVIEWED_FAST_MLSIRM_REVISION,
    ValidationAnalysisResult,
    WeightEligibilityReceipt,
    WeightVarianceCompatibilityReceipt,
)

TENANT = "10000000-0000-7000-8000-000000000001"
RESULT = "validation_analysis_result:11111111-1111-4111-8111-111111111111"
WEIGHT_RECEIPT = "analysis_weight_receipt:22222222-2222-4222-8222-222222222222"
ELIGIBILITY_RECEIPT = "weight_eligibility_receipt:33333333-3333-4333-8333-333333333333"
COMPATIBILITY_RECEIPT = (
    "weight_variance_compatibility_receipt:44444444-4444-4444-8444-444444444444"
)
VARIANCE_RECEIPT = "variance_design_receipt:55555555-5555-4555-8555-555555555555"
ESTIMAND = "validation_estimand:66666666-6666-4666-8666-666666666666"
TARGET = "analysis_target_population:77777777-7777-4777-8777-777777777777"
WINDOW = "analysis_window:88888888-8888-4888-8888-888888888888"
DURATION = "analysis_reference_duration:99999999-9999-4999-8999-999999999999"
HANDOFF_DIGEST = "a" * 64
PROVENANCE_DIGEST = "b" * 64
VARIANCE_DIGEST = "d" * 64
OTHER_VARIANCE_DIGEST = "e" * 64
DIGEST_1 = "1" * 64
DIGEST_2 = "2" * 64
DIGEST_3 = "3" * 64
DIGEST_4 = "4" * 64
DIGEST_5 = "5" * 64
DIGEST_6 = "6" * 64
DIGEST_7 = "7" * 64


def point_weight(**overrides: object) -> FinalAnalysisWeightReceipt:
    """Build one base-weight-only point-estimation receipt for result binding."""
    eligibility = WeightEligibilityReceipt(
        tenant_record_id=TENANT,
        receipt_reference=ELIGIBILITY_RECEIPT,
        weight_scope_code="cross_sectional",
        target_population_reference=TARGET,
        target_population_digest=DIGEST_1,
        reference_duration_reference=DURATION,
        reference_duration_digest=DIGEST_2,
        eligible_case_set_digest=DIGEST_3,
        weight_artifact_digest=DIGEST_7,
        constructed_at=datetime(2026, 9, 17, 4, 0, tzinfo=timezone.utc),
    )
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "receipt_reference": WEIGHT_RECEIPT,
        "estimand_reference": ESTIMAND,
        "estimand_digest": DIGEST_4,
        "estimand_scope_code": "cross_sectional",
        "target_population_reference": TARGET,
        "target_population_digest": DIGEST_1,
        "analysis_unit_code": "worker_occurrence",
        "analysis_window_reference": WINDOW,
        "reference_duration_reference": DURATION,
        "reference_duration_digest": DIGEST_2,
        "eligible_case_set_digest": DIGEST_3,
        "analytic_case_occurrence_set_digest": DIGEST_5,
        "source_universe_receipt_digest": DIGEST_6,
        "sampling_design_receipt_digest": "8" * 64,
        "base_weight_method_code": "inverse_inclusion_probability",
        "base_weight_method_version": 1,
        "base_weight_evidence_digest": "9" * 64,
        "base_weight_artifact_digest": DIGEST_7,
        "adjustments": (),
        "final_weight_artifact_digest": DIGEST_7,
        "weight_eligibility": eligibility,
        "analytic_case_count": 12,
        "constructed_at": datetime(2026, 9, 17, 4, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return FinalAnalysisWeightReceipt(**values)


def compatibility(
    weight: FinalAnalysisWeightReceipt, variance_digest: str = VARIANCE_DIGEST
) -> WeightVarianceCompatibilityReceipt:
    """Build compatibility evidence whose variance lineage names the exact point weight."""
    return WeightVarianceCompatibilityReceipt(
        tenant_record_id=TENANT,
        receipt_reference=COMPATIBILITY_RECEIPT,
        analysis_weight_receipt=weight,
        variance_design_receipt_reference=VARIANCE_RECEIPT,
        variance_design_receipt_version=1,
        variance_design_receipt_digest=variance_digest,
        variance_analysis_weight_receipt_digest=weight.sha256_digest(),
        variance_analytic_case_occurrence_set_digest=(
            weight.analytic_case_occurrence_set_digest
        ),
        variance_weight_eligibility_receipt_digest=(
            weight.weight_eligibility.sha256_digest()
        ),
        variance_weight_correction_sequence=weight.correction_sequence,
        variance_final_weight_artifact_digest=weight.final_weight_artifact_digest,
        constructed_at=datetime(2026, 9, 17, 4, 5, tzinfo=timezone.utc),
    )


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


def test_weighted_result_binds_point_variance_and_compatibility_receipts() -> None:
    """Require exact point-weight, variance, and cross-lineage compatibility evidence."""
    weight = point_weight()
    correlation = compatibility(weight)
    candidate = result(
        point_estimation_mode="weighted_design_based",
        analysis_weight_receipt_digest=weight.sha256_digest(),
        variance_design_receipt_digest=VARIANCE_DIGEST,
        weight_variance_compatibility=correlation,
    )
    payload = candidate.canonical_json()
    assert '"point_estimation_mode":"weighted_design_based"' in payload
    assert f'"analysis_weight_receipt_digest":"{weight.sha256_digest()}"' in payload
    assert f'"variance_design_receipt_digest":"{VARIANCE_DIGEST}"' in payload
    assert (
        f'"weight_variance_compatibility_receipt_digest":"{correlation.sha256_digest()}"'
        in payload
    )


def test_weighted_result_rejects_same_point_and_variance_receipt() -> None:
    """A variance-design receipt cannot silently stand in for the point-weight receipt."""
    weight = point_weight()
    with pytest.raises(ValueError, match="must identify different evidence"):
        result(
            point_estimation_mode="weighted_design_based",
            analysis_weight_receipt_digest=weight.sha256_digest(),
            variance_design_receipt_digest=weight.sha256_digest(),
            weight_variance_compatibility=compatibility(weight),
        )


def test_weighted_result_requires_compatibility_receipt() -> None:
    """Do not release weighted inference without explicit point/variance congruence."""
    weight = point_weight()
    with pytest.raises(ValueError, match="weight_variance_compatibility"):
        result(
            point_estimation_mode="weighted_design_based",
            analysis_weight_receipt_digest=weight.sha256_digest(),
            variance_design_receipt_digest=VARIANCE_DIGEST,
        )


def test_weighted_result_rejects_compatibility_for_other_point_or_variance_evidence() -> None:
    """The compatibility receipt must correlate the same point and variance digests."""
    weight = point_weight()
    corrected_weight = point_weight(
        correction_sequence=2,
        supersedes_receipt_digest=weight.sha256_digest(),
    )
    with pytest.raises(ValueError, match="analysis weight receipt"):
        result(
            point_estimation_mode="weighted_design_based",
            analysis_weight_receipt_digest=weight.sha256_digest(),
            variance_design_receipt_digest=VARIANCE_DIGEST,
            weight_variance_compatibility=compatibility(corrected_weight),
        )
    with pytest.raises(ValueError, match="variance design receipt"):
        result(
            point_estimation_mode="weighted_design_based",
            analysis_weight_receipt_digest=weight.sha256_digest(),
            variance_design_receipt_digest=OTHER_VARIANCE_DIGEST,
            weight_variance_compatibility=compatibility(weight),
        )


def test_weighted_result_rechecks_compatibility_tenant_and_time_boundary() -> None:
    """Forged compatibility state cannot cross tenant or result-time boundaries."""
    weight = point_weight()
    correlation = compatibility(weight)
    object.__setattr__(
        correlation,
        "tenant_record_id",
        "10000000-0000-7000-8000-000000000002",
    )
    with pytest.raises(ValueError, match="tenant_record_id"):
        result(
            point_estimation_mode="weighted_design_based",
            analysis_weight_receipt_digest=weight.sha256_digest(),
            variance_design_receipt_digest=VARIANCE_DIGEST,
            weight_variance_compatibility=correlation,
        )

    later = compatibility(weight)
    object.__setattr__(
        later,
        "constructed_at",
        datetime(2026, 9, 17, 4, 11, tzinfo=timezone.utc),
    )
    with pytest.raises(ValueError, match="cannot be constructed after"):
        result(
            point_estimation_mode="weighted_design_based",
            analysis_weight_receipt_digest=weight.sha256_digest(),
            variance_design_receipt_digest=VARIANCE_DIGEST,
            weight_variance_compatibility=later,
        )


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
                "analysis_weight_receipt_digest": "c" * 64,
                "variance_design_receipt_digest": None,
            },
            "variance_design_receipt_digest",
        ),
        (
            {
                "point_estimation_mode": "unweighted",
                "analysis_weight_receipt_digest": "c" * 64,
            },
            "unweighted",
        ),
        (
            {
                "point_estimation_mode": "unweighted",
                "variance_design_receipt_digest": VARIANCE_DIGEST,
            },
            "unweighted",
        ),
        (
            {
                "point_estimation_mode": "unweighted",
                "weight_variance_compatibility": compatibility(point_weight()),
            },
            "unweighted",
        ),
        ({"point_estimation_mode": "opaque_weighted"}, "point_estimation_mode"),
        ({"point_estimation_mode": None}, "point_estimation_mode"),
    ],
)
def test_result_rejects_unverifiable_weight_binding(
    overrides: dict[str, object], match: str
) -> None:
    """Fail closed when result and point/variance weight provenance disagree."""
    with pytest.raises(ValueError, match=match):
        result(**overrides)


def test_weighted_result_rejects_malformed_receipt_digests() -> None:
    """Do not permit opaque labels to stand in for immutable weight evidence."""
    weight = point_weight()
    with pytest.raises(ValueError, match="analysis_weight_receipt_digest"):
        result(
            point_estimation_mode="weighted_design_based",
            analysis_weight_receipt_digest="weight-v1",
            variance_design_receipt_digest=VARIANCE_DIGEST,
            weight_variance_compatibility=compatibility(weight),
        )
    with pytest.raises(ValueError, match="variance_design_receipt_digest"):
        result(
            point_estimation_mode="weighted_design_based",
            analysis_weight_receipt_digest=weight.sha256_digest(),
            variance_design_receipt_digest="variance-v1",
            weight_variance_compatibility=compatibility(weight),
        )
