"""Require final-weight successor release to be the exact supersession cutover."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.final_weight_supersession_authority import (
    FinalWeightSupersessionAuthorityRecord,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
RECEIPT_REFERENCE = "analysis_weight_receipt:11111111-1111-4111-8111-111111111111"
SUCCESSOR_REFERENCE = "analysis_weight_receipt:33333333-3333-4333-8333-333333333333"
OWNER_CONTRACT_REFERENCE = "released_owner_contract:22222222-2222-4222-8222-222222222222"
RELEASED_AT = datetime(2026, 7, 15, tzinfo=timezone.utc)
SUPERSEDED_AT = datetime(2026, 9, 17, tzinfo=timezone.utc)


def test_successor_release_must_equal_final_weight_cutover() -> None:
    """Reject an overlap where successor evidence exists before predecessor cutover."""
    with pytest.raises(
        ValueError,
        match="successor final-weight receipt must be released exactly at supersession",
    ):
        FinalWeightSupersessionAuthorityRecord(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            analysis_weight_receipt_reference=RECEIPT_REFERENCE,
            analysis_weight_receipt_digest="1" * 64,
            evidence_version=1,
            correction_sequence=2,
            owner_contract_reference=OWNER_CONTRACT_REFERENCE,
            owner_contract_version=3,
            owner_contract_digest="2" * 64,
            owner_contract_released_at=RELEASED_AT - timedelta(days=1),
            released_at=RELEASED_AT,
            superseded_at=SUPERSEDED_AT,
            successor_analysis_weight_receipt_reference=SUCCESSOR_REFERENCE,
            successor_correction_sequence=3,
            successor_analysis_weight_receipt_digest="3" * 64,
            successor_released_at=SUPERSEDED_AT - timedelta(seconds=1),
        )
