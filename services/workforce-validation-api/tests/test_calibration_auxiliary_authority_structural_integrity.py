"""Structural-integrity regressions for calibration auxiliary owner evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy

from orgmetra_workforce_validation_api import ValidationPrincipal
import orgmetra_workforce_validation_api.scientific_authority as target
from orgmetra_workforce_validation_api.scientific_authority import (
    CalibrationAuxiliaryAuthorityIntegrityError,
    CalibrationAuxiliaryAuthorityRecord,
    resolve_calibration_auxiliary_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000c1")
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 8, 31, tzinfo=timezone.utc)
AUTHORIZATION_RECEIPT_RELEASED_AT = datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
AUTHORIZED_FROM = datetime(2026, 9, 1, tzinfo=timezone.utc)
AUTHORIZED_TO = datetime(2026, 10, 1, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, tzinfo=timezone.utc)


class _ReadPort:
    """Return configured persisted evidence through the auxiliary owner capability."""

    def __init__(self, result: object) -> None:
        self.result = result

    def read_calibration_auxiliary_authority(self, **_: object) -> object:
        """Return the configured owner evidence."""
        return self.result


def _record() -> CalibrationAuxiliaryAuthorityRecord:
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
        owner_contract_released_at=OWNER_CONTRACT_RELEASED_AT,
        authorization_receipt_reference=(
            "scientific_data_authorization:55555555-5555-4555-8555-555555555555"
        ),
        authorization_receipt_digest="4" * 64,
        authorization_receipt_released_at=AUTHORIZATION_RECEIPT_RELEASED_AT,
        scientific_use_receipt_reference=(
            "scientific_use_receipt:66666666-6666-4666-8666-666666666666"
        ),
        scientific_use_receipt_digest="5" * 64,
        scientific_use_at=USED_AT,
        authorized_from=AUTHORIZED_FROM,
        authorized_to=AUTHORIZED_TO,
    )


def _resolve(result: object) -> object:
    return resolve_calibration_auxiliary_authority(
        principal=ValidationPrincipal(
            tenant_record_id=TENANT,
            actor_reference="person:validation-analyst-1",
            granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
        ),
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
        authorization_receipt_reference=(
            "scientific_data_authorization:55555555-5555-4555-8555-555555555555"
        ),
        authorization_receipt_digest="4" * 64,
        scientific_use_receipt_reference=(
            "scientific_use_receipt:66666666-6666-4666-8666-666666666666"
        ),
        scientific_use_receipt_digest="5" * 64,
        used_at=USED_AT,
        purpose_code="selection_validity_analysis",
        policy=PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="calibration-authority-read-v1",
            resource_kind="calibration_auxiliary_authority",
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
        CalibrationAuxiliaryAuthorityRecord,
        tuple(canonical) + ("hidden-owner-coordinate",),
    )

    with pytest.raises(CalibrationAuxiliaryAuthorityIntegrityError):
        _resolve(forged)


def test_truncated_exact_typed_tuple_maps_to_integrity_error() -> None:
    canonical = _record()
    forged = tuple.__new__(CalibrationAuxiliaryAuthorityRecord, tuple(canonical)[:-1])

    with pytest.raises(CalibrationAuxiliaryAuthorityIntegrityError):
        _resolve(forged)
