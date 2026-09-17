"""Fail closed when non-verifiability owner contracts are retroactive."""

from __future__ import annotations

from datetime import datetime, timezone
from inspect import signature
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.result_nonverifiability import (
    ValidationResultNonVerifiabilityRecord,
    resolve_validation_result_nonverifiability,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 9, 17, 5, 55, tzinfo=timezone.utc)
EVALUATED_AT = datetime(2026, 9, 17, 6, 0, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 6, 5, tzinfo=timezone.utc)


def _record(**overrides: object) -> ValidationResultNonVerifiabilityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "result_reference": (
            "validation_analysis_result:11111111-1111-4111-8111-111111111111"
        ),
        "result_digest": "1" * 64,
        "failed_evidence_kind": "analysis_weight_receipt",
        "failure_mode": "missing",
        "failed_evidence_reference": None,
        "failed_evidence_digest": None,
        "verification_attempt_reference": (
            "validation_evidence_verification_attempt:"
            "33333333-3333-4333-8333-333333333333"
        ),
        "verification_attempt_digest": "3" * 64,
        "owner_contract_reference": (
            "released_owner_contract:44444444-4444-4444-8444-444444444444"
        ),
        "owner_contract_version": 7,
        "owner_contract_digest": "4" * 64,
        "owner_contract_released_at": OWNER_CONTRACT_RELEASED_AT,
        "evaluated_at": EVALUATED_AT,
        "released_at": RELEASED_AT,
    }
    values.update(overrides)
    return ValidationResultNonVerifiabilityRecord(**values)


def test_owner_contract_release_is_owner_resolved_not_a_request_coordinate() -> None:
    assert "owner_contract_released_at" not in signature(
        resolve_validation_result_nonverifiability
    ).parameters


def test_owner_contract_must_exist_before_verification_evaluation() -> None:
    with pytest.raises(ValueError, match="owner_contract_released_at"):
        _record(
            owner_contract_released_at=datetime(
                2026, 9, 17, 6, 0, 1, tzinfo=timezone.utc
            )
        )


def test_owner_contract_release_requires_timezone_aware_evidence() -> None:
    with pytest.raises(ValueError):
        _record(owner_contract_released_at=datetime(2026, 9, 17, 5, 55))


def test_owner_contract_can_be_released_immediately_before_evaluation() -> None:
    record = _record()
    assert record.owner_contract_released_at == OWNER_CONTRACT_RELEASED_AT
    assert record.evaluated_at == EVALUATED_AT
