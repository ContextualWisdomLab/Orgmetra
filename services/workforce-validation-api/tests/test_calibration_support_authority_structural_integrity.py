"""Structural-integrity regressions for calibration support owner evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy

from orgmetra_workforce_validation_api import ValidationPrincipal
import orgmetra_workforce_validation_api.calibration_support_authority as target
from orgmetra_workforce_validation_api.calibration_support_authority import (
    CalibrationSupportAuthorityIntegrityError,
    CalibrationSupportAuthorityRecord,
    resolve_calibration_support_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000f2")
AUX_OWNER_RELEASED_AT = datetime(2026, 9, 17, 7, 50, tzinfo=timezone.utc)
AUX_AUTH_RELEASED_AT = datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc)
AUX_AUTHORIZED_FROM = datetime(2026, 9, 17, 8, 10, tzinfo=timezone.utc)
AUX_AUTHORIZED_TO = datetime(2026, 10, 1, tzinfo=timezone.utc)
AUX_USE_AT = datetime(2026, 9, 17, 8, 30, tzinfo=timezone.utc)
BENCHMARK_OWNER_RELEASED_AT = datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc)
BENCHMARK_RECEIPT_RELEASED_AT = datetime(2026, 9, 17, 8, 20, tzinfo=timezone.utc)
BENCHMARK_REFERENCE_AT = datetime(2026, 9, 17, 8, 15, tzinfo=timezone.utc)
CONSTRUCTED_AT = datetime(2026, 9, 17, 9, 0, tzinfo=timezone.utc)
OWNER_RELEASED_AT = datetime(2026, 9, 17, 9, 10, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 9, 20, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, 10, 0, tzinfo=timezone.utc)


class _ReadPort:
    """Return configured persisted evidence through the owner-read capability."""

    def __init__(self, result: object) -> None:
        self.result = result

    def read_calibration_support_authority(self, **_: object) -> object:
        """Return the configured owner evidence."""
        return self.result


def _record() -> CalibrationSupportAuthorityRecord:
    return CalibrationSupportAuthorityRecord(
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
        auxiliary_owner_contract_released_at=AUX_OWNER_RELEASED_AT,
        auxiliary_authorization_receipt_reference=(
            "scientific_data_authorization:66666666-6666-4666-8666-666666666666"
        ),
        auxiliary_authorization_receipt_digest="5" * 64,
        auxiliary_authorization_receipt_released_at=AUX_AUTH_RELEASED_AT,
        auxiliary_scientific_use_receipt_reference=(
            "scientific_use_receipt:77777777-7777-4777-8777-777777777777"
        ),
        auxiliary_scientific_use_receipt_digest="6" * 64,
        auxiliary_scientific_use_at=AUX_USE_AT,
        auxiliary_authorized_from=AUX_AUTHORIZED_FROM,
        auxiliary_authorized_to=AUX_AUTHORIZED_TO,
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
        benchmark_owner_contract_released_at=BENCHMARK_OWNER_RELEASED_AT,
        benchmark_reference_at=BENCHMARK_REFERENCE_AT,
        benchmark_receipt_released_at=BENCHMARK_RECEIPT_RELEASED_AT,
        benchmark_receipt_superseded_at=None,
        constructed_at=CONSTRUCTED_AT,
        owner_contract_reference=(
            "released_owner_contract:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        ),
        owner_contract_version=10,
        owner_contract_digest="9" * 64,
        owner_contract_released_at=OWNER_RELEASED_AT,
        released_at=RELEASED_AT,
    )


def _resolve(result: object) -> object:
    return resolve_calibration_support_authority(
        principal=ValidationPrincipal(
            tenant_record_id=TENANT,
            actor_reference="person:validation-analyst-1",
            granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
        ),
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
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
        auxiliary_authorization_receipt_reference=(
            "scientific_data_authorization:66666666-6666-4666-8666-666666666666"
        ),
        auxiliary_authorization_receipt_digest="5" * 64,
        auxiliary_scientific_use_receipt_reference=(
            "scientific_use_receipt:77777777-7777-4777-8777-777777777777"
        ),
        auxiliary_scientific_use_receipt_digest="6" * 64,
        auxiliary_scientific_use_at=AUX_USE_AT,
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
        benchmark_reference_at=BENCHMARK_REFERENCE_AT,
        constructed_at=CONSTRUCTED_AT,
        owner_contract_reference=(
            "released_owner_contract:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        ),
        owner_contract_version=10,
        owner_contract_digest="9" * 64,
        used_at=USED_AT,
        purpose_code="selection_validity_analysis",
        policy=PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="calibration-support-read-v1",
            resource_kind="calibration_support_authority",
            purpose_code="selection_validity_analysis",
            operation_code="read",
            required_scope_code="orgmetra.workforce_validation.read",
            permitted_fields=target._READ_FIELDS,
        ),
        read_port=_ReadPort(result),
    )


def test_hidden_trailing_tuple_structure_fails_closed() -> None:
    canonical = _record()
    forged = tuple.__new__(
        CalibrationSupportAuthorityRecord,
        tuple(canonical) + ("hidden-owner-coordinate",),
    )

    with pytest.raises(CalibrationSupportAuthorityIntegrityError):
        _resolve(forged)


def test_truncated_exact_typed_tuple_maps_to_integrity_error() -> None:
    canonical = _record()
    forged = tuple.__new__(CalibrationSupportAuthorityRecord, tuple(canonical)[:-1])

    with pytest.raises(CalibrationSupportAuthorityIntegrityError):
        _resolve(forged)
