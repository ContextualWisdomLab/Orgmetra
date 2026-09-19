"""Fail closed when trimming/bounding owner contracts are retroactive."""

from __future__ import annotations

from datetime import datetime, timezone
from inspect import signature
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.trimming_bounding_authority import (
    TrimmingBoundingAuthorityRecord,
    resolve_trimming_bounding_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
CONSTRUCTED_AT = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 9, 16, 12, 30, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc)


def _record(**overrides: object) -> TrimmingBoundingAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "adjustment_receipt_reference": (
            "trimming_bounding_adjustment_receipt:11111111-1111-4111-8111-111111111111"
        ),
        "adjustment_receipt_digest": "1" * 64,
        "evidence_version": 1,
        "rule_reference": "weight_trimming_rule:winsor-p995-v1",
        "rule_version": 2,
        "rule_configuration_digest": "2" * 64,
        "affected_case_occurrence_set_digest": "3" * 64,
        "affected_case_count": 17,
        "input_weight_artifact_digest": "4" * 64,
        "output_weight_artifact_digest": "5" * 64,
        "constructed_at": CONSTRUCTED_AT,
        "owner_contract_reference": (
            "released_owner_contract:22222222-2222-4222-8222-222222222222"
        ),
        "owner_contract_version": 3,
        "owner_contract_digest": "6" * 64,
        "owner_contract_released_at": OWNER_CONTRACT_RELEASED_AT,
        "released_at": RELEASED_AT,
    }
    values.update(overrides)
    return TrimmingBoundingAuthorityRecord(**values)


def test_owner_contract_release_is_owner_resolved_not_a_request_coordinate() -> None:
    assert "owner_contract_released_at" not in signature(
        resolve_trimming_bounding_authority
    ).parameters


def test_owner_contract_must_exist_before_adjustment_receipt_release() -> None:
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
