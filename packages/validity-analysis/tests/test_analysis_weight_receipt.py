"""RED contract for reproducible point-estimation weight lineage."""

from datetime import datetime, timezone

import pytest

from orgmetra_validity_analysis import AnalysisWeightAdjustment, FinalAnalysisWeightReceipt

TENANT = "10000000-0000-7000-8000-000000000001"
RECEIPT = "analysis_weight_receipt:11111111-1111-4111-8111-111111111111"
ESTIMAND = "validation_estimand:22222222-2222-4222-8222-222222222222"
TARGET = "analysis_target_population:33333333-3333-4333-8333-333333333333"
WINDOW = "analysis_window:44444444-4444-4444-8444-444444444444"
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


def adjustment() -> AnalysisWeightAdjustment:
    """Return one governed nonresponse adjustment without copying case weights."""
    return AnalysisWeightAdjustment(
        sequence_number=1,
        adjustment_code="nonresponse_adjustment",
        method_reference="weight_method:55555555-5555-4555-8555-555555555555",
        method_version=1,
        input_weight_artifact_digest=DIGEST_D,
        output_weight_artifact_digest=DIGEST_E,
        configuration_digest=DIGEST_F,
        evidence_receipt_digest=DIGEST_1,
    )


def receipt(**overrides: object) -> FinalAnalysisWeightReceipt:
    """Return one exact final point-weight receipt."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "receipt_reference": RECEIPT,
        "estimand_reference": ESTIMAND,
        "estimand_digest": DIGEST_A,
        "target_population_reference": TARGET,
        "target_population_digest": DIGEST_B,
        "analysis_unit_code": "worker_occurrence",
        "analysis_window_reference": WINDOW,
        "eligible_case_set_digest": DIGEST_C,
        "analytic_case_occurrence_set_digest": DIGEST_2,
        "source_universe_receipt_digest": DIGEST_3,
        "sampling_design_receipt_digest": DIGEST_4,
        "base_weight_method_code": "inverse_inclusion_probability",
        "base_weight_method_version": 1,
        "base_weight_evidence_digest": DIGEST_5,
        "base_weight_artifact_digest": DIGEST_D,
        "adjustments": (adjustment(),),
        "final_weight_artifact_digest": DIGEST_E,
        "analytic_case_count": 12,
        "constructed_at": datetime(2026, 9, 17, 4, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return FinalAnalysisWeightReceipt(**values)


def test_receipt_is_deterministic_and_value_minimized() -> None:
    """Bind exact estimand and ordered weight lineage without embedding row weights."""
    candidate = receipt()
    assert candidate.sha256_digest() == receipt().sha256_digest()
    assert candidate.final_weight_artifact_digest == DIGEST_E
    assert "person_record" not in candidate.canonical_json()
    assert "weight_value" not in candidate.canonical_json()


def test_adjustment_chain_must_reach_final_weight_artifact() -> None:
    """Reject a receipt whose declared final weight is not the ordered chain output."""
    with pytest.raises(ValueError, match="final_weight_artifact_digest"):
        receipt(final_weight_artifact_digest=DIGEST_F)


def test_probability_design_receipt_is_required() -> None:
    """Do not allow point weights to detach from the sampled design evidence."""
    with pytest.raises(ValueError, match="sampling_design_receipt_digest"):
        receipt(sampling_design_receipt_digest="not-a-digest")


def test_correction_must_link_to_the_superseded_receipt() -> None:
    """Require append-only correction lineage instead of overwriting prior weight evidence."""
    with pytest.raises(ValueError, match="supersedes_receipt_digest"):
        receipt(correction_sequence=2)
