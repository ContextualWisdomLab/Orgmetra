"""Fail closed when supersession would discard non-reproducible evidence identity."""

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.result_nonverifiability_supersession_authority import (
    ValidationResultNonVerifiabilitySupersessionAuthorityRecord,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
RESULT_REFERENCE = "validation_analysis_result:11111111-1111-4111-8111-111111111111"
ATTEMPT_REFERENCE = "validation_evidence_verification_attempt:33333333-3333-4333-8333-333333333333"
OWNER_CONTRACT_REFERENCE = "released_owner_contract:22222222-2222-4222-8222-222222222222"
RESULT_DIGEST = "1" * 64
ATTEMPT_DIGEST = "3" * 64
OWNER_CONTRACT_DIGEST = "2" * 64
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 9, 1, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 18, 8, tzinfo=timezone.utc)


def _record(*, failure_mode: str) -> ValidationResultNonVerifiabilitySupersessionAuthorityRecord:
    """Build one predecessor using the v1 supersession identity currently persisted."""
    return ValidationResultNonVerifiabilitySupersessionAuthorityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        result_reference=RESULT_REFERENCE,
        result_digest=RESULT_DIGEST,
        failed_evidence_kind="analysis_weight_receipt",
        failure_mode=failure_mode,
        verification_attempt_reference=ATTEMPT_REFERENCE,
        verification_attempt_digest=ATTEMPT_DIGEST,
        evidence_version=1,
        owner_contract_reference=OWNER_CONTRACT_REFERENCE,
        owner_contract_version=3,
        owner_contract_digest=OWNER_CONTRACT_DIGEST,
        owner_contract_released_at=OWNER_CONTRACT_RELEASED_AT,
        released_at=RELEASED_AT,
    )


def test_missing_predecessor_remains_supported_without_fabricated_evidence_identity() -> None:
    """Keep missing-evidence outcomes representable because no artifact identity exists."""
    fields = dict(_record(failure_mode="missing").fields)
    assert fields["failure_mode"] == "missing"


def test_nonreproducible_predecessor_fails_closed_when_artifact_identity_would_be_lost() -> None:
    """Reject v1 supersession until exact failed reference, digest, and release can be bound."""
    with pytest.raises(
        ValueError,
        match="non_reproducible supersession requires exact failed-evidence identity",
    ):
        _record(failure_mode="non_reproducible")
