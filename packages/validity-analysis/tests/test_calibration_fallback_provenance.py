"""Regression contracts for explicit calibration fallback provenance."""

from datetime import datetime, timedelta, timezone

import pytest

from orgmetra_validity_analysis import CalibrationAdjustmentReceipt

TENANT = "10000000-0000-7000-8000-000000000001"
NOW = datetime(2026, 9, 17, 7, 0, tzinfo=timezone.utc)
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


def calibration_receipt(**overrides: object) -> CalibrationAdjustmentReceipt:
    """Return one fallback-bearing calibration receipt for focused provenance checks."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "receipt_reference": "calibration_adjustment_receipt:33333333-3333-4333-8333-333333333333",
        "target_population_digest": DIGEST_A,
        "analysis_window_reference": "analysis_window:44444444-4444-4444-8444-444444444444",
        "auxiliary_authority_reference": "scientific_auxiliary_authority:55555555-5555-4555-8555-555555555550",
        "auxiliary_projection_reference": "calibration_auxiliary_projection:55555555-5555-4555-8555-555555555555",
        "auxiliary_projection_version": 4,
        "auxiliary_projection_digest": DIGEST_B,
        "auxiliary_purpose_reference": "scientific_data_use_purpose:55555555-5555-4555-8555-555555555556",
        "auxiliary_purpose_digest": DIGEST_3,
        "auxiliary_owner_contract_reference": "released_owner_contract:55555555-5555-4555-8555-555555555557",
        "auxiliary_owner_contract_version": 1,
        "auxiliary_owner_contract_digest": DIGEST_1,
        "auxiliary_authorization_receipt_reference": "scientific_data_authorization:55555555-5555-4555-8555-555555555558",
        "auxiliary_authorization_receipt_digest": DIGEST_4,
        "auxiliary_scientific_use_receipt_reference": "scientific_use_receipt:55555555-5555-4555-8555-555555555559",
        "auxiliary_scientific_use_receipt_digest": DIGEST_2,
        "auxiliary_scientific_use_at": NOW,
        "benchmark_receipt_reference": "calibration_benchmark_receipt:66666666-6666-4666-8666-666666666666",
        "benchmark_receipt_version": 2,
        "benchmark_receipt_digest": DIGEST_C,
        "benchmark_owner_contract_reference": "released_owner_contract:66666666-6666-4666-8666-666666666667",
        "benchmark_owner_contract_version": 3,
        "benchmark_owner_contract_digest": DIGEST_5,
        "benchmark_reference_at": NOW - timedelta(days=1),
        "algorithm_reference": "calibration_algorithm:77777777-7777-4777-8777-777777777777",
        "algorithm_version": 1,
        "constraints_digest": DIGEST_F,
        "termination_code": "fallback_applied",
        "fallback_reason_code": "primary_nonconvergence",
        "fallback_rule_reference": "calibration_fallback_rule:99999999-9999-4999-8999-999999999999",
        "fallback_rule_digest": DIGEST_2,
        "fallback_algorithm_reference": "calibration_algorithm:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "fallback_algorithm_version": 2,
        "fallback_configuration_digest": DIGEST_4,
        "input_weight_artifact_digest": DIGEST_D,
        "output_weight_artifact_digest": DIGEST_E,
        "constructed_at": NOW,
    }
    values.update(overrides)
    return CalibrationAdjustmentReceipt(**values)


def test_fallback_identifies_reason_rule_and_algorithm_that_produced_weights() -> None:
    """Do not label fallback output as if the primary calibration algorithm succeeded."""
    candidate = calibration_receipt()
    canonical = candidate.canonical_json()

    assert '"termination_code":"fallback_applied"' in canonical
    assert '"fallback_reason_code":"primary_nonconvergence"' in canonical
    assert '"fallback_algorithm_reference":"calibration_algorithm:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"' in canonical
    assert '"fallback_algorithm_version":2' in canonical
    assert f'"fallback_configuration_digest":"{DIGEST_4}"' in canonical
    assert f'"fallback_rule_digest":"{DIGEST_2}"' in canonical


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("fallback_reason_code", None),
        ("fallback_rule_reference", None),
        ("fallback_rule_digest", None),
        ("fallback_algorithm_reference", None),
        ("fallback_algorithm_version", None),
        ("fallback_configuration_digest", None),
    ],
)
def test_fallback_rejects_incomplete_actual_method_provenance(
    field_name: str,
    value: object,
) -> None:
    """A fallback needs the actual generating method, not only an opaque fallback flag."""
    with pytest.raises((TypeError, ValueError), match="fallback"):
        calibration_receipt(**{field_name: value})


def test_converged_calibration_rejects_fallback_only_fields() -> None:
    """Fallback evidence must not contaminate a genuinely converged primary algorithm."""
    with pytest.raises(ValueError, match="fallback"):
        calibration_receipt(termination_code="converged")
