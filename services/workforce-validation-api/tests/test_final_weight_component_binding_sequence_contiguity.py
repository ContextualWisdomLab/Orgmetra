"""Regression contract for contiguous final-weight component receipt bindings."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.final_weight_component_binding_authority import (
    FinalWeightAdjustmentEvidenceBinding,
    FinalWeightComponentBindingAuthorityRecord,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000f1")
OWNER_RELEASED_AT = datetime(2026, 9, 19, 4, 0, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 19, 4, 10, tzinfo=timezone.utc)


def _binding(
    *,
    sequence_number: int,
    evidence_kind: str,
    evidence_receipt_reference: str,
    evidence_receipt_digest: str,
) -> FinalWeightAdjustmentEvidenceBinding:
    return FinalWeightAdjustmentEvidenceBinding(
        sequence_number=sequence_number,
        evidence_kind=evidence_kind,
        evidence_receipt_reference=evidence_receipt_reference,
        evidence_version=1,
        evidence_receipt_digest=evidence_receipt_digest,
    )


def _record(
    adjustment_bindings: tuple[FinalWeightAdjustmentEvidenceBinding, ...],
) -> FinalWeightComponentBindingAuthorityRecord:
    return FinalWeightComponentBindingAuthorityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        analysis_weight_receipt_reference=(
            "analysis_weight_receipt:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        ),
        analysis_weight_receipt_digest="1" * 64,
        analysis_weight_evidence_version=1,
        binding_reference=(
            "final_weight_component_binding:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        ),
        binding_digest="2" * 64,
        binding_version=1,
        base_weight_evidence_receipt_reference=(
            "base_weight_evidence_receipt:cccccccc-cccc-4ccc-8ccc-cccccccccccc"
        ),
        base_weight_evidence_receipt_digest="3" * 64,
        base_weight_evidence_version=1,
        adjustment_bindings=adjustment_bindings,
        owner_contract_reference=(
            "released_owner_contract:dddddddd-dddd-4ddd-8ddd-dddddddddddd"
        ),
        owner_contract_version=1,
        owner_contract_digest="4" * 64,
        owner_contract_released_at=OWNER_RELEASED_AT,
        released_at=RELEASED_AT,
    )


def test_component_binding_sequences_must_start_at_one_and_remain_contiguous() -> None:
    first = _binding(
        sequence_number=1,
        evidence_kind="nonresponse_adjustment_receipt",
        evidence_receipt_reference=(
            "nonresponse_adjustment_receipt:11111111-1111-4111-8111-111111111111"
        ),
        evidence_receipt_digest="a" * 64,
    )
    third = _binding(
        sequence_number=3,
        evidence_kind="trimming_bounding_adjustment_receipt",
        evidence_receipt_reference=(
            "trimming_bounding_adjustment_receipt:33333333-3333-4333-8333-333333333333"
        ),
        evidence_receipt_digest="b" * 64,
    )
    second = _binding(
        sequence_number=2,
        evidence_kind="calibration_adjustment_receipt",
        evidence_receipt_reference=(
            "calibration_adjustment_receipt:22222222-2222-4222-8222-222222222222"
        ),
        evidence_receipt_digest="c" * 64,
    )

    with pytest.raises(ValueError, match="contiguous"):
        _record((first, third))
    with pytest.raises(ValueError, match="contiguous"):
        _record((second,))
