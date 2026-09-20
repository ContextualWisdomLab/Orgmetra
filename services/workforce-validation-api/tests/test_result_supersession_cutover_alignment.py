"""Require a released successor to become authoritative exactly at predecessor cutover."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.result_supersession_authority import (
    ValidationResultSupersessionAuthorityRecord,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
RESULT_REFERENCE = "validation_analysis_result:11111111-1111-4111-8111-111111111111"
SUCCESSOR_REFERENCE = "validation_analysis_result:33333333-3333-4333-8333-333333333333"
OWNER_REFERENCE = "released_owner_contract:22222222-2222-4222-8222-222222222222"
RESULT_DIGEST = "1" * 64
SUCCESSOR_DIGEST = "3" * 64
OWNER_DIGEST = "2" * 64
RELEASED_AT = datetime(2026, 9, 17, 10, tzinfo=timezone.utc)
CUTOVER = datetime(2026, 9, 17, 12, tzinfo=timezone.utc)


def _record(*, successor_released_at: datetime) -> ValidationResultSupersessionAuthorityRecord:
    return ValidationResultSupersessionAuthorityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        result_reference=RESULT_REFERENCE,
        result_digest=RESULT_DIGEST,
        evidence_version=1,
        correction_sequence=2,
        owner_contract_reference=OWNER_REFERENCE,
        owner_contract_version=3,
        owner_contract_digest=OWNER_DIGEST,
        owner_contract_released_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        released_at=RELEASED_AT,
        superseded_at=CUTOVER,
        successor_result_reference=SUCCESSOR_REFERENCE,
        successor_correction_sequence=3,
        successor_result_digest=SUCCESSOR_DIGEST,
        successor_released_at=successor_released_at,
    )


def test_successor_release_cannot_precede_cutover() -> None:
    with pytest.raises(ValueError, match="exactly at supersession"):
        _record(successor_released_at=CUTOVER - timedelta(seconds=1))


def test_successor_release_matches_cutover() -> None:
    record = _record(successor_released_at=CUTOVER)
    assert record.superseded_at == CUTOVER
    assert dict(record.successor_fields or ())["successor_released_at"] == CUTOVER
