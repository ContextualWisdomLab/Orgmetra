"""Regression contract for exact auxiliary and benchmark identity in calibration evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from inspect import signature
from uuid import UUID

from orgmetra_workforce_validation_api.calibration_adjustment_authority import (
    CalibrationAdjustmentAuthorityReadPort,
    CalibrationAdjustmentAuthorityRecord,
    resolve_calibration_adjustment_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000f2")
CONSTRUCTED_AT = datetime(2026, 9, 17, 9, 0, tzinfo=timezone.utc)
OWNER_RELEASED_AT = datetime(2026, 9, 17, 9, 10, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 9, 30, tzinfo=timezone.utc)
SUPPORTING_FIELDS = (
    "auxiliary_authority_reference",
    "auxiliary_projection_reference",
    "auxiliary_projection_version",
    "auxiliary_purpose_reference",
    "auxiliary_purpose_digest",
    "auxiliary_owner_contract_reference",
    "auxiliary_owner_contract_version",
    "auxiliary_owner_contract_digest",
    "auxiliary_authorization_receipt_reference",
    "auxiliary_authorization_receipt_digest",
    "auxiliary_scientific_use_receipt_reference",
    "auxiliary_scientific_use_receipt_digest",
    "auxiliary_scientific_use_at",
    "benchmark_receipt_reference",
    "benchmark_receipt_version",
    "benchmark_owner_contract_reference",
    "benchmark_owner_contract_version",
    "benchmark_owner_contract_digest",
    "benchmark_reference_at",
)


def _record() -> CalibrationAdjustmentAuthorityRecord:
    """Build the complete leaf-semantic calibration authority projection."""
    return CalibrationAdjustmentAuthorityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        calibration_receipt_reference=(
            "calibration_adjustment_receipt:11111111-1111-4111-8111-111111111111"
        ),
        calibration_receipt_digest="1" * 64,
        evidence_version=1,
        target_population_digest="2" * 64,
        analysis_window_reference="analysis_window:2026q3",
        auxiliary_authority_reference=(
            "scientific_auxiliary_authority:22222222-2222-4222-8222-222222222222"
        ),
        auxiliary_projection_reference=(
            "calibration_auxiliary_projection:33333333-3333-4333-8333-333333333333"
        ),
        auxiliary_projection_version=3,
        auxiliary_projection_digest="3" * 64,
        auxiliary_purpose_reference=(
            "scientific_data_use_purpose:44444444-4444-4444-8444-444444444444"
        ),
        auxiliary_purpose_digest="4" * 64,
        auxiliary_owner_contract_reference=(
            "released_owner_contract:55555555-5555-4555-8555-555555555555"
        ),
        auxiliary_owner_contract_version=5,
        auxiliary_owner_contract_digest="5" * 64,
        auxiliary_authorization_receipt_reference=(
            "scientific_data_authorization:66666666-6666-4666-8666-666666666666"
        ),
        auxiliary_authorization_receipt_digest="6" * 64,
        auxiliary_scientific_use_receipt_reference=(
            "scientific_use_receipt:77777777-7777-4777-8777-777777777777"
        ),
        auxiliary_scientific_use_receipt_digest="7" * 64,
        auxiliary_scientific_use_at=datetime(2026, 9, 17, 8, 30, tzinfo=timezone.utc),
        benchmark_receipt_reference=(
            "calibration_benchmark_receipt:88888888-8888-4888-8888-888888888888"
        ),
        benchmark_receipt_version=8,
        benchmark_receipt_digest="8" * 64,
        benchmark_owner_contract_reference=(
            "released_owner_contract:99999999-9999-4999-8999-999999999999"
        ),
        benchmark_owner_contract_version=9,
        benchmark_owner_contract_digest="9" * 64,
        benchmark_reference_at=datetime(2026, 9, 17, 8, 45, tzinfo=timezone.utc),
        algorithm_reference="calibration_algorithm:generalized_regression",
        algorithm_version=3,
        constraints_digest="a" * 64,
        termination_code="converged",
        input_weight_artifact_digest="b" * 64,
        output_weight_artifact_digest="c" * 64,
        constructed_at=CONSTRUCTED_AT,
        fallback_reason_code=None,
        fallback_rule_reference=None,
        fallback_rule_digest=None,
        fallback_algorithm_reference=None,
        fallback_algorithm_version=None,
        fallback_configuration_digest=None,
        owner_contract_reference=(
            "released_owner_contract:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        ),
        owner_contract_version=10,
        owner_contract_digest="d" * 64,
        owner_contract_released_at=OWNER_RELEASED_AT,
        released_at=RELEASED_AT,
    )


def test_calibration_authority_preserves_exact_supporting_evidence_identity() -> None:
    """Do not collapse calibration auxiliary/benchmark provenance to digest-only labels."""
    record = _record()
    read_parameters = signature(
        CalibrationAdjustmentAuthorityReadPort.read_calibration_adjustment_authority
    ).parameters
    resolver_parameters = signature(resolve_calibration_adjustment_authority).parameters

    for field_name in SUPPORTING_FIELDS:
        assert hasattr(record, field_name)
        assert field_name in read_parameters
        assert field_name in resolver_parameters

    assert record.auxiliary_projection_reference.startswith("calibration_auxiliary_projection:")
    assert record.benchmark_receipt_reference.startswith("calibration_benchmark_receipt:")
    assert record.auxiliary_scientific_use_at <= record.constructed_at
    assert record.benchmark_reference_at <= record.constructed_at
