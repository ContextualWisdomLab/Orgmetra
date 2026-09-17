"""Reject retroactive owner contracts and stale final analysis-weight use."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from inspect import signature
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.final_weight_authority import (
    FinalAnalysisWeightAuthorityIntegrityError,
    FinalAnalysisWeightAuthorityRecord,
    FinalWeightAdjustmentCoordinate,
    resolve_final_analysis_weight_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000f1")
WEIGHT_RECEIPT_REFERENCE = "analysis_weight_receipt:11111111-1111-4111-8111-111111111111"
ESTIMAND_REFERENCE = "validation_estimand:criterion-validity-q3"
TARGET_REFERENCE = "analysis_target_population:workers-2026q3"
WINDOW_REFERENCE = "analysis_window:2026q3"
DURATION_REFERENCE = "analysis_reference_duration:2026q3"
SOURCE_REFERENCE = "source_universe_receipt:22222222-2222-4222-8222-222222222222"
SAMPLING_REFERENCE = "sampling_design_receipt:33333333-3333-4333-8333-333333333333"
ELIGIBILITY_REFERENCE = "weight_eligibility_receipt:44444444-4444-4444-8444-444444444444"
OWNER_REFERENCE = "released_owner_contract:55555555-5555-4555-8555-555555555555"
METHOD_REFERENCE = "weight_method:nonresponse-cell-adjustment"
WEIGHT_RECEIPT_DIGEST = "1" * 64
ESTIMAND_DIGEST = "2" * 64
TARGET_DIGEST = "3" * 64
DURATION_DIGEST = "4" * 64
ELIGIBLE_CASE_DIGEST = "5" * 64
ANALYTIC_CASE_DIGEST = "6" * 64
SOURCE_DIGEST = "7" * 64
SAMPLING_DIGEST = "8" * 64
BASE_EVIDENCE_DIGEST = "9" * 64
BASE_ARTIFACT_DIGEST = "a" * 64
ADJUSTED_ARTIFACT_DIGEST = "b" * 64
ADJUSTMENT_CONFIG_DIGEST = "c" * 64
ADJUSTMENT_RECEIPT_DIGEST = "d" * 64
ELIGIBILITY_DIGEST = "e" * 64
OWNER_DIGEST = "f" * 64
CONSTRUCTED_AT = datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc)
OWNER_RELEASED_AT = datetime(2026, 9, 17, 8, 10, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 8, 30, tzinfo=timezone.utc)
SUPERSEDED_AT = datetime(2026, 9, 17, 10, 0, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "analysis_weight_receipt_reference",
        "analysis_weight_receipt_digest",
        "evidence_version",
        "estimand_reference",
        "estimand_digest",
        "estimand_scope_code",
        "target_population_reference",
        "target_population_digest",
        "analysis_unit_code",
        "analysis_window_reference",
        "reference_duration_reference",
        "reference_duration_digest",
        "eligible_case_set_digest",
        "analytic_case_occurrence_set_digest",
        "source_universe_receipt_reference",
        "source_universe_receipt_version",
        "source_universe_receipt_digest",
        "sampling_design_receipt_reference",
        "sampling_design_receipt_version",
        "sampling_design_receipt_digest",
        "base_weight_method_code",
        "base_weight_method_version",
        "base_weight_evidence_digest",
        "base_weight_artifact_digest",
        "adjustments",
        "final_weight_artifact_digest",
        "weight_eligibility_receipt_reference",
        "weight_eligibility_receipt_digest",
        "analytic_case_count",
        "constructed_at",
        "correction_sequence",
        "supersedes_receipt_digest",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
    }
)


class _ReadPort:
    def __init__(self, record: FinalAnalysisWeightAuthorityRecord) -> None:
        self.record = record

    def read_final_analysis_weight_authority(self, **_: object) -> FinalAnalysisWeightAuthorityRecord:
        return self.record


def _adjustment() -> FinalWeightAdjustmentCoordinate:
    return FinalWeightAdjustmentCoordinate(
        sequence_number=1,
        adjustment_code="nonresponse_adjustment",
        method_reference=METHOD_REFERENCE,
        method_version=2,
        input_weight_artifact_digest=BASE_ARTIFACT_DIGEST,
        output_weight_artifact_digest=ADJUSTED_ARTIFACT_DIGEST,
        configuration_digest=ADJUSTMENT_CONFIG_DIGEST,
        evidence_receipt_digest=ADJUSTMENT_RECEIPT_DIGEST,
        evidence_kind="nonresponse_adjustment_receipt",
    )


def _record(**overrides: object) -> FinalAnalysisWeightAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "analysis_weight_receipt_reference": WEIGHT_RECEIPT_REFERENCE,
        "analysis_weight_receipt_digest": WEIGHT_RECEIPT_DIGEST,
        "evidence_version": 1,
        "estimand_reference": ESTIMAND_REFERENCE,
        "estimand_digest": ESTIMAND_DIGEST,
        "estimand_scope_code": "longitudinal",
        "target_population_reference": TARGET_REFERENCE,
        "target_population_digest": TARGET_DIGEST,
        "analysis_unit_code": "person_occurrence",
        "analysis_window_reference": WINDOW_REFERENCE,
        "reference_duration_reference": DURATION_REFERENCE,
        "reference_duration_digest": DURATION_DIGEST,
        "eligible_case_set_digest": ELIGIBLE_CASE_DIGEST,
        "analytic_case_occurrence_set_digest": ANALYTIC_CASE_DIGEST,
        "source_universe_receipt_reference": SOURCE_REFERENCE,
        "source_universe_receipt_version": 4,
        "source_universe_receipt_digest": SOURCE_DIGEST,
        "sampling_design_receipt_reference": SAMPLING_REFERENCE,
        "sampling_design_receipt_version": 3,
        "sampling_design_receipt_digest": SAMPLING_DIGEST,
        "base_weight_method_code": "inverse_inclusion_probability",
        "base_weight_method_version": 1,
        "base_weight_evidence_digest": BASE_EVIDENCE_DIGEST,
        "base_weight_artifact_digest": BASE_ARTIFACT_DIGEST,
        "adjustments": (_adjustment(),),
        "final_weight_artifact_digest": ADJUSTED_ARTIFACT_DIGEST,
        "weight_eligibility_receipt_reference": ELIGIBILITY_REFERENCE,
        "weight_eligibility_receipt_digest": ELIGIBILITY_DIGEST,
        "analytic_case_count": 1200,
        "constructed_at": CONSTRUCTED_AT,
        "correction_sequence": 1,
        "supersedes_receipt_digest": None,
        "owner_contract_reference": OWNER_REFERENCE,
        "owner_contract_version": 7,
        "owner_contract_digest": OWNER_DIGEST,
        "owner_contract_released_at": OWNER_RELEASED_AT,
        "released_at": RELEASED_AT,
        "superseded_at": SUPERSEDED_AT,
    }
    values.update(overrides)
    return FinalAnalysisWeightAuthorityRecord(**values)


def _resolve(*, used_at: datetime, record: FinalAnalysisWeightAuthorityRecord) -> object:
    return resolve_final_analysis_weight_authority(
        principal=ValidationPrincipal(
            tenant_record_id=TENANT,
            actor_reference="person:validation-analyst-1",
            granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
        ),
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        analysis_weight_receipt_reference=WEIGHT_RECEIPT_REFERENCE,
        analysis_weight_receipt_digest=WEIGHT_RECEIPT_DIGEST,
        evidence_version=1,
        estimand_reference=ESTIMAND_REFERENCE,
        estimand_digest=ESTIMAND_DIGEST,
        estimand_scope_code="longitudinal",
        target_population_reference=TARGET_REFERENCE,
        target_population_digest=TARGET_DIGEST,
        analysis_unit_code="person_occurrence",
        analysis_window_reference=WINDOW_REFERENCE,
        reference_duration_reference=DURATION_REFERENCE,
        reference_duration_digest=DURATION_DIGEST,
        eligible_case_set_digest=ELIGIBLE_CASE_DIGEST,
        analytic_case_occurrence_set_digest=ANALYTIC_CASE_DIGEST,
        source_universe_receipt_reference=SOURCE_REFERENCE,
        source_universe_receipt_version=4,
        source_universe_receipt_digest=SOURCE_DIGEST,
        sampling_design_receipt_reference=SAMPLING_REFERENCE,
        sampling_design_receipt_version=3,
        sampling_design_receipt_digest=SAMPLING_DIGEST,
        base_weight_method_code="inverse_inclusion_probability",
        base_weight_method_version=1,
        base_weight_evidence_digest=BASE_EVIDENCE_DIGEST,
        base_weight_artifact_digest=BASE_ARTIFACT_DIGEST,
        adjustments=(_adjustment(),),
        final_weight_artifact_digest=ADJUSTED_ARTIFACT_DIGEST,
        weight_eligibility_receipt_reference=ELIGIBILITY_REFERENCE,
        weight_eligibility_receipt_digest=ELIGIBILITY_DIGEST,
        analytic_case_count=1200,
        constructed_at=CONSTRUCTED_AT,
        correction_sequence=1,
        supersedes_receipt_digest=None,
        owner_contract_reference=OWNER_REFERENCE,
        owner_contract_version=7,
        owner_contract_digest=OWNER_DIGEST,
        used_at=used_at,
        purpose_code="selection_validity_analysis",
        policy=PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="final-analysis-weight-authority-read-v2",
            resource_kind="final_analysis_weight_authority",
            purpose_code="selection_validity_analysis",
            operation_code="read",
            required_scope_code="orgmetra.workforce_validation.read",
            permitted_fields=READ_FIELDS,
        ),
        read_port=_ReadPort(record),
    )


def test_chronology_is_owner_evidence_not_caller_input() -> None:
    parameters = signature(resolve_final_analysis_weight_authority).parameters
    assert "owner_contract_released_at" not in parameters
    assert "superseded_at" not in parameters


def test_owner_contract_cannot_retroactively_authorize_final_weight() -> None:
    with pytest.raises(ValueError, match="owner contract"):
        _record(owner_contract_released_at=RELEASED_AT + timedelta(microseconds=1))


def test_final_weight_uses_owner_resolved_half_open_authority_interval() -> None:
    historical = _resolve(
        used_at=SUPERSEDED_AT - timedelta(microseconds=1), record=_record()
    )
    fields = dict(historical.fields)
    assert fields["owner_contract_released_at"] == OWNER_RELEASED_AT
    assert fields["superseded_at"] == SUPERSEDED_AT

    with pytest.raises(FinalAnalysisWeightAuthorityIntegrityError, match="supersession"):
        _resolve(used_at=SUPERSEDED_AT, record=_record())


def test_non_positive_owner_authority_interval_is_rejected() -> None:
    with pytest.raises(ValueError, match="superseded_at"):
        _record(superseded_at=RELEASED_AT)
