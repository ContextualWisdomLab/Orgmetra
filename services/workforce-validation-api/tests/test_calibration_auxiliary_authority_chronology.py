"""Chronology contract for calibration auxiliary-use authority."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from inspect import signature
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.scientific_authority import (
    CalibrationAuxiliaryAuthorityRecord,
    resolve_calibration_auxiliary_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000c1")
AUTHORIZED_FROM = datetime(2026, 9, 1, tzinfo=timezone.utc)
AUTHORIZED_TO = datetime(2026, 10, 1, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, tzinfo=timezone.utc)
OWNER_CONTRACT_RELEASED_AT = AUTHORIZED_FROM - timedelta(days=1)


def _record(*, owner_contract_released_at: object) -> CalibrationAuxiliaryAuthorityRecord:
    return CalibrationAuxiliaryAuthorityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        authority_reference=(
            "scientific_auxiliary_authority:11111111-1111-4111-8111-111111111111"
        ),
        auxiliary_projection_reference=(
            "calibration_auxiliary_projection:22222222-2222-4222-8222-222222222222"
        ),
        auxiliary_projection_version=4,
        auxiliary_projection_digest="1" * 64,
        scientific_purpose_reference=(
            "scientific_data_use_purpose:33333333-3333-4333-8333-333333333333"
        ),
        scientific_purpose_digest="2" * 64,
        owner_contract_reference=(
            "released_owner_contract:44444444-4444-4444-8444-444444444444"
        ),
        owner_contract_version=7,
        owner_contract_digest="3" * 64,
        owner_contract_released_at=owner_contract_released_at,
        authorization_receipt_reference=(
            "scientific_data_authorization:55555555-5555-4555-8555-555555555555"
        ),
        authorization_receipt_digest="4" * 64,
        scientific_use_receipt_reference=(
            "scientific_use_receipt:66666666-6666-4666-8666-666666666666"
        ),
        scientific_use_receipt_digest="5" * 64,
        scientific_use_at=USED_AT,
        authorized_from=AUTHORIZED_FROM,
        authorized_to=AUTHORIZED_TO,
    )


def test_owner_contract_release_is_owner_evidence_not_a_caller_coordinate() -> None:
    assert "owner_contract_released_at" not in signature(
        resolve_calibration_auxiliary_authority
    ).parameters

    record = _record(owner_contract_released_at=OWNER_CONTRACT_RELEASED_AT)
    assert record.owner_contract_released_at == OWNER_CONTRACT_RELEASED_AT


def test_owner_contract_cannot_retroactively_authorize_the_interval() -> None:
    with pytest.raises(ValueError, match="owner contract must be released no later"):
        _record(owner_contract_released_at=AUTHORIZED_FROM + timedelta(seconds=1))


def test_owner_contract_release_requires_timezone_aware_evidence() -> None:
    with pytest.raises(ValueError):
        _record(owner_contract_released_at=datetime(2026, 8, 31))
