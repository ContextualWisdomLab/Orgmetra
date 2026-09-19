"""Structural-integrity regressions for final analysis-weight owner evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy

from orgmetra_workforce_validation_api import ValidationPrincipal
import orgmetra_workforce_validation_api.final_weight_authority as target
from orgmetra_workforce_validation_api.final_weight_authority import (
    FinalAnalysisWeightAuthorityIntegrityError,
    FinalAnalysisWeightAuthorityRecord,
    FinalWeightAdjustmentCoordinate,
    resolve_final_analysis_weight_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000f1")
CONSTRUCTED_AT = datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc)
OWNER_RELEASED_AT = datetime(2026, 9, 17, 8, 10, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 8, 30, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, 9, 0, tzinfo=timezone.utc)


class _ReadPort:
    """Return configured persisted evidence through the final-weight owner capability."""

    def __init__(self, result: object) -> None:
        self.result = result

    def read_final_analysis_weight_authority(self, **_: object) -> object:
        """Return the configured owner evidence."""
        return self.result


def _adjustment() -> FinalWeightAdjustmentCoordinate:
    return FinalWeightAdjustmentCoordinate(
        sequence_number=1,
        adjustment_code="nonresponse_adjustment",
        method_reference="weight_method:nonresponse-cell-adjustment",
        method_version=2,
        input_weight_artifact_digest="a" * 64,
        output_weight_artifact_digest="b" * 64,
        configuration_digest="c" * 64,
        evidence_receipt_digest="d" * 64,
        evidence_kind="nonresponse_adjustment_receipt",
    )


def _record() -> FinalAnalysisWeightAuthorityRecord:
    return FinalAnalysisWeightAuthorityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        analysis_weight_receipt_reference=(
            "analysis_weight_receipt:11111111-1111-4111-8111-111111111111"
        ),
        analysis_weight_receipt_digest="1" * 64,
        evidence_version=1,
        estimand_reference="validation_estimand:criterion-validity-q3",
        estimand_digest="2" * 64,
        estimand_scope_code="longitudinal",
        target_population_reference="analysis_target_population:workers-2026q3",
        target_population_digest="3" * 64,
        analysis_unit_code="person_occurrence",
        analysis_window_reference="analysis_window:2026q3",
        reference_duration_reference="analysis_reference_duration:2026q3",
        reference_duration_digest="4" * 64,
        eligible_case_set_digest="5" * 64,
        analytic_case_occurrence_set_digest="6" * 64,
        source_universe_receipt_reference=(
            "source_universe_receipt:22222222-2222-4222-8222-222222222222"
        ),
        source_universe_receipt_version=4,
        source_universe_receipt_digest="7" * 64,
        sampling_design_receipt_reference=(
            "sampling_design_receipt:33333333-3333-4333-8333-333333333333"
        ),
        sampling_design_receipt_version=3,
        sampling_design_receipt_digest="8" * 64,
        base_weight_method_code="inverse_inclusion_probability",
        base_weight_method_version=1,
        base_weight_evidence_digest="9" * 64,
        base_weight_artifact_digest="a" * 64,
        adjustments=(_adjustment(),),
        final_weight_artifact_digest="b" * 64,
        weight_eligibility_receipt_reference=(
            "weight_eligibility_receipt:44444444-4444-4444-8444-444444444444"
        ),
        weight_eligibility_receipt_digest="e" * 64,
        analytic_case_count=1200,
        constructed_at=CONSTRUCTED_AT,
        correction_sequence=1,
        supersedes_receipt_digest=None,
        owner_contract_reference=(
            "released_owner_contract:55555555-5555-4555-8555-555555555555"
        ),
        owner_contract_version=7,
        owner_contract_digest="f" * 64,
        owner_contract_released_at=OWNER_RELEASED_AT,
        released_at=RELEASED_AT,
        superseded_at=None,
    )


def _resolve(result: object) -> object:
    values = dict(_record().fields)
    values.update(
        {
            "principal": ValidationPrincipal(
                tenant_record_id=TENANT,
                actor_reference="person:validation-analyst-1",
                granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
            ),
            "tenant_record_id": TENANT,
            "validity_study_id": STUDY,
            "used_at": USED_AT,
            "purpose_code": "selection_validity_analysis",
            "policy": PurposeBoundAccessPolicy(
                tenant_record_id=TENANT,
                policy_version_code="final-analysis-weight-authority-read-v1",
                resource_kind="final_analysis_weight_authority",
                purpose_code="selection_validity_analysis",
                operation_code="read",
                required_scope_code="orgmetra.workforce_validation.read",
                permitted_fields=target._READ_FIELDS,
            ),
            "read_port": _ReadPort(result),
        }
    )
    return resolve_final_analysis_weight_authority(**values)


def test_hidden_trailing_tuple_structure_fails_closed() -> None:
    canonical = _record()
    forged = tuple.__new__(
        FinalAnalysisWeightAuthorityRecord,
        tuple(canonical) + ("hidden-owner-coordinate",),
    )

    with pytest.raises(FinalAnalysisWeightAuthorityIntegrityError):
        _resolve(forged)


def test_truncated_exact_typed_tuple_maps_to_integrity_error() -> None:
    canonical = _record()
    forged = tuple.__new__(FinalAnalysisWeightAuthorityRecord, tuple(canonical)[:-1])

    with pytest.raises(FinalAnalysisWeightAuthorityIntegrityError):
        _resolve(forged)


def test_duplicate_nested_field_cannot_be_normalized_away() -> None:
    canonical = _record()
    duplicate_fields = canonical.fields + (
        ("owner_contract_reference", dict(canonical.fields)["owner_contract_reference"]),
    )
    forged = tuple.__new__(
        FinalAnalysisWeightAuthorityRecord,
        (
            canonical[0],
            canonical[1],
            duplicate_fields,
            canonical[3],
            canonical[4],
            canonical[5],
        ),
    )

    with pytest.raises(FinalAnalysisWeightAuthorityIntegrityError):
        _resolve(forged)
