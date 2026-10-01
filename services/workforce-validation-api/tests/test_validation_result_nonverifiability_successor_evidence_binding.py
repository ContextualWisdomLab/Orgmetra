"""Bind negative-outcome supersession to the same failed-evidence obligation."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.result_nonverifiability_supersession_authority import (
    ValidationResultNonVerifiabilitySupersessionAuthorityRecord,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
RESULT_REFERENCE = "validation_analysis_result:11111111-1111-4111-8111-111111111111"
OWNER_CONTRACT_REFERENCE = "released_owner_contract:22222222-2222-4222-8222-222222222222"
ATTEMPT_REFERENCE = "validation_evidence_verification_attempt:33333333-3333-4333-8333-333333333333"
SUCCESSOR_ATTEMPT_REFERENCE = "validation_evidence_verification_attempt:44444444-4444-4444-8444-444444444444"
RESULT_DIGEST = "1" * 64
OWNER_CONTRACT_DIGEST = "2" * 64
ATTEMPT_DIGEST = "3" * 64
SUCCESSOR_ATTEMPT_DIGEST = "4" * 64
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 9, 1, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 18, 8, tzinfo=timezone.utc)
CUTOVER = RELEASED_AT + timedelta(hours=1)


def _record(
    successor_failed_evidence_kind: str,
) -> ValidationResultNonVerifiabilitySupersessionAuthorityRecord:
    """Build one supersession edge with an explicit successor evidence obligation."""
    return ValidationResultNonVerifiabilitySupersessionAuthorityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        result_reference=RESULT_REFERENCE,
        result_digest=RESULT_DIGEST,
        failed_evidence_kind="analysis_weight_receipt",
        failure_mode="missing",
        verification_attempt_reference=ATTEMPT_REFERENCE,
        verification_attempt_digest=ATTEMPT_DIGEST,
        evidence_version=1,
        owner_contract_reference=OWNER_CONTRACT_REFERENCE,
        owner_contract_version=3,
        owner_contract_digest=OWNER_CONTRACT_DIGEST,
        owner_contract_released_at=OWNER_CONTRACT_RELEASED_AT,
        released_at=RELEASED_AT,
        superseded_at=CUTOVER,
        successor_target_result_reference=RESULT_REFERENCE,
        successor_target_result_digest=RESULT_DIGEST,
        successor_failed_evidence_kind=successor_failed_evidence_kind,
        successor_verification_attempt_reference=SUCCESSOR_ATTEMPT_REFERENCE,
        successor_verification_attempt_digest=SUCCESSOR_ATTEMPT_DIGEST,
        successor_verification_attempt_released_at=CUTOVER,
    )


def test_successor_attempt_preserves_the_failed_evidence_obligation() -> None:
    """Persist the obligation family that the successor attempt actually re-evaluates."""
    successor = dict(_record("analysis_weight_receipt").successor_fields or ())
    assert successor["successor_failed_evidence_kind"] == "analysis_weight_receipt"


def test_unrelated_evidence_family_cannot_retire_the_negative_outcome() -> None:
    """A same-result attempt for another evidence family cannot end this failure interval."""
    with pytest.raises(ValueError, match="same failed-evidence obligation"):
        _record("variance_design_receipt")
