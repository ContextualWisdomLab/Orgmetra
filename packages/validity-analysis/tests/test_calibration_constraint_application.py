"""RED contracts for reviewed versus actually applied calibration constraints."""

from dataclasses import fields
from datetime import datetime, timedelta, timezone

import pytest

from orgmetra_validity_analysis import CalibrationAdjustmentReceipt

TENANT = "10000000-0000-7000-8000-000000000001"
NOW = datetime(2026, 9, 18, 3, 30, tzinfo=timezone.utc)
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


def _receipt(**overrides: object) -> CalibrationAdjustmentReceipt:
    """Build one calibration receipt with separate reviewed and applied constraints."""
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
        "applied_constraints_digest": DIGEST_F,
        "termination_code": "converged",
        "input_weight_artifact_digest": DIGEST_D,
        "output_weight_artifact_digest": DIGEST_E,
        "constructed_at": NOW,
    }
    values.update(overrides)
    return CalibrationAdjustmentReceipt(**values)


def test_calibration_receipt_exposes_actual_applied_constraints() -> None:
    """A reviewed constraint set and the generating constraint set must be distinct fields."""
    assert "applied_constraints_digest" in {
        field.name for field in fields(CalibrationAdjustmentReceipt)
    }


def test_primary_convergence_rejects_silent_constraint_relaxation() -> None:
    """Changed generating constraints require explicit fallback provenance."""
    with pytest.raises(ValueError, match="fallback"):
        _receipt(applied_constraints_digest=DIGEST_1)


def test_fallback_commits_to_reviewed_and_applied_constraint_sets() -> None:
    """A fallback may change constraints only when its generating path is explicit."""
    candidate = _receipt(
        termination_code="fallback_applied",
        applied_constraints_digest=DIGEST_1,
        fallback_reason_code="constraint_relaxation",
        fallback_rule_reference="calibration_fallback_rule:99999999-9999-4999-8999-999999999999",
        fallback_rule_digest=DIGEST_2,
        fallback_algorithm_reference="calibration_algorithm:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        fallback_algorithm_version=2,
        fallback_configuration_digest=DIGEST_4,
    )
    payload = candidate.canonical_json()

    assert f'"constraints_digest":"{DIGEST_F}"' in payload
    assert f'"applied_constraints_digest":"{DIGEST_1}"' in payload
