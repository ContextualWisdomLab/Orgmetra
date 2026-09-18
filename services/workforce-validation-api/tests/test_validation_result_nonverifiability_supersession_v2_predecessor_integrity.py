"""Require v2 correction authority to revalidate the complete predecessor contract."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
OWNER_REFERENCE = "released_owner_contract:55555555-5555-4555-8555-555555555555"
RESULT_DIGEST = "1" * 64
FAILED_DIGEST = "2" * 64
ATTEMPT_DIGEST = "3" * 64
OWNER_DIGEST = "5" * 64
OWNER_RELEASED_AT = datetime(2026, 9, 17, 5, 55, tzinfo=timezone.utc)
FAILED_RELEASED_AT = datetime(2026, 9, 17, 5, 59, tzinfo=timezone.utc)
EVALUATED_AT = datetime(2026, 9, 17, 6, 0, tzinfo=timezone.utc)
ATTEMPT_RELEASED_AT = datetime(2026, 9, 17, 6, 2, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 6, 5, tzinfo=timezone.utc)


def _predecessor() -> ValidationResultNonVerifiabilityRecord:
    """Build one canonical non-reproducible predecessor before structural corruption."""
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
    )


@pytest.mark.parametrize(
    ("tuple_index", "hostile_value"),
    [
        (7, RESULT_DIGEST),
        (13, EVALUATED_AT + timedelta(seconds=1)),
        (17, EVALUATED_AT + timedelta(seconds=1)),
        (18, EVALUATED_AT - timedelta(seconds=1)),
    ],
)
def test_v2_revalidates_full_predecessor_invariants(
    tuple_index: int, hostile_value: object
) -> None:
    """Reject exact-typed predecessors forged around v1 digest or chronology guards."""
    canonical = _predecessor()
    forged_values = list(canonical)
    forged_values[tuple_index] = hostile_value
    forged = tuple.__new__(ValidationResultNonVerifiabilityRecord, forged_values)

    with pytest.raises(ValueError):
        ValidationResultNonVerifiabilitySupersessionV2AuthorityRecord(
            predecessor=forged,
            evidence_version=2,
        )
