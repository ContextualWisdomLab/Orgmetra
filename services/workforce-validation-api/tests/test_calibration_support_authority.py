"""Regression contract for released calibration supporting-authority chronology."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from inspect import signature
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.calibration_support_authority import (
    CalibrationSupportAuthorityReadPort,
    CalibrationSupportAuthorityRecord,
    resolve_calibration_support_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000f2")
AUX_OWNER_RELEASED_AT = datetime(2026, 9, 17, 7, 50, tzinfo=timezone.utc)
AUX_AUTH_RELEASED_AT = datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc)
AUX_AUTHORIZED_FROM = datetime(2026, 9, 17, 8, 10, tzinfo=timezone.utc)
AUX_USE_AT = datetime(2026, 9, 17, 8, 30, tzinfo=timezone.utc)
BENCHMARK_OWNER_RELEASED_AT = datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc)
BENCHMARK_RECEIPT_RELEASED_AT = datetime(2026, 9, 17, 8, 20, tzinfo=timezone.utc)
BENCHMARK_REFERENCE_AT = datetime(2026, 9, 17, 8, 15, tzinfo=timezone.utc)
CONSTRUCTED_AT = datetime(2026, 9, 17, 9, 0, tzinfo=timezone.utc)
OWNER_RELEASED_AT = datetime(2026, 9, 17, 9, 10, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 9, 20, tzinfo=timezone.utc)


def _record(**overrides: object) -> CalibrationSupportAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "support_authority_reference": (
            "calibration_support_authority:10101010-1010-4010-8010-101010101010"
        ),
        "support_authority_digest": "0" * 64,
        "evidence_version": 1,
        "calibration_receipt_reference": (
            "calibration_adjustment_receipt:11111111-1111-4111-8111-111111111111"
        ),
        "calibration_receipt_digest": "1" * 64,
        "auxiliary_authority_reference": (
            "scientific_auxiliary_authority:22222222-2222-4222-8222-222222222222"
        ),
        "auxiliary_projection_reference": (
            "calibration_auxiliary_projection:33333333-3333-4333-8333-333333333333"
        ),
        "auxiliary_projection_version": 3,
        "auxiliary_projection_digest": "2" * 64,
        "auxiliary_purpose_reference": (
            "scientific_data_use_purpose:44444444-4444-4444-8444-444444444444"
        ),
        "auxiliary_purpose_digest": "3" * 64,
        "auxiliary_owner_contract_reference": (
            "released_owner_contract:55555555-5555-4555-8555-555555555555"
        ),
        "auxiliary_owner_contract_version": 5,
        "auxiliary_owner_contract_digest": "4" * 64,
        "auxiliary_owner_contract_released_at": AUX_OWNER_RELEASED_AT,
        "auxiliary_authorization_receipt_reference": (
            "scientific_data_authorization:66666666-6666-4666-8666-666666666666"
        ),
        "auxiliary_authorization_receipt_digest": "5" * 64,
        "auxiliary_authorization_receipt_released_at": AUX_AUTH_RELEASED_AT,
        "auxiliary_scientific_use_receipt_reference": (
            "scientific_use_receipt:77777777-7777-4777-8777-777777777777"
        ),
        "auxiliary_scientific_use_receipt_digest": "6" * 64,
        "auxiliary_scientific_use_at": AUX_USE_AT,
        "auxiliary_authorized_from": AUX_AUTHORIZED_FROM,
        "auxiliary_authorized_to": datetime(2026, 10, 1, tzinfo=timezone.utc),
        "benchmark_receipt_reference": (
            "calibration_benchmark_receipt:88888888-8888-4888-8888-888888888888"
        ),
        "benchmark_receipt_version": 8,
        "benchmark_receipt_digest": "7" * 64,
        "benchmark_owner_contract_reference": (
            "released_owner_contract:99999999-9999-4999-8999-999999999999"
        ),
        "benchmark_owner_contract_version": 9,
        "benchmark_owner_contract_digest": "8" * 64,
        "benchmark_owner_contract_released_at": BENCHMARK_OWNER_RELEASED_AT,
        "benchmark_reference_at": BENCHMARK_REFERENCE_AT,
        "benchmark_receipt_released_at": BENCHMARK_RECEIPT_RELEASED_AT,
        "benchmark_receipt_superseded_at": None,
        "constructed_at": CONSTRUCTED_AT,
        "owner_contract_reference": (
            "released_owner_contract:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        ),
        "owner_contract_version": 10,
        "owner_contract_digest": "9" * 64,
        "owner_contract_released_at": OWNER_RELEASED_AT,
        "released_at": RELEASED_AT,
    }
    values.update(overrides)
    return CalibrationSupportAuthorityRecord(**values)  # type: ignore[arg-type]


def test_support_chronology_is_owner_evidence_not_lookup_authority() -> None:
    record = _record()
    read_parameters = signature(
        CalibrationSupportAuthorityReadPort.read_calibration_support_authority
    ).parameters
    resolver_parameters = signature(resolve_calibration_support_authority).parameters

    owner_resolved = {
        "auxiliary_owner_contract_released_at",
        "auxiliary_authorization_receipt_released_at",
        "auxiliary_authorized_from",
        "auxiliary_authorized_to",
        "benchmark_owner_contract_released_at",
        "benchmark_receipt_released_at",
        "benchmark_receipt_superseded_at",
        "owner_contract_released_at",
        "released_at",
    }
    for field_name in owner_resolved:
        assert hasattr(record, field_name)
        assert field_name not in read_parameters
        assert field_name not in resolver_parameters


def test_auxiliary_evidence_must_exist_before_the_committed_scientific_use() -> None:
    with pytest.raises(ValueError, match="authorization receipt must be released no later"):
        _record(auxiliary_authorization_receipt_released_at=AUX_USE_AT + timedelta(seconds=1))

    with pytest.raises(ValueError, match="auxiliary owner contract cannot postdate authorization"):
        _record(auxiliary_owner_contract_released_at=AUX_AUTH_RELEASED_AT + timedelta(seconds=1))


def test_auxiliary_use_must_be_inside_owner_resolved_authorization_interval() -> None:
    with pytest.raises(ValueError, match="auxiliary scientific use must fall inside"):
        _record(auxiliary_authorized_from=AUX_USE_AT + timedelta(seconds=1))

    with pytest.raises(ValueError, match="auxiliary scientific use must fall inside"):
        _record(auxiliary_authorized_to=AUX_USE_AT)


def test_supporting_evidence_must_exist_before_calibration_construction() -> None:
    with pytest.raises(ValueError, match="benchmark receipt must be released no later"):
        _record(benchmark_receipt_released_at=CONSTRUCTED_AT + timedelta(seconds=1))

    with pytest.raises(ValueError, match="auxiliary scientific use cannot be later"):
        _record(auxiliary_scientific_use_at=CONSTRUCTED_AT + timedelta(seconds=1))


def test_superseded_benchmark_cannot_support_later_calibration_construction() -> None:
    with pytest.raises(ValueError, match="superseded benchmark cannot support calibration"):
        _record(benchmark_receipt_superseded_at=CONSTRUCTED_AT)


def test_support_chronology_requires_timezone_aware_owner_evidence() -> None:
    with pytest.raises(ValueError):
        _record(benchmark_receipt_released_at=datetime(2026, 9, 17, 8, 20))


def test_application_owner_contract_cannot_retroactively_authorize_support_binding() -> None:
    with pytest.raises(ValueError, match="owner contract cannot be released after support evidence"):
        _record(owner_contract_released_at=RELEASED_AT + timedelta(seconds=1))
