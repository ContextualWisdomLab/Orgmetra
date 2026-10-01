"""Hostile edges for typed nonresponse-adjustment authority."""

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.nonresponse_adjustment_authority import (
    NonresponseAdjustmentAuthorityRecord,
)


def _record(*, evidence_version: object = 1) -> NonresponseAdjustmentAuthorityRecord:
    return NonresponseAdjustmentAuthorityRecord(
        tenant_record_id=UUID("10000000-0000-7000-8000-000000000001"),
        validity_study_id=UUID("00000000-0000-7000-8000-0000000000d1"),
        nonresponse_receipt_reference=(
            "nonresponse_adjustment_receipt:11111111-1111-4111-8111-111111111111"
        ),
        nonresponse_receipt_digest="1" * 64,
        evidence_version=evidence_version,
        response_disposition_receipt_reference=(
            "response_disposition_receipt:22222222-2222-4222-8222-222222222222"
        ),
        response_disposition_receipt_version=4,
        response_disposition_receipt_digest="2" * 64,
        response_disposition_receipt_released_at=datetime(
            2026, 9, 16, 10, 0, tzinfo=timezone.utc
        ),
        adjustment_population_digest="3" * 64,
        method_reference="weight_method:response_propensity_cells",
        method_version=3,
        configuration_digest="4" * 64,
        ineligible_treatment_code="exclude_ineligible",
        unknown_treatment_code="retain_unknown_class",
        unavailable_treatment_code="retain_unavailable_class",
        input_weight_artifact_digest="5" * 64,
        output_weight_artifact_digest="6" * 64,
        constructed_at=datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc),
        owner_contract_reference=(
            "released_owner_contract:33333333-3333-4333-8333-333333333333"
        ),
        owner_contract_version=5,
        owner_contract_digest="7" * 64,
        owner_contract_released_at=datetime(2026, 9, 16, 12, 30, tzinfo=timezone.utc),
        released_at=datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc),
    )


def test_evidence_version_cannot_advance_without_a_contract_revision() -> None:
    with pytest.raises(ValueError, match="evidence_version must remain 1"):
        _record(evidence_version=2)
