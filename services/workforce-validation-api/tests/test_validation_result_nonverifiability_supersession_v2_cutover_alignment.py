"""RED contract binding v2 correction edges to ordinary predecessor cutover chronology."""

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.result_nonverifiability import (
    ValidationResultNonVerifiabilityRecord,
)
from orgmetra_workforce_validation_api.result_nonverifiability_supersession_v2_authority import (
    ValidationResultNonVerifiabilitySupersessionV2AuthorityRecord,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
RESULT_REFERENCE = "validation_analysis_result:11111111-1111-4111-8111-111111111111"
FAILED_REFERENCE = "analysis_weight_receipt:22222222-2222-4222-8222-222222222222"
ATTEMPT_REFERENCE = "validation_evidence_verification_attempt:33333333-3333-4333-8333-333333333333"
SUCCESSOR_ATTEMPT_REFERENCE = "validation_evidence_verification_attempt:44444444-4444-4444-8444-444444444444"
OWNER_REFERENCE = "released_owner_contract:55555555-5555-4555-8555-555555555555"
RESULT_DIGEST = "1" * 64
FAILED_DIGEST = "2" * 64
ATTEMPT_DIGEST = "3" * 64
SUCCESSOR_DIGEST = "4" * 64
OWNER_DIGEST = "5" * 64
OWNER_RELEASED_AT = datetime(2026, 9, 17, 5, 55, tzinfo=timezone.utc)
FAILED_RELEASED_AT = datetime(2026, 9, 17, 5, 59, tzinfo=timezone.utc)
EVALUATED_AT = datetime(2026, 9, 17, 6, 0, tzinfo=timezone.utc)
ATTEMPT_RELEASED_AT = datetime(2026, 9, 17, 6, 2, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 6, 5, tzinfo=timezone.utc)
CUTOVER = datetime(2026, 9, 17, 7, 0, tzinfo=timezone.utc)
OTHER_CUTOVER = datetime(2026, 9, 17, 7, 1, tzinfo=timezone.utc)


def _predecessor(*, superseded_at: datetime | None) -> ValidationResultNonVerifiabilityRecord:
    return ValidationResultNonVerifiabilityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        result_reference=RESULT_REFERENCE,
        result_digest=RESULT_DIGEST,
        failed_evidence_kind="analysis_weight_receipt",
        failure_mode="non_reproducible",
        failed_evidence_reference=FAILED_REFERENCE,
        failed_evidence_digest=FAILED_DIGEST,
        failed_evidence_released_at=FAILED_RELEASED_AT,
        verification_attempt_reference=ATTEMPT_REFERENCE,
        verification_attempt_digest=ATTEMPT_DIGEST,
        verification_attempt_released_at=ATTEMPT_RELEASED_AT,
        owner_contract_reference=OWNER_REFERENCE,
        owner_contract_version=7,
        owner_contract_digest=OWNER_DIGEST,
        owner_contract_released_at=OWNER_RELEASED_AT,
        evaluated_at=EVALUATED_AT,
        released_at=RELEASED_AT,
        superseded_at=superseded_at,
    )


def _successor_values(*, superseded_at: datetime) -> dict[str, object]:
    return {
        "superseded_at": superseded_at,
        "successor_target_result_reference": RESULT_REFERENCE,
        "successor_target_result_digest": RESULT_DIGEST,
        "successor_failed_evidence_kind": "analysis_weight_receipt",
        "successor_target_failed_evidence_reference": FAILED_REFERENCE,
        "successor_target_failed_evidence_digest": FAILED_DIGEST,
        "successor_target_failed_evidence_released_at": FAILED_RELEASED_AT,
        "successor_verification_attempt_reference": SUCCESSOR_ATTEMPT_REFERENCE,
        "successor_verification_attempt_digest": SUCCESSOR_DIGEST,
        "successor_verification_attempt_released_at": superseded_at,
    }


def test_successor_requires_the_same_cutover_as_the_ordinary_predecessor() -> None:
    """An explicit edge must not disagree with the ordinary owner projection."""
    with pytest.raises(ValueError, match="ordinary predecessor cutover"):
        ValidationResultNonVerifiabilitySupersessionV2AuthorityRecord(
            predecessor=_predecessor(superseded_at=CUTOVER),
            evidence_version=2,
            **_successor_values(superseded_at=OTHER_CUTOVER),
        )


def test_successor_is_invalid_when_ordinary_predecessor_has_no_cutover() -> None:
    """A separate edge must not manufacture currentness absent from the ordinary record."""
    with pytest.raises(ValueError, match="ordinary predecessor cutover"):
        ValidationResultNonVerifiabilitySupersessionV2AuthorityRecord(
            predecessor=_predecessor(superseded_at=None),
            evidence_version=2,
            **_successor_values(superseded_at=CUTOVER),
        )


def test_current_v2_projection_rejects_a_predecessor_already_marked_superseded() -> None:
    """Omitting successor coordinates must not hide an owner-resolved ordinary cutover."""
    with pytest.raises(ValueError, match="ordinary predecessor cutover"):
        ValidationResultNonVerifiabilitySupersessionV2AuthorityRecord(
            predecessor=_predecessor(superseded_at=CUTOVER),
            evidence_version=2,
        )
