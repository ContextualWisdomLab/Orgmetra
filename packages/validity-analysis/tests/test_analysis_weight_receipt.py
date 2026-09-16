"""Regression contracts for reproducible point-estimation weight lineage."""

from datetime import datetime, timezone

import pytest

from orgmetra_validity_analysis import (
    AnalysisWeightAdjustment,
    FinalAnalysisWeightReceipt,
    WeightEligibilityReceipt,
)

TENANT = "10000000-0000-7000-8000-000000000001"
RECEIPT = "analysis_weight_receipt:11111111-1111-4111-8111-111111111111"
ELIGIBILITY_RECEIPT = "weight_eligibility_receipt:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
ESTIMAND = "validation_estimand:22222222-2222-4222-8222-222222222222"
TARGET = "analysis_target_population:33333333-3333-4333-8333-333333333333"
WINDOW = "analysis_window:44444444-4444-4444-8444-444444444444"
DURATION = "analysis_reference_duration:77777777-7777-4777-8777-777777777777"
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
DIGEST_6 = "6" * 64


def adjustment(**overrides: object) -> AnalysisWeightAdjustment:
    """Return one governed adjustment without copying case-level weight values."""
    values: dict[str, object] = {
        "sequence_number": 1,
        "adjustment_code": "nonresponse_adjustment",
        "method_reference": "weight_method:55555555-5555-4555-8555-555555555555",
        "method_version": 1,
        "input_weight_artifact_digest": DIGEST_D,
        "output_weight_artifact_digest": DIGEST_E,
        "configuration_digest": DIGEST_F,
        "evidence_receipt_digest": DIGEST_1,
        "evidence_kind": "nonresponse_adjustment_receipt",
    }
    values.update(overrides)
    return AnalysisWeightAdjustment(**values)


def eligibility(**overrides: object) -> WeightEligibilityReceipt:
    """Return one weight eligibility receipt aligned to the default estimand."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "receipt_reference": ELIGIBILITY_RECEIPT,
        "weight_scope_code": "cross_sectional",
        "target_population_reference": TARGET,
        "target_population_digest": DIGEST_B,
        "reference_duration_reference": DURATION,
        "reference_duration_digest": DIGEST_6,
        "eligible_case_set_digest": DIGEST_C,
        "weight_artifact_digest": DIGEST_E,
        "constructed_at": datetime(2026, 9, 17, 4, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return WeightEligibilityReceipt(**values)


def receipt(**overrides: object) -> FinalAnalysisWeightReceipt:
    """Return one exact final point-weight receipt."""
    final_weight = overrides.get("final_weight_artifact_digest", DIGEST_E)
    eligibility_receipt = overrides.get(
        "weight_eligibility", eligibility(weight_artifact_digest=final_weight)
    )
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "receipt_reference": RECEIPT,
        "estimand_reference": ESTIMAND,
        "estimand_digest": DIGEST_A,
        "estimand_scope_code": "cross_sectional",
        "target_population_reference": TARGET,
        "target_population_digest": DIGEST_B,
        "analysis_unit_code": "worker_occurrence",
        "analysis_window_reference": WINDOW,
        "reference_duration_reference": DURATION,
        "reference_duration_digest": DIGEST_6,
        "eligible_case_set_digest": DIGEST_C,
        "analytic_case_occurrence_set_digest": DIGEST_2,
        "source_universe_receipt_digest": DIGEST_3,
        "sampling_design_receipt_digest": DIGEST_4,
        "base_weight_method_code": "inverse_inclusion_probability",
        "base_weight_method_version": 1,
        "base_weight_evidence_digest": DIGEST_5,
        "base_weight_artifact_digest": DIGEST_D,
        "adjustments": (adjustment(),),
        "final_weight_artifact_digest": final_weight,
        "weight_eligibility": eligibility_receipt,
        "analytic_case_count": 12,
        "constructed_at": datetime(2026, 9, 17, 4, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return FinalAnalysisWeightReceipt(**values)


def test_receipt_is_deterministic_value_minimized_and_redacted() -> None:
    """Bind exact estimand and ordered weight lineage without embedding row weights."""
    candidate = receipt()
    assert candidate.sha256_digest() == receipt().sha256_digest()
    assert candidate.final_weight_artifact_digest == DIGEST_E
    assert "person_record" not in candidate.canonical_json()
    assert "weight_value" not in candidate.canonical_json()
    assert "weight_eligibility_receipt_digest" in candidate.canonical_json()
    assert repr(candidate) == "FinalAnalysisWeightReceipt(<redacted>)"


def test_no_adjustment_receipt_can_bind_base_weight_as_final_weight() -> None:
    """Allow an explicit base-weight-only analysis without inventing a transform."""
    candidate = receipt(adjustments=(), final_weight_artifact_digest=DIGEST_D)
    assert '"adjustments":[]' in candidate.canonical_json()
    assert candidate.final_weight_artifact_digest == DIGEST_D


def test_adjustment_chain_must_reach_final_weight_artifact() -> None:
    """Reject a receipt whose declared final weight is not the ordered chain output."""
    with pytest.raises(ValueError, match="final_weight_artifact_digest"):
        receipt(final_weight_artifact_digest=DIGEST_F)


def test_adjustment_rejects_noop_artifact_identity() -> None:
    """Require each declared transform to produce a distinct artifact identity."""
    with pytest.raises(ValueError, match="output_weight_artifact_digest"):
        adjustment(output_weight_artifact_digest=DIGEST_D)


def test_adjustments_must_be_immutable_exact_and_contiguous() -> None:
    """Reject mutable, foreign, skipped, or disconnected adjustment chains."""
    with pytest.raises(ValueError, match="immutable tuple"):
        receipt(adjustments=[adjustment()])
    with pytest.raises(ValueError, match="AnalysisWeightAdjustment"):
        receipt(adjustments=(object(),))
    with pytest.raises(ValueError, match="sequence_number"):
        receipt(adjustments=(adjustment(sequence_number=2),))
    with pytest.raises(ValueError, match="breaks the weight chain"):
        receipt(adjustments=(adjustment(input_weight_artifact_digest=DIGEST_C),))


def test_probability_design_receipt_is_required() -> None:
    """Do not allow point weights to detach from the sampled design evidence."""
    with pytest.raises(ValueError, match="sampling_design_receipt_digest"):
        receipt(sampling_design_receipt_digest="not-a-digest")


def test_weight_eligibility_must_match_estimand_scope_population_duration_and_cases() -> None:
    """Reject cross-sectional/longitudinal or target-window mismatches before release."""
    with pytest.raises(ValueError, match="weight scope"):
        receipt(weight_eligibility=eligibility(weight_scope_code="longitudinal"))
    with pytest.raises(ValueError, match="target population"):
        receipt(weight_eligibility=eligibility(target_population_digest=DIGEST_A))
    with pytest.raises(ValueError, match="reference duration"):
        receipt(weight_eligibility=eligibility(reference_duration_digest=DIGEST_A))
    with pytest.raises(ValueError, match="eligible case set"):
        receipt(weight_eligibility=eligibility(eligible_case_set_digest=DIGEST_A))
    with pytest.raises(ValueError, match="final point-estimation weight artifact"):
        receipt(weight_eligibility=eligibility(weight_artifact_digest=DIGEST_D))


def test_longitudinal_weight_is_accepted_only_for_matching_longitudinal_estimand() -> None:
    """Allow longitudinal inference when population, duration, cases, and artifact all agree."""
    candidate = receipt(
        estimand_scope_code="longitudinal",
        weight_eligibility=eligibility(weight_scope_code="longitudinal"),
    )
    assert candidate.estimand_scope_code == "longitudinal"
    assert candidate.weight_eligibility.weight_scope_code == "longitudinal"


def test_positive_versions_and_counts_fail_closed() -> None:
    """Reject sentinel sequence, method-version, count, and correction values."""
    with pytest.raises(ValueError, match="sequence_number"):
        adjustment(sequence_number=0)
    with pytest.raises(ValueError, match="method_version"):
        adjustment(method_version=0)
    with pytest.raises(ValueError, match="analytic_case_count"):
        receipt(analytic_case_count=0)
    with pytest.raises(ValueError, match="correction_sequence"):
        receipt(correction_sequence=0)


def test_correction_lineage_is_append_only_and_canonicalized() -> None:
    """Require successor evidence rather than overwriting a prior weight receipt."""
    with pytest.raises(ValueError, match="supersedes_receipt_digest"):
        receipt(correction_sequence=2)
    with pytest.raises(ValueError, match="must be absent"):
        receipt(supersedes_receipt_digest=DIGEST_A)

    corrected = receipt(correction_sequence=2, supersedes_receipt_digest=DIGEST_A)
    assert f'"supersedes_receipt_digest":"{DIGEST_A}"' in corrected.canonical_json()


def test_evidence_version_is_not_caller_extensible() -> None:
    """Prevent callers from inventing a new receipt schema without a reviewed contract."""
    with pytest.raises(ValueError, match="evidence_version"):
        receipt(evidence_version=2)
