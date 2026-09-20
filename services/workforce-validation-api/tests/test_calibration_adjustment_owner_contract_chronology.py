"""Fail closed when calibration-adjustment owner contracts are retroactive."""

from __future__ import annotations

from datetime import datetime, timezone
from inspect import signature
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.calibration_adjustment_authority import (
    CalibrationAdjustmentAuthorityRecord,
    resolve_calibration_adjustment_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
CONSTRUCTED_AT = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 9, 16, 12, 30, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc)


def _record(**overrides: object) -> CalibrationAdjustmentAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "calibration_receipt_reference": (
            "calibration_adjustment_receipt:11111111-1111-4111-8111-111111111111"
        ),
        "calibration_receipt_digest": "1" * 64,
        "evidence_version": 1,
        "target_population_digest": "a" * 64,
        "analysis_window_reference": "analysis_window:2026q3",
        "auxiliary_authority_reference": (
            "scientific_auxiliary_authority:44444444-4444-4444-8444-444444444444"
        ),
        "auxiliary_projection_reference": (
            "calibration_auxiliary_projection:55555555-5555-4555-8555-555555555555"
        ),
        "auxiliary_projection_version": 2,
        "auxiliary_projection_digest": "2" * 64,
        "auxiliary_purpose_reference": (
            "scientific_data_use_purpose:66666666-6666-4666-8666-666666666666"
        ),
        "auxiliary_purpose_digest": "8" * 64,
        "auxiliary_owner_contract_reference": (
            "released_owner_contract:77777777-7777-4777-8777-777777777777"
        ),
        "auxiliary_owner_contract_version": 3,
        "auxiliary_owner_contract_digest": "9" * 64,
        "auxiliary_authorization_receipt_reference": (
            "scientific_data_authorization:88888888-8888-4888-8888-888888888888"
        ),
        "auxiliary_authorization_receipt_digest": "a" * 64,
        "auxiliary_scientific_use_receipt_reference": (
            "scientific_use_receipt:99999999-9999-4999-8999-999999999999"
        ),
        "auxiliary_scientific_use_receipt_digest": "b" * 64,
        "auxiliary_scientific_use_at": datetime(
            2026, 9, 16, 11, 0, tzinfo=timezone.utc
        ),
        "benchmark_receipt_reference": (
            "calibration_benchmark_receipt:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        ),
        "benchmark_receipt_version": 4,
        "benchmark_receipt_digest": "3" * 64,
        "benchmark_owner_contract_reference": (
            "released_owner_contract:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        ),
        "benchmark_owner_contract_version": 4,
        "benchmark_owner_contract_digest": "c" * 64,
        "benchmark_reference_at": datetime(2026, 9, 16, 11, 30, tzinfo=timezone.utc),
        "algorithm_reference": "calibration_algorithm:raking",
        "algorithm_version": 2,
        "constraints_digest": "4" * 64,
        "termination_code": "converged",
        "input_weight_artifact_digest": "5" * 64,
        "output_weight_artifact_digest": "6" * 64,
        "constructed_at": CONSTRUCTED_AT,
        "fallback_reason_code": None,
        "fallback_rule_reference": None,
        "fallback_rule_digest": None,
        "fallback_algorithm_reference": None,
        "fallback_algorithm_version": None,
        "fallback_configuration_digest": None,
        "owner_contract_reference": (
            "released_owner_contract:33333333-3333-4333-8333-333333333333"
        ),
        "owner_contract_version": 5,
        "owner_contract_digest": "7" * 64,
        "owner_contract_released_at": OWNER_CONTRACT_RELEASED_AT,
        "released_at": RELEASED_AT,
    }
    values.update(overrides)
    return CalibrationAdjustmentAuthorityRecord(**values)


def test_owner_contract_release_is_owner_resolved_not_a_request_coordinate() -> None:
    assert "owner_contract_released_at" not in signature(
        resolve_calibration_adjustment_authority
    ).parameters


def test_owner_contract_must_exist_before_calibration_receipt_release() -> None:
    with pytest.raises(ValueError, match="owner_contract_released_at"):
        _record(
            owner_contract_released_at=datetime(
                2026, 9, 16, 13, 0, 1, tzinfo=timezone.utc
            )
        )


def test_owner_contract_release_requires_timezone_aware_evidence() -> None:
    with pytest.raises(ValueError):
        _record(owner_contract_released_at=datetime(2026, 9, 16, 12, 30))


def test_contract_released_after_construction_but_before_receipt_release_is_valid() -> None:
    record = _record()
    assert record.owner_contract_released_at == OWNER_CONTRACT_RELEASED_AT
    assert record.released_at == RELEASED_AT
