"""RED contract for versioned calibration auxiliary projection identity."""

from datetime import datetime, timedelta, timezone

import pytest

from orgmetra_validity_analysis import CalibrationAdjustmentReceipt

TENANT = "10000000-0000-7000-8000-000000000001"
NOW = datetime(2026, 9, 17, 5, 0, tzinfo=timezone.utc)


def receipt(**overrides: object) -> CalibrationAdjustmentReceipt:
    """Return one calibration receipt with an exact versioned auxiliary projection."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "receipt_reference": "calibration_adjustment_receipt:33333333-3333-4333-8333-333333333333",
        "target_population_digest": "a" * 64,
        "analysis_window_reference": "analysis_window:44444444-4444-4444-8444-444444444444",
        "auxiliary_authority_reference": "scientific_auxiliary_authority:55555555-5555-4555-8555-555555555550",
        "auxiliary_projection_reference": "calibration_auxiliary_projection:55555555-5555-4555-8555-555555555555",
        "auxiliary_projection_version": 4,
        "auxiliary_projection_digest": "b" * 64,
        "auxiliary_purpose_reference": "scientific_data_use_purpose:55555555-5555-4555-8555-555555555556",
        "auxiliary_purpose_digest": "3" * 64,
        "auxiliary_owner_contract_reference": "released_owner_contract:55555555-5555-4555-8555-555555555557",
        "auxiliary_owner_contract_version": 1,
        "auxiliary_owner_contract_digest": "1" * 64,
        "auxiliary_authorization_receipt_reference": "scientific_data_authorization:55555555-5555-4555-8555-555555555558",
        "auxiliary_authorization_receipt_digest": "4" * 64,
        "auxiliary_scientific_use_receipt_reference": "scientific_use_receipt:55555555-5555-4555-8555-555555555559",
        "auxiliary_scientific_use_receipt_digest": "2" * 64,
        "auxiliary_scientific_use_at": NOW,
        "benchmark_receipt_reference": "calibration_benchmark_receipt:66666666-6666-4666-8666-666666666666",
        "benchmark_receipt_version": 2,
        "benchmark_receipt_digest": "c" * 64,
        "benchmark_owner_contract_reference": "released_owner_contract:66666666-6666-4666-8666-666666666667",
        "benchmark_owner_contract_version": 3,
        "benchmark_owner_contract_digest": "5" * 64,
        "benchmark_reference_at": NOW - timedelta(days=1),
        "algorithm_reference": "calibration_algorithm:77777777-7777-4777-8777-777777777777",
        "algorithm_version": 1,
        "constraints_digest": "f" * 64,
        "termination_code": "converged",
        "input_weight_artifact_digest": "d" * 64,
        "output_weight_artifact_digest": "e" * 64,
        "constructed_at": NOW,
    }
    values.update(overrides)
    return CalibrationAdjustmentReceipt(**values)


def test_calibration_receipt_binds_projection_version_into_canonical_evidence() -> None:
    candidate = receipt()
    assert candidate.auxiliary_projection_version == 4
    assert '"auxiliary_projection_version":4' in candidate.canonical_json()


@pytest.mark.parametrize("invalid", [0, -1, True, "4", None])
def test_calibration_receipt_rejects_nonpositive_or_nonnumeric_projection_version(
    invalid: object,
) -> None:
    with pytest.raises(ValueError, match="auxiliary_projection_version"):
        receipt(auxiliary_projection_version=invalid)
