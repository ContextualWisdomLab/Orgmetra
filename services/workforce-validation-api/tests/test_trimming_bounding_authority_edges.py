"""Hostile edges for released trimming/bounding authority."""

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.trimming_bounding_authority import (
    TrimmingBoundingAuthorityRecord,
)


def _record(*, evidence_version: object = 1) -> TrimmingBoundingAuthorityRecord:
    return TrimmingBoundingAuthorityRecord(
        tenant_record_id=UUID("10000000-0000-7000-8000-000000000001"),
        validity_study_id=UUID("00000000-0000-7000-8000-0000000000d1"),
        adjustment_receipt_reference=(
            "trimming_bounding_adjustment_receipt:11111111-1111-4111-8111-111111111111"
        ),
        adjustment_receipt_digest="1" * 64,
        evidence_version=evidence_version,
        rule_reference="weight_trimming_rule:winsor-p995-v1",
        rule_version=2,
        rule_configuration_digest="2" * 64,
        affected_case_occurrence_set_digest="3" * 64,
        affected_case_count=17,
        input_weight_artifact_digest="4" * 64,
        output_weight_artifact_digest="5" * 64,
        constructed_at=datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc),
        owner_contract_reference=(
            "released_owner_contract:22222222-2222-4222-8222-222222222222"
        ),
        owner_contract_version=3,
        owner_contract_digest="6" * 64,
        owner_contract_released_at=datetime(2026, 9, 16, 12, 30, tzinfo=timezone.utc),
        released_at=datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc),
    )


def test_evidence_version_cannot_advance_without_contract_revision() -> None:
    with pytest.raises(ValueError, match="evidence_version must remain 1"):
        _record(evidence_version=2)
