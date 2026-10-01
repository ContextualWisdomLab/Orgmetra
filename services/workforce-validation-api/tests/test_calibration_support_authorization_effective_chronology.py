"""RED contract for calibration support authorization release chronology."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.calibration_support_authority import (
    CalibrationSupportAuthorityRecord,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000f2")
AUTHORIZED_FROM = datetime(2026, 9, 17, 8, 10, tzinfo=timezone.utc)
USE_AT = datetime(2026, 9, 17, 8, 30, tzinfo=timezone.utc)
CONSTRUCTED_AT = datetime(2026, 9, 17, 9, 0, tzinfo=timezone.utc)


def test_authorization_receipt_cannot_be_released_after_interval_begins() -> None:
    """Do not accept retroactive authority merely because the receipt predates use."""
    with pytest.raises(ValueError, match="authorization receipt must exist before authorization begins"):
        CalibrationSupportAuthorityRecord(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            support_authority_reference=(
                "calibration_support_authority:10101010-1010-4010-8010-101010101010"
            ),
            support_authority_digest="0" * 64,
            evidence_version=1,
            calibration_receipt_reference=(
                "calibration_adjustment_receipt:11111111-1111-4111-8111-111111111111"
            ),
            calibration_receipt_digest="1" * 64,
            auxiliary_authority_reference=(
                "scientific_auxiliary_authority:22222222-2222-4222-8222-222222222222"
            ),
            auxiliary_projection_reference=(
                "calibration_auxiliary_projection:33333333-3333-4333-8333-333333333333"
            ),
            auxiliary_projection_version=3,
            auxiliary_projection_digest="2" * 64,
            auxiliary_purpose_reference=(
                "scientific_data_use_purpose:44444444-4444-4444-8444-444444444444"
            ),
            auxiliary_purpose_digest="3" * 64,
            auxiliary_owner_contract_reference=(
                "released_owner_contract:55555555-5555-4555-8555-555555555555"
            ),
            auxiliary_owner_contract_version=5,
            auxiliary_owner_contract_digest="4" * 64,
            auxiliary_owner_contract_released_at=datetime(
                2026, 9, 17, 7, 50, tzinfo=timezone.utc
            ),
            auxiliary_authorization_receipt_reference=(
                "scientific_data_authorization:66666666-6666-4666-8666-666666666666"
            ),
            auxiliary_authorization_receipt_digest="5" * 64,
            auxiliary_authorization_receipt_released_at=(
                AUTHORIZED_FROM + timedelta(seconds=1)
            ),
            auxiliary_scientific_use_receipt_reference=(
                "scientific_use_receipt:77777777-7777-4777-8777-777777777777"
            ),
            auxiliary_scientific_use_receipt_digest="6" * 64,
            auxiliary_scientific_use_at=USE_AT,
            auxiliary_authorized_from=AUTHORIZED_FROM,
            auxiliary_authorized_to=datetime(2026, 10, 1, tzinfo=timezone.utc),
            benchmark_receipt_reference=(
                "calibration_benchmark_receipt:88888888-8888-4888-8888-888888888888"
            ),
            benchmark_receipt_version=8,
            benchmark_receipt_digest="7" * 64,
            benchmark_owner_contract_reference=(
                "released_owner_contract:99999999-9999-4999-8999-999999999999"
            ),
            benchmark_owner_contract_version=9,
            benchmark_owner_contract_digest="8" * 64,
            benchmark_owner_contract_released_at=datetime(
                2026, 9, 17, 8, 0, tzinfo=timezone.utc
            ),
            benchmark_reference_at=datetime(2026, 9, 17, 8, 15, tzinfo=timezone.utc),
            benchmark_receipt_released_at=datetime(
                2026, 9, 17, 8, 20, tzinfo=timezone.utc
            ),
            benchmark_receipt_superseded_at=None,
            constructed_at=CONSTRUCTED_AT,
            owner_contract_reference=(
                "released_owner_contract:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
            ),
            owner_contract_version=10,
            owner_contract_digest="9" * 64,
            owner_contract_released_at=datetime(2026, 9, 17, 9, 10, tzinfo=timezone.utc),
            released_at=datetime(2026, 9, 17, 9, 20, tzinfo=timezone.utc),
        )
