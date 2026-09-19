"""Cross-owner consistency for deterministic final-weight component reproduction."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.final_weight_authority import (
    FinalAnalysisWeightAuthorityRecord,
    FinalWeightAdjustmentCoordinate,
)
from orgmetra_workforce_validation_api.final_weight_component_binding_authority import (
    FinalWeightAdjustmentEvidenceBinding,
    FinalWeightComponentBindingAuthorityRecord,
)
from orgmetra_workforce_validation_api.final_weight_component_evidence_resolution import (
    AdjustmentComponentEvidence,
    BaseWeightComponentEvidence,
    FinalWeightComponentEvidenceIntegrityError,
    FinalWeightComponentEvidenceNotFound,
    FinalWeightComponentEvidenceResolution,
    corroborate_final_weight_component_evidence,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000f1")
CONSTRUCTED_AT = datetime(2026, 9, 19, 4, 5, tzinfo=timezone.utc)
FINAL_RELEASED_AT = datetime(2026, 9, 19, 4, 10, tzinfo=timezone.utc)
BINDING_RELEASED_AT = datetime(2026, 9, 19, 4, 15, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 19, 4, 30, tzinfo=timezone.utc)
FINAL_REFERENCE = "analysis_weight_receipt:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
FINAL_DIGEST = "1" * 64
BASE_RECEIPT_REFERENCE = (
    "base_weight_evidence_receipt:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
)
BASE_RECEIPT_DIGEST = "2" * 64
BASE_ARTIFACT_DIGEST = "3" * 64
ADJUSTMENT_RECEIPT_REFERENCE = (
    "nonresponse_adjustment_receipt:cccccccc-cccc-4ccc-8ccc-cccccccccccc"
)
ADJUSTMENT_RECEIPT_DIGEST = "4" * 64
ADJUSTMENT_OUTPUT_DIGEST = "5" * 64
CONFIGURATION_DIGEST = "6" * 64
METHOD_REFERENCE = "weight_method:dddddddd-dddd-4ddd-8ddd-dddddddddddd"


def _final_weight(**overrides: object) -> FinalAnalysisWeightAuthorityRecord:
    adjustment = FinalWeightAdjustmentCoordinate(
        sequence_number=1,
        adjustment_code="nonresponse_adjustment",
        method_reference=METHOD_REFERENCE,
        method_version=1,
        input_weight_artifact_digest=BASE_ARTIFACT_DIGEST,
        output_weight_artifact_digest=ADJUSTMENT_OUTPUT_DIGEST,
        configuration_digest=CONFIGURATION_DIGEST,
        evidence_receipt_digest=ADJUSTMENT_RECEIPT_DIGEST,
        evidence_kind="nonresponse_adjustment_receipt",
    )
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "analysis_weight_receipt_reference": FINAL_REFERENCE,
        "analysis_weight_receipt_digest": FINAL_DIGEST,
        "evidence_version": 1,
        "estimand_reference": "validation_estimand:11111111-1111-4111-8111-111111111111",
        "estimand_digest": "7" * 64,
        "estimand_scope_code": "cross_sectional",
        "target_population_reference": (
            "analysis_target_population:22222222-2222-4222-8222-222222222222"
        ),
        "target_population_digest": "8" * 64,
        "analysis_unit_code": "person",
        "analysis_window_reference": "analysis_window:33333333-3333-4333-8333-333333333333",
        "reference_duration_reference": (
            "analysis_reference_duration:44444444-4444-4444-8444-444444444444"
        ),
        "reference_duration_digest": "9" * 64,
        "eligible_case_set_digest": "a" * 64,
        "analytic_case_occurrence_set_digest": "b" * 64,
        "source_universe_receipt_reference": (
            "source_universe_receipt:55555555-5555-4555-8555-555555555555"
        ),
        "source_universe_receipt_version": 1,
        "source_universe_receipt_digest": "c" * 64,
        "sampling_design_receipt_reference": (
            "sampling_design_receipt:66666666-6666-4666-8666-666666666666"
        ),
        "sampling_design_receipt_version": 1,
        "sampling_design_receipt_digest": "d" * 64,
        "base_weight_method_code": "inverse_probability",
        "base_weight_method_version": 1,
        "base_weight_evidence_digest": BASE_RECEIPT_DIGEST,
        "base_weight_artifact_digest": BASE_ARTIFACT_DIGEST,
        "adjustments": (adjustment,),
        "final_weight_artifact_digest": ADJUSTMENT_OUTPUT_DIGEST,
        "weight_eligibility_receipt_reference": (
            "weight_eligibility_receipt:77777777-7777-4777-8777-777777777777"
        ),
        "weight_eligibility_receipt_digest": "e" * 64,
        "analytic_case_count": 10,
        "constructed_at": CONSTRUCTED_AT,
        "correction_sequence": 1,
        "supersedes_receipt_digest": None,
        "owner_contract_reference": (
            "released_owner_contract:88888888-8888-4888-8888-888888888888"
        ),
        "owner_contract_version": 1,
        "owner_contract_digest": "f" * 64,
        "owner_contract_released_at": CONSTRUCTED_AT - timedelta(minutes=10),
        "released_at": FINAL_RELEASED_AT,
        "superseded_at": None,
    }
    values.update(overrides)
    return FinalAnalysisWeightAuthorityRecord(**values)


def _binding(**overrides: object) -> FinalWeightComponentBindingAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "analysis_weight_receipt_reference": FINAL_REFERENCE,
        "analysis_weight_receipt_digest": FINAL_DIGEST,
        "analysis_weight_evidence_version": 1,
        "binding_reference": (
            "final_weight_component_binding:99999999-9999-4999-8999-999999999999"
        ),
        "binding_digest": "0" * 64,
        "binding_version": 1,
        "base_weight_evidence_receipt_reference": BASE_RECEIPT_REFERENCE,
        "base_weight_evidence_receipt_digest": BASE_RECEIPT_DIGEST,
        "base_weight_evidence_version": 1,
        "adjustment_bindings": (
            FinalWeightAdjustmentEvidenceBinding(
                sequence_number=1,
                evidence_kind="nonresponse_adjustment_receipt",
                evidence_receipt_reference=ADJUSTMENT_RECEIPT_REFERENCE,
                evidence_version=1,
                evidence_receipt_digest=ADJUSTMENT_RECEIPT_DIGEST,
            ),
        ),
        "owner_contract_reference": (
            "released_owner_contract:aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        ),
        "owner_contract_version": 1,
        "owner_contract_digest": "a" * 64,
        "owner_contract_released_at": FINAL_RELEASED_AT,
        "released_at": BINDING_RELEASED_AT,
        "superseded_at": None,
    }
    values.update(overrides)
    return FinalWeightComponentBindingAuthorityRecord(**values)


def _base_evidence(**overrides: object) -> BaseWeightComponentEvidence:
    values: dict[str, object] = {
        "receipt_reference": BASE_RECEIPT_REFERENCE,
        "receipt_digest": BASE_RECEIPT_DIGEST,
        "evidence_version": 1,
        "method_code": "inverse_probability",
        "method_version": 1,
        "output_weight_artifact_digest": BASE_ARTIFACT_DIGEST,
        "released_at": CONSTRUCTED_AT - timedelta(minutes=15),
        "superseded_at": None,
    }
    values.update(overrides)
    return BaseWeightComponentEvidence(**values)


def _adjustment_evidence(**overrides: object) -> AdjustmentComponentEvidence:
    values: dict[str, object] = {
        "evidence_kind": "nonresponse_adjustment_receipt",
        "receipt_reference": ADJUSTMENT_RECEIPT_REFERENCE,
        "receipt_digest": ADJUSTMENT_RECEIPT_DIGEST,
        "evidence_version": 1,
        "method_reference": METHOD_REFERENCE,
        "method_version": 1,
        "input_weight_artifact_digest": BASE_ARTIFACT_DIGEST,
        "output_weight_artifact_digest": ADJUSTMENT_OUTPUT_DIGEST,
        "configuration_digest": CONFIGURATION_DIGEST,
        "released_at": CONSTRUCTED_AT - timedelta(minutes=1),
        "superseded_at": None,
    }
    values.update(overrides)
    return AdjustmentComponentEvidence(**values)


class _ReadPort:
    def __init__(
        self,
        *,
        base: BaseWeightComponentEvidence | None = None,
        adjustment: AdjustmentComponentEvidence | None = None,
    ) -> None:
        self.base = _base_evidence() if base is None else base
        self.adjustment = _adjustment_evidence() if adjustment is None else adjustment
        self.base_calls: list[dict[str, object]] = []
        self.adjustment_calls: list[dict[str, object]] = []

    def read_base_weight_component_evidence(self, **kwargs: object) -> BaseWeightComponentEvidence | None:
        self.base_calls.append(dict(kwargs))
        return self.base

    def read_adjustment_component_evidence(self, **kwargs: object) -> AdjustmentComponentEvidence | None:
        self.adjustment_calls.append(dict(kwargs))
        return self.adjustment


def test_exact_receipt_identity_resolves_and_cross_checks_component_semantics() -> None:
    port = _ReadPort()
    resolution = corroborate_final_weight_component_evidence(
        final_weight=_final_weight(),
        binding=_binding(),
        used_at=USED_AT,
        read_port=port,
    )

    assert isinstance(resolution, FinalWeightComponentEvidenceResolution)
    assert resolution.base_weight.receipt_reference == BASE_RECEIPT_REFERENCE
    assert resolution.adjustments == (_adjustment_evidence(),)
    assert port.base_calls == [
        {
            "tenant_record_id": TENANT,
            "validity_study_id": STUDY,
            "receipt_reference": BASE_RECEIPT_REFERENCE,
            "receipt_digest": BASE_RECEIPT_DIGEST,
            "evidence_version": 1,
        }
    ]
    assert port.adjustment_calls == [
        {
            "tenant_record_id": TENANT,
            "validity_study_id": STUDY,
            "evidence_kind": "nonresponse_adjustment_receipt",
            "receipt_reference": ADJUSTMENT_RECEIPT_REFERENCE,
            "receipt_digest": ADJUSTMENT_RECEIPT_DIGEST,
            "evidence_version": 1,
        }
    ]


def test_component_method_or_artifact_mismatch_fails_closed() -> None:
    port = _ReadPort(
        adjustment=_adjustment_evidence(
            method_reference="weight_method:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
        )
    )
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="adjustment semantics"):
        corroborate_final_weight_component_evidence(
            final_weight=_final_weight(),
            binding=_binding(),
            used_at=USED_AT,
            read_port=port,
        )


def test_component_not_released_by_final_construction_fails_closed() -> None:
    port = _ReadPort(
        adjustment=_adjustment_evidence(
            released_at=CONSTRUCTED_AT + timedelta(microseconds=1)
        )
    )
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="construction"):
        corroborate_final_weight_component_evidence(
            final_weight=_final_weight(),
            binding=_binding(),
            used_at=USED_AT,
            read_port=port,
        )


def test_missing_exact_component_receipt_fails_closed() -> None:
    port = _ReadPort()
    port.adjustment = None
    with pytest.raises(FinalWeightComponentEvidenceNotFound):
        corroborate_final_weight_component_evidence(
            final_weight=_final_weight(),
            binding=_binding(),
            used_at=USED_AT,
            read_port=port,
        )


def test_binding_cannot_omit_a_specialized_adjustment() -> None:
    binding = _binding(adjustment_bindings=())
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="specialized"):
        corroborate_final_weight_component_evidence(
            final_weight=_final_weight(),
            binding=binding,
            used_at=USED_AT,
            read_port=_ReadPort(),
        )


def test_binding_cannot_be_released_before_the_final_weight_authority() -> None:
    binding_release = FINAL_RELEASED_AT - timedelta(microseconds=1)
    binding = _binding(
        owner_contract_released_at=binding_release - timedelta(minutes=1),
        released_at=binding_release,
    )
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="binding.*final"):
        corroborate_final_weight_component_evidence(
            final_weight=_final_weight(),
            binding=binding,
            used_at=USED_AT,
            read_port=_ReadPort(),
        )
