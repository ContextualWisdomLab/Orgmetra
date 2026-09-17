"""Hostile edges for released weight-eligibility authority."""

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.weight_eligibility_authority import (
    WeightEligibilityAuthorityRecord,
)


def _record(*, evidence_version: object = 1) -> WeightEligibilityAuthorityRecord:
    return WeightEligibilityAuthorityRecord(
        tenant_record_id=UUID("10000000-0000-7000-8000-000000000001"),
        validity_study_id=UUID("00000000-0000-7000-8000-0000000000d1"),
        eligibility_receipt_reference=(
            "weight_eligibility_receipt:11111111-1111-4111-8111-111111111111"
        ),
        eligibility_receipt_digest="1" * 64,
        evidence_version=evidence_version,
        weight_scope_code="longitudinal",
        target_population_reference="analysis_target_population:workers-2026q3",
        target_population_digest="2" * 64,
        reference_duration_reference="analysis_reference_duration:2026q3",
        reference_duration_digest="3" * 64,
        eligible_case_set_digest="4" * 64,
        weight_artifact_digest="5" * 64,
        constructed_at=datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc),
        owner_contract_reference=(
            "released_owner_contract:22222222-2222-4222-8222-222222222222"
        ),
        owner_contract_version=3,
        owner_contract_digest="6" * 64,
        released_at=datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc),
    )


def test_evidence_version_cannot_advance_without_contract_revision() -> None:
    with pytest.raises(ValueError, match="evidence_version must remain 1"):
        _record(evidence_version=2)
