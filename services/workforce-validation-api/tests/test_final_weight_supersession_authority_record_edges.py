"""Record-level hostile edges for final analysis-weight correction authority."""

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
RECEIPT_DIGEST = "1" * 64
SUCCESSOR_DIGEST = "3" * 64
OWNER_CONTRACT_DIGEST = "2" * 64
RELEASED_AT = datetime(2026, 7, 15, tzinfo=timezone.utc)
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 7, 1, tzinfo=timezone.utc)
SUPERSEDED_AT = datetime(2026, 9, 17, tzinfo=timezone.utc)
SUCCESSOR_RELEASED_AT = SUPERSEDED_AT - timedelta(hours=1)


def _record(**overrides: object) -> FinalWeightSupersessionAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "analysis_weight_receipt_reference": RECEIPT_REFERENCE,
        "analysis_weight_receipt_digest": RECEIPT_DIGEST,
        "evidence_version": 1,
        "correction_sequence": 2,
        "owner_contract_reference": OWNER_CONTRACT_REFERENCE,
        "owner_contract_version": 3,
        "owner_contract_digest": OWNER_CONTRACT_DIGEST,
        "owner_contract_released_at": OWNER_CONTRACT_RELEASED_AT,
        "released_at": RELEASED_AT,
        "superseded_at": SUPERSEDED_AT,
        "successor_analysis_weight_receipt_reference": SUCCESSOR_REFERENCE,
        "successor_correction_sequence": 3,
        "successor_analysis_weight_receipt_digest": SUCCESSOR_DIGEST,
        "successor_released_at": SUCCESSOR_RELEASED_AT,
    }
    values.update(overrides)
    return FinalWeightSupersessionAuthorityRecord(**values)


@pytest.mark.parametrize(
    "overrides",
    [
        {"owner_contract_released_at": datetime(2026, 7, 1)},
        {"released_at": datetime(2026, 7, 15)},
        {"superseded_at": datetime(2026, 9, 17)},
        {"successor_analysis_weight_receipt_reference": "wrong:receipt"},
        {"successor_correction_sequence": False},
        {"successor_analysis_weight_receipt_digest": "ABC"},
        {"successor_released_at": datetime(2026, 9, 16, 23, 0)},
    ],
)
def test_record_rejects_malformed_owner_resolved_chronology_or_successor_coordinates(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        _record(**overrides)
