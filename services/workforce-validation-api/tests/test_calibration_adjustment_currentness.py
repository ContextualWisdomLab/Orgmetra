"""Currentness contract for released typed calibration-adjustment evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.calibration_adjustment_authority import (
    CalibrationAdjustmentAuthorityIntegrityError,
    CalibrationAdjustmentAuthorityRecord,
    _READ_FIELDS,
    resolve_calibration_adjustment_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
RELEASED = datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc)
CUTOVER = datetime(2026, 9, 17, 13, 0, tzinfo=timezone.utc)


class _ReadPort:
    def __init__(self, record: CalibrationAdjustmentAuthorityRecord) -> None:
        self.record = record

    def read_calibration_adjustment_authority(
        self, **_: object
    ) -> CalibrationAdjustmentAuthorityRecord:
        return self.record


def _record(**overrides: object) -> CalibrationAdjustmentAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "calibration_receipt_reference": "calibration_adjustment_receipt:11111111-1111-4111-8111-111111111111",
        "calibration_receipt_digest": "1" * 64,
        "evidence_version": 1,
        "target_population_digest": "2" * 64,
        "analysis_window_reference": "analysis_window:2026q3",
        "auxiliary_authority_reference": "scientific_auxiliary_authority:33333333-3333-4333-8333-333333333333",
        "auxiliary_projection_reference": "calibration_auxiliary_projection:44444444-4444-4444-8444-444444444444",
        "auxiliary_projection_version": 1,
        "auxiliary_projection_digest": "3" * 64,
        "auxiliary_purpose_reference": "scientific_data_use_purpose:55555555-5555-4555-8555-555555555555",
        "auxiliary_purpose_digest": "4" * 64,
        "auxiliary_owner_contract_reference": "released_owner_contract:66666666-6666-4666-8666-666666666666",
        "auxiliary_owner_contract_version": 1,
        "auxiliary_owner_contract_digest": "5" * 64,
        "auxiliary_authorization_receipt_reference": "scientific_data_authorization:77777777-7777-4777-8777-777777777777",
        "auxiliary_authorization_receipt_digest": "6" * 64,
        "auxiliary_scientific_use_receipt_reference": "scientific_use_receipt:88888888-8888-4888-8888-888888888888",
        "auxiliary_scientific_use_receipt_digest": "7" * 64,
        "auxiliary_scientific_use_at": datetime(2026, 9, 16, 11, 0, tzinfo=timezone.utc),
        "benchmark_receipt_reference": "calibration_benchmark_receipt:99999999-9999-4999-8999-999999999999",
        "benchmark_receipt_version": 1,
        "benchmark_receipt_digest": "8" * 64,
        "benchmark_owner_contract_reference": "released_owner_contract:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "benchmark_owner_contract_version": 1,
        "benchmark_owner_contract_digest": "9" * 64,
        "benchmark_reference_at": datetime(2026, 9, 16, 11, 30, tzinfo=timezone.utc),
        "algorithm_reference": "calibration_algorithm:generalized_regression",
        "algorithm_version": 1,
        "constraints_digest": "a" * 64,
        "termination_code": "converged",
        "input_weight_artifact_digest": "b" * 64,
        "output_weight_artifact_digest": "c" * 64,
        "constructed_at": datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc),
        "fallback_reason_code": None,
        "fallback_rule_reference": None,
        "fallback_rule_digest": None,
        "fallback_algorithm_reference": None,
        "fallback_algorithm_version": None,
        "fallback_configuration_digest": None,
        "owner_contract_reference": "released_owner_contract:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "owner_contract_version": 1,
        "owner_contract_digest": "d" * 64,
        "owner_contract_released_at": datetime(2026, 9, 16, 12, 30, tzinfo=timezone.utc),
        "released_at": RELEASED,
        "superseded_at": CUTOVER,
    }
    values.update(overrides)
    return CalibrationAdjustmentAuthorityRecord(**values)


def _resolve(record: CalibrationAdjustmentAuthorityRecord, *, used_at: datetime) -> None:
    resolve_calibration_adjustment_authority(
        principal=ValidationPrincipal(
            tenant_record_id=TENANT,
            actor_reference="person:validation-analyst-1",
            granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
        ),
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        calibration_receipt_reference=record.calibration_receipt_reference,
        calibration_receipt_digest=record.calibration_receipt_digest,
        evidence_version=record.evidence_version,
        target_population_digest=record.target_population_digest,
        analysis_window_reference=record.analysis_window_reference,
        auxiliary_authority_reference=record.auxiliary_authority_reference,
        auxiliary_projection_reference=record.auxiliary_projection_reference,
        auxiliary_projection_version=record.auxiliary_projection_version,
        auxiliary_projection_digest=record.auxiliary_projection_digest,
        auxiliary_purpose_reference=record.auxiliary_purpose_reference,
        auxiliary_purpose_digest=record.auxiliary_purpose_digest,
        auxiliary_owner_contract_reference=record.auxiliary_owner_contract_reference,
        auxiliary_owner_contract_version=record.auxiliary_owner_contract_version,
        auxiliary_owner_contract_digest=record.auxiliary_owner_contract_digest,
        auxiliary_authorization_receipt_reference=record.auxiliary_authorization_receipt_reference,
        auxiliary_authorization_receipt_digest=record.auxiliary_authorization_receipt_digest,
        auxiliary_scientific_use_receipt_reference=record.auxiliary_scientific_use_receipt_reference,
        auxiliary_scientific_use_receipt_digest=record.auxiliary_scientific_use_receipt_digest,
        auxiliary_scientific_use_at=record.auxiliary_scientific_use_at,
        benchmark_receipt_reference=record.benchmark_receipt_reference,
        benchmark_receipt_version=record.benchmark_receipt_version,
        benchmark_receipt_digest=record.benchmark_receipt_digest,
        benchmark_owner_contract_reference=record.benchmark_owner_contract_reference,
        benchmark_owner_contract_version=record.benchmark_owner_contract_version,
        benchmark_owner_contract_digest=record.benchmark_owner_contract_digest,
        benchmark_reference_at=record.benchmark_reference_at,
        algorithm_reference=record.algorithm_reference,
        algorithm_version=record.algorithm_version,
        constraints_digest=record.constraints_digest,
        termination_code=record.termination_code,
        input_weight_artifact_digest=record.input_weight_artifact_digest,
        output_weight_artifact_digest=record.output_weight_artifact_digest,
        constructed_at=record.constructed_at,
        fallback_reason_code=record.fallback_reason_code,
        fallback_rule_reference=record.fallback_rule_reference,
        fallback_rule_digest=record.fallback_rule_digest,
        fallback_algorithm_reference=record.fallback_algorithm_reference,
        fallback_algorithm_version=record.fallback_algorithm_version,
        fallback_configuration_digest=record.fallback_configuration_digest,
        owner_contract_reference=record.owner_contract_reference,
        owner_contract_version=record.owner_contract_version,
        owner_contract_digest=record.owner_contract_digest,
        used_at=used_at,
        purpose_code="selection_validity_analysis",
        policy=PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="calibration-adjustment-authority-read-v1",
            resource_kind="calibration_adjustment_authority",
            purpose_code="selection_validity_analysis",
            operation_code="read",
            required_scope_code="orgmetra.workforce_validation.read",
            permitted_fields=_READ_FIELDS,
        ),
        read_port=_ReadPort(record),
    )


def test_supersession_cutover_is_owner_resolved_and_half_open() -> None:
    record = _record()
    _resolve(record, used_at=CUTOVER - timedelta(microseconds=1))

    with pytest.raises(CalibrationAdjustmentAuthorityIntegrityError, match="superseded"):
        _resolve(record, used_at=CUTOVER)


def test_superseded_at_requires_timezone_and_post_release_cutover() -> None:
    with pytest.raises(ValueError):
        _record(superseded_at=datetime(2026, 9, 17, 13, 0))

    with pytest.raises(ValueError, match="later than released_at"):
        _record(superseded_at=RELEASED)
