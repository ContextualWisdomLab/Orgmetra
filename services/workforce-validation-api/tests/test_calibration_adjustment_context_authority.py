"""Regression contract for calibration target-population and analysis-window authority."""

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
STUDY = UUID("00000000-0000-7000-8000-0000000000f1")
CONSTRUCTED_AT = datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc)
OWNER_RELEASED_AT = datetime(2026, 9, 17, 8, 10, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 8, 30, tzinfo=timezone.utc)
TARGET_POPULATION_DIGEST = "a" * 64
ANALYSIS_WINDOW_REFERENCE = "analysis_window:2026q3"


def _record() -> CalibrationAdjustmentAuthorityRecord:
    """Build one released calibration authority with explicit analysis context."""
    return CalibrationAdjustmentAuthorityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        calibration_receipt_reference=(
            "calibration_adjustment_receipt:11111111-1111-4111-8111-111111111111"
        ),
        calibration_receipt_digest="1" * 64,
        evidence_version=1,
        target_population_digest=TARGET_POPULATION_DIGEST,
        analysis_window_reference=ANALYSIS_WINDOW_REFERENCE,
        auxiliary_projection_digest="2" * 64,
        benchmark_receipt_digest="3" * 64,
        algorithm_reference="calibration_algorithm:linear-raking",
        algorithm_version=1,
        constraints_digest="4" * 64,
        termination_code="converged",
        input_weight_artifact_digest="5" * 64,
        output_weight_artifact_digest="6" * 64,
        constructed_at=CONSTRUCTED_AT,
        fallback_reason_code=None,
        fallback_rule_reference=None,
        fallback_rule_digest=None,
        fallback_algorithm_reference=None,
        fallback_algorithm_version=None,
        fallback_configuration_digest=None,
        owner_contract_reference=(
            "released_owner_contract:22222222-2222-4222-8222-222222222222"
        ),
        owner_contract_version=1,
        owner_contract_digest="7" * 64,
        owner_contract_released_at=OWNER_RELEASED_AT,
        released_at=RELEASED_AT,
    )


def test_calibration_authority_binds_target_population_and_analysis_window() -> None:
    """Keep the scientific leaf's population/window semantics in owner corroboration."""
    record = _record()

    assert record.target_population_digest == TARGET_POPULATION_DIGEST
    assert record.analysis_window_reference == ANALYSIS_WINDOW_REFERENCE

    read_parameters = signature(
        CalibrationAdjustmentAuthorityReadPort.read_calibration_adjustment_authority
    ).parameters
    resolver_parameters = signature(resolve_calibration_adjustment_authority).parameters
    for field_name in ("target_population_digest", "analysis_window_reference"):
        assert field_name in read_parameters
        assert field_name in resolver_parameters

    for owner_resolved_field in ("owner_contract_released_at", "released_at"):
        assert owner_resolved_field not in read_parameters
        assert owner_resolved_field not in resolver_parameters
