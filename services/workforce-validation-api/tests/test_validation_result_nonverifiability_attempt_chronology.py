"""RED contract for immutable verification-attempt release chronology."""

from __future__ import annotations

from datetime import datetime, timezone
from inspect import signature
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.result_nonverifiability import (
    ValidationResultNonVerifiabilityReadPort,
    ValidationResultNonVerifiabilityRecord,
    resolve_validation_result_nonverifiability,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
OWNER_RELEASED_AT = datetime(2026, 9, 17, 5, 45, tzinfo=timezone.utc)
FAILED_EVIDENCE_RELEASED_AT = datetime(2026, 9, 17, 5, 50, tzinfo=timezone.utc)
EVALUATED_AT = datetime(2026, 9, 17, 6, 0, tzinfo=timezone.utc)
ATTEMPT_RELEASED_AT = datetime(2026, 9, 17, 6, 2, tzinfo=timezone.utc)
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
        "failure_mode": "non_reproducible",
        "failed_evidence_reference": (
            "analysis_weight_receipt:22222222-2222-4222-8222-222222222222"
        ),
        "failed_evidence_digest": "2" * 64,
        "failed_evidence_released_at": FAILED_EVIDENCE_RELEASED_AT,
        "verification_attempt_reference": (
            "validation_evidence_verification_attempt:"
            "33333333-3333-4333-8333-333333333333"
        ),
        "verification_attempt_digest": "3" * 64,
        "verification_attempt_released_at": ATTEMPT_RELEASED_AT,
        "owner_contract_reference": (
            "released_owner_contract:44444444-4444-4444-8444-444444444444"
        ),
        "owner_contract_version": 7,
        "owner_contract_digest": "4" * 64,
        "owner_contract_released_at": OWNER_RELEASED_AT,
        "evaluated_at": EVALUATED_AT,
        "released_at": RELEASED_AT,
    }
    values.update(overrides)
    return ValidationResultNonVerifiabilityRecord(**values)


def test_attempt_release_is_owner_evidence_not_lookup_coordinate() -> None:
    assert "verification_attempt_released_at" not in signature(
        resolve_validation_result_nonverifiability
    ).parameters
    assert (
        "verification_attempt_released_at"
        not in signature(
            ValidationResultNonVerifiabilityReadPort.read_validation_result_nonverifiability
        ).parameters
    )


def test_verification_attempt_release_is_retained() -> None:
    record = _record()
    assert record.verification_attempt_released_at == ATTEMPT_RELEASED_AT


def test_verification_attempt_cannot_be_released_before_evaluation() -> None:
    with pytest.raises(ValueError, match="verification_attempt_released_at"):
        _record(
            verification_attempt_released_at=datetime(
                2026, 9, 17, 5, 59, 59, tzinfo=timezone.utc
            )
        )


def test_verification_attempt_must_exist_before_outcome_release() -> None:
    with pytest.raises(ValueError, match="verification_attempt_released_at"):
        _record(
            verification_attempt_released_at=datetime(
                2026, 9, 17, 6, 5, 1, tzinfo=timezone.utc
            )
        )


def test_verification_attempt_release_requires_timezone() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _record(verification_attempt_released_at=datetime(2026, 9, 17, 6, 2))
