"""Fail closed when base-weight evidence predates its released owner contract."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.base_weight_authority import BaseWeightAuthorityRecord

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000f1")
SOURCE_RELEASED_AT = datetime(2026, 9, 17, 6, 0, tzinfo=timezone.utc)
SAMPLING_RELEASED_AT = datetime(2026, 9, 17, 6, 30, tzinfo=timezone.utc)
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 9, 17, 6, 45, tzinfo=timezone.utc)
CONSTRUCTED_AT = datetime(2026, 9, 17, 7, 0, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 7, 30, tzinfo=timezone.utc)


def _record(**overrides: object) -> BaseWeightAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "base_weight_evidence_receipt_reference": (
            "base_weight_evidence_receipt:11111111-1111-4111-8111-111111111111"
        ),
        "base_weight_evidence_receipt_digest": "1" * 64,
        "evidence_version": 1,
        "source_universe_receipt_reference": (
            "source_universe_receipt:22222222-2222-4222-8222-222222222222"
        ),
        "source_universe_receipt_version": 4,
        "source_universe_receipt_digest": "2" * 64,
        "source_universe_released_at": SOURCE_RELEASED_AT,
        "sampling_design_receipt_reference": (
            "sampling_design_receipt:33333333-3333-4333-8333-333333333333"
        ),
        "sampling_design_receipt_version": 3,
        "sampling_design_receipt_digest": "3" * 64,
        "sampling_design_released_at": SAMPLING_RELEASED_AT,
        "sampled_occurrence_set_digest": "4" * 64,
        "selection_probability_set_digest": "5" * 64,
        "selection_stage_count": 2,
        "base_weight_method_code": "inverse_inclusion_probability",
        "base_weight_method_version": 1,
        "base_weight_artifact_digest": "6" * 64,
        "constructed_at": CONSTRUCTED_AT,
        "owner_contract_reference": (
            "released_owner_contract:44444444-4444-4444-8444-444444444444"
        ),
        "owner_contract_version": 6,
        "owner_contract_digest": "7" * 64,
        "owner_contract_released_at": OWNER_CONTRACT_RELEASED_AT,
        "released_at": RELEASED_AT,
    }
    values.update(overrides)
    return BaseWeightAuthorityRecord(**values)


def test_owner_contract_release_is_preserved_as_authority_provenance() -> None:
    record = _record()

    assert dict(record.fields)["owner_contract_released_at"] == OWNER_CONTRACT_RELEASED_AT


def test_owner_contract_cannot_postdate_base_weight_receipt_release() -> None:
    with pytest.raises(ValueError, match="owner contract"):
        _record(owner_contract_released_at=RELEASED_AT + timedelta(seconds=1))
