"""Hostile edges for released weight-eligibility authority."""

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.weight_eligibility_authority import (
    WeightEligibilityAuthorityRecord,
)


def _record(
    *,
    evidence_version: object = 1,
    owner_contract_released_at: object = datetime(
        2026, 9, 16, 12, 30, tzinfo=timezone.utc
    ),
    superseded_at: object = None,
) -> WeightEligibilityAuthorityRecord:
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
        owner_contract_released_at=owner_contract_released_at,
        released_at=datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc),
        superseded_at=superseded_at,
    )


def test_evidence_version_cannot_advance_without_contract_revision() -> None:
    with pytest.raises(ValueError, match="evidence_version must remain 1"):
        _record(evidence_version=2)


def test_owner_chronology_requires_timezone_aware_instants() -> None:
    with pytest.raises(ValueError):
        _record(owner_contract_released_at=datetime(2026, 9, 16, 12, 30))
    with pytest.raises(ValueError):
        _record(superseded_at=datetime(2026, 9, 17, 13, 0))
