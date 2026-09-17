"""Regression contract for point-weight and variance-design compatibility evidence."""

from datetime import datetime, timezone

import pytest

from orgmetra_validity_analysis import (
    FinalAnalysisWeightReceipt,
    WeightEligibilityReceipt,
    WeightVarianceCompatibilityReceipt,
)

TENANT = "10000000-0000-7000-8000-000000000001"
WEIGHT_RECEIPT = "analysis_weight_receipt:11111111-1111-4111-8111-111111111111"
COMPATIBILITY_RECEIPT = (
    "weight_variance_compatibility_receipt:22222222-2222-4222-8222-222222222222"
)
VARIANCE_RECEIPT = "variance_design_receipt:33333333-3333-4333-8333-333333333333"
ELIGIBILITY_RECEIPT = "weight_eligibility_receipt:44444444-4444-4444-8444-444444444444"
ESTIMAND = "validation_estimand:55555555-5555-4555-8555-555555555555"
TARGET = "analysis_target_population:66666666-6666-4666-8666-666666666666"
WINDOW = "analysis_window:77777777-7777-4777-8777-777777777777"
DURATION = "analysis_reference_duration:88888888-8888-4888-8888-888888888888"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
DIGEST_E = "e" * 64
DIGEST_F = "f" * 64
DIGEST_1 = "1" * 64
DIGEST_2 = "2" * 64
DIGEST_3 = "3" * 64
DIGEST_4 = "4" * 64
DIGEST_5 = "5" * 64


def weight_receipt(**overrides: object) -> FinalAnalysisWeightReceipt:
    """Build one base-weight-only receipt for compatibility correlation tests."""
    eligibility = WeightEligibilityReceipt(
        tenant_record_id=TENANT,
        receipt_reference=ELIGIBILITY_RECEIPT,
        weight_scope_code="cross_sectional",
        target_population_reference=TARGET,
        target_population_digest=DIGEST_B,
        reference_duration_reference=DURATION,
        reference_duration_digest=DIGEST_C,
        eligible_case_set_digest=DIGEST_D,
        weight_artifact_digest=DIGEST_5,
        constructed_at=datetime(2026, 9, 17, 0, 30, tzinfo=timezone.utc),
    )
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "receipt_reference": WEIGHT_RECEIPT,
        "estimand_reference": ESTIMAND,
        "estimand_digest": DIGEST_A,
        "estimand_scope_code": "cross_sectional",
        "target_population_reference": TARGET,
        "target_population_digest": DIGEST_B,
        "analysis_unit_code": "worker_occurrence",
        "analysis_window_reference": WINDOW,
        "reference_duration_reference": DURATION,
        "reference_duration_digest": DIGEST_C,
        "eligible_case_set_digest": DIGEST_D,
        "analytic_case_occurrence_set_digest": DIGEST_E,
        "source_universe_receipt_digest": DIGEST_F,
        "sampling_design_receipt_digest": DIGEST_1,
        "base_weight_method_code": "inverse_inclusion_probability",
        "base_weight_method_version": 1,
        "base_weight_evidence_digest": DIGEST_2,
        "base_weight_artifact_digest": DIGEST_5,
        "adjustments": (),
        "final_weight_artifact_digest": DIGEST_5,
        "weight_eligibility": eligibility,
        "analytic_case_count": 12,
        "constructed_at": datetime(2026, 9, 17, 0, 30, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return FinalAnalysisWeightReceipt(**values)


def compatibility(**overrides: object) -> WeightVarianceCompatibilityReceipt:
    """Build owner-correlatable compatibility evidence for one weighted analysis."""
    point_weight = overrides.pop("analysis_weight_receipt", weight_receipt())
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "receipt_reference": COMPATIBILITY_RECEIPT,
        "analysis_weight_receipt": point_weight,
        "variance_design_receipt_reference": VARIANCE_RECEIPT,
        "variance_design_receipt_version": 1,
        "variance_design_receipt_digest": DIGEST_3,
        "variance_analysis_weight_receipt_digest": point_weight.sha256_digest(),
        "variance_analytic_case_occurrence_set_digest": (
            point_weight.analytic_case_occurrence_set_digest
        ),
        "variance_weight_eligibility_receipt_digest": (
            point_weight.weight_eligibility.sha256_digest()
        ),
        "variance_weight_correction_sequence": point_weight.correction_sequence,
        "variance_final_weight_artifact_digest": point_weight.final_weight_artifact_digest,
        "constructed_at": datetime(2026, 9, 17, 0, 31, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return WeightVarianceCompatibilityReceipt(**values)


def test_compatibility_receipt_binds_exact_point_and_variance_lineage() -> None:
    """Require variance evidence to name the exact point-weight basis it accompanies."""
    candidate = compatibility()
    payload = candidate.canonical_json()
    assert candidate.sha256_digest() == compatibility().sha256_digest()
    assert f'"variance_design_receipt_digest":"{DIGEST_3}"' in payload
    assert f'"variance_final_weight_artifact_digest":"{DIGEST_5}"' in payload
    assert repr(candidate) == "WeightVarianceCompatibilityReceipt(<redacted>)"


@pytest.mark.parametrize(
    "field,value,match",
    [
        ("variance_analysis_weight_receipt_digest", DIGEST_A, "analysis weight receipt"),
        ("variance_analytic_case_occurrence_set_digest", DIGEST_A, "analytic case occurrence"),
        ("variance_weight_eligibility_receipt_digest", DIGEST_A, "weight eligibility"),
        ("variance_weight_correction_sequence", 2, "correction sequence"),
        ("variance_final_weight_artifact_digest", DIGEST_A, "final weight artifact"),
    ],
)
def test_compatibility_receipt_rejects_point_variance_lineage_mismatch(
    field: str, value: object, match: str
) -> None:
    """Fail closed when variance evidence was generated from a different weight lineage."""
    with pytest.raises(ValueError, match=match):
        compatibility(**{field: value})


def test_compatibility_receipt_rejects_foreign_point_weight_or_tenant() -> None:
    """Do not admit an opaque object or a point-weight receipt from another tenant."""
    with pytest.raises(ValueError, match="FinalAnalysisWeightReceipt"):
        compatibility(analysis_weight_receipt=object())

    foreign = weight_receipt(
        tenant_record_id="10000000-0000-7000-8000-000000000002",
        weight_eligibility=WeightEligibilityReceipt(
            tenant_record_id="10000000-0000-7000-8000-000000000002",
            receipt_reference=ELIGIBILITY_RECEIPT,
            weight_scope_code="cross_sectional",
            target_population_reference=TARGET,
            target_population_digest=DIGEST_B,
            reference_duration_reference=DURATION,
            reference_duration_digest=DIGEST_C,
            eligible_case_set_digest=DIGEST_D,
            weight_artifact_digest=DIGEST_5,
            constructed_at=datetime(2026, 9, 17, 0, 30, tzinfo=timezone.utc),
        ),
    )
    with pytest.raises(ValueError, match="tenant_record_id"):
        compatibility(analysis_weight_receipt=foreign)


def test_compatibility_receipt_rejects_point_receipt_as_variance_receipt() -> None:
    """Point-weight evidence cannot masquerade as the distinct variance-design receipt."""
    point_weight = weight_receipt()
    with pytest.raises(ValueError, match="distinct from the analysis weight receipt"):
        compatibility(
            analysis_weight_receipt=point_weight,
            variance_design_receipt_digest=point_weight.sha256_digest(),
        )


def test_compatibility_receipt_rejects_time_reversal_and_schema_forgery() -> None:
    """Compatibility evidence cannot predate its point weight or invent a schema version."""
    with pytest.raises(ValueError, match="cannot precede"):
        compatibility(constructed_at=datetime(2026, 9, 17, 0, 29, tzinfo=timezone.utc))
    with pytest.raises(ValueError, match="evidence_version"):
        compatibility(evidence_version=2)


@pytest.mark.parametrize("version", [0, True])
def test_variance_design_receipt_version_is_strictly_positive(version: object) -> None:
    """Reject unversioned or boolean variance owner evidence."""
    with pytest.raises(ValueError, match="variance_design_receipt_version"):
        compatibility(variance_design_receipt_version=version)
