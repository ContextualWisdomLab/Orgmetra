"""Scientific contracts for nonresponse and calibration weight adjustments."""

from datetime import datetime, timezone

import pytest

from orgmetra_validity_analysis import (
    AnalysisWeightAdjustment,
    CalibrationAdjustmentReceipt,
    NonresponseAdjustmentReceipt,
)

TENANT = "10000000-0000-7000-8000-000000000001"
NOW = datetime(2026, 9, 17, 5, 0, tzinfo=timezone.utc)
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


def nonresponse_receipt(**overrides: object) -> NonresponseAdjustmentReceipt:
    """Return one disposition-aware nonresponse adjustment receipt."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "receipt_reference": "nonresponse_adjustment_receipt:11111111-1111-4111-8111-111111111111",
        "response_disposition_receipt_digest": DIGEST_A,
        "adjustment_population_digest": DIGEST_B,
        "method_reference": "weight_method:22222222-2222-4222-8222-222222222222",
        "method_version": 1,
        "configuration_digest": DIGEST_C,
        "ineligible_treatment_code": "exclude_as_ineligible",
        "unknown_treatment_code": "retain_in_unknown_class",
        "unavailable_treatment_code": "retain_in_unavailable_class",
        "input_weight_artifact_digest": DIGEST_D,
        "output_weight_artifact_digest": DIGEST_E,
        "constructed_at": NOW,
    }
    values.update(overrides)
    return NonresponseAdjustmentReceipt(**values)


def calibration_receipt(**overrides: object) -> CalibrationAdjustmentReceipt:
    """Return one benchmark-bound converged calibration receipt."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "receipt_reference": "calibration_adjustment_receipt:33333333-3333-4333-8333-333333333333",
        "target_population_digest": DIGEST_A,
        "analysis_window_reference": "analysis_window:44444444-4444-4444-8444-444444444444",
        "auxiliary_projection_reference": "calibration_auxiliary_projection:55555555-5555-4555-8555-555555555555",
        "auxiliary_projection_digest": DIGEST_B,
        "benchmark_receipt_reference": "calibration_benchmark_receipt:66666666-6666-4666-8666-666666666666",
        "benchmark_receipt_digest": DIGEST_C,
        "algorithm_reference": "calibration_algorithm:77777777-7777-4777-8777-777777777777",
        "algorithm_version": 1,
        "constraints_digest": DIGEST_F,
        "termination_code": "converged",
        "input_weight_artifact_digest": DIGEST_D,
        "output_weight_artifact_digest": DIGEST_E,
        "constructed_at": NOW,
    }
    values.update(overrides)
    return CalibrationAdjustmentReceipt(**values)


def adjustment(*, code: str, evidence_kind: str) -> AnalysisWeightAdjustment:
    """Return one adjustment linked to typed scientific evidence."""
    return AnalysisWeightAdjustment(
        sequence_number=1,
        adjustment_code=code,
        method_reference="weight_method:88888888-8888-4888-8888-888888888888",
        method_version=1,
        input_weight_artifact_digest=DIGEST_D,
        output_weight_artifact_digest=DIGEST_E,
        configuration_digest=DIGEST_F,
        evidence_receipt_digest=DIGEST_1,
        evidence_kind=evidence_kind,
    )


def test_nonresponse_receipt_is_value_minimized_and_disposition_aware() -> None:
    """Preserve explicit disposition treatment without copying source attributes."""
    candidate = nonresponse_receipt()
    assert candidate.sha256_digest() == nonresponse_receipt().sha256_digest()
    assert '"unknown_treatment_code":"retain_in_unknown_class"' in candidate.canonical_json()
    assert "person_record" not in candidate.canonical_json()
    assert "protected_attribute" not in candidate.canonical_json()
    assert repr(candidate) == "NonresponseAdjustmentReceipt(<redacted>)"

    with pytest.raises(ValueError, match="unknown_treatment_code"):
        nonresponse_receipt(unknown_treatment_code="")
    with pytest.raises(ValueError, match="output_weight_artifact_digest"):
        nonresponse_receipt(output_weight_artifact_digest=DIGEST_D)
    with pytest.raises(ValueError, match="evidence_version"):
        nonresponse_receipt(evidence_version=2)
    with pytest.raises(ValueError, match="evidence_version"):
        nonresponse_receipt(evidence_version=True)


def test_calibration_receipt_binds_owner_benchmark_and_termination_state() -> None:
    """Keep benchmark ownership and fallback semantics explicit and immutable."""
    candidate = calibration_receipt()
    assert candidate.sha256_digest() == calibration_receipt().sha256_digest()
    assert f'"benchmark_receipt_digest":"{DIGEST_C}"' in candidate.canonical_json()
    assert '"termination_code":"converged"' in candidate.canonical_json()
    assert repr(candidate) == "CalibrationAdjustmentReceipt(<redacted>)"

    fallback_reference = "calibration_fallback_rule:99999999-9999-4999-8999-999999999999"
    fallback = calibration_receipt(
        termination_code="fallback_applied",
        fallback_rule_reference=fallback_reference,
        fallback_rule_digest=DIGEST_2,
    )
    assert f'"fallback_rule_digest":"{DIGEST_2}"' in fallback.canonical_json()

    with pytest.raises(ValueError, match="termination_code"):
        calibration_receipt(termination_code="failed")
    with pytest.raises(ValueError, match="termination_code"):
        calibration_receipt(termination_code=1)
    with pytest.raises(ValueError, match="fallback_rule"):
        calibration_receipt(termination_code="fallback_applied")
    with pytest.raises(ValueError, match="fallback_rule"):
        calibration_receipt(
            termination_code="fallback_applied",
            fallback_rule_reference=fallback_reference,
        )
    with pytest.raises(ValueError, match="must be absent"):
        calibration_receipt(
            fallback_rule_reference=fallback_reference,
            fallback_rule_digest=DIGEST_2,
        )
    with pytest.raises(ValueError, match="must be absent"):
        calibration_receipt(fallback_rule_digest=DIGEST_2)
    with pytest.raises(ValueError, match="output_weight_artifact_digest"):
        calibration_receipt(output_weight_artifact_digest=DIGEST_D)
    with pytest.raises(ValueError, match="evidence_version"):
        calibration_receipt(evidence_version=2)
    with pytest.raises(ValueError, match="evidence_version"):
        calibration_receipt(evidence_version=True)


def test_specialized_adjustments_require_matching_evidence_kind() -> None:
    """Do not let typed nonresponse or calibration semantics collapse into opaque digests."""
    nonresponse = adjustment(
        code="nonresponse_adjustment",
        evidence_kind="nonresponse_adjustment_receipt",
    )
    calibration = adjustment(
        code="calibration_adjustment",
        evidence_kind="calibration_adjustment_receipt",
    )
    assert nonresponse.evidence_kind == "nonresponse_adjustment_receipt"
    assert calibration.evidence_kind == "calibration_adjustment_receipt"

    with pytest.raises(ValueError, match="nonresponse_adjustment_receipt"):
        adjustment(code="nonresponse_adjustment", evidence_kind="generic_adjustment_receipt")
    with pytest.raises(ValueError, match="calibration_adjustment_receipt"):
        adjustment(code="raking_adjustment", evidence_kind="generic_adjustment_receipt")

    generic = adjustment(code="trimming_adjustment", evidence_kind="generic_adjustment_receipt")
    assert generic.evidence_kind == "generic_adjustment_receipt"
