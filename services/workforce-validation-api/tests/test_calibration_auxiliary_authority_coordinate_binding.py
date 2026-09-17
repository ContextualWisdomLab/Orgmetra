"""RED contract for exact calibration auxiliary authority coordinates."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.scientific_authority import (
    CalibrationAuxiliaryAuthorityIntegrityError,
    CalibrationAuxiliaryAuthorityRecord,
    resolve_calibration_auxiliary_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000c1")
AUTHORITY_REFERENCE = "scientific_auxiliary_authority:11111111-1111-4111-8111-111111111111"
PROJECTION_REFERENCE = "calibration_auxiliary_projection:22222222-2222-4222-8222-222222222222"
PURPOSE_REFERENCE = "scientific_data_use_purpose:33333333-3333-4333-8333-333333333333"
OWNER_REFERENCE = "released_owner_contract:44444444-4444-4444-8444-444444444444"
AUTHORIZATION_REFERENCE = "scientific_data_authorization:55555555-5555-4555-8555-555555555555"
USE_REFERENCE = "scientific_use_receipt:66666666-6666-4666-8666-666666666666"
PROJECTION_DIGEST = "1" * 64
PURPOSE_DIGEST = "2" * 64
OWNER_DIGEST = "3" * 64
AUTHORIZATION_DIGEST = "4" * 64
USE_DIGEST = "5" * 64
USED_AT = datetime(2026, 9, 17, tzinfo=timezone.utc)

READ_FIELDS = frozenset(
    {
        "authority_reference",
        "auxiliary_projection_reference",
        "auxiliary_projection_digest",
        "scientific_purpose_reference",
        "scientific_purpose_digest",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "authorization_receipt_reference",
        "authorization_receipt_digest",
        "scientific_use_receipt_reference",
        "scientific_use_receipt_digest",
        "scientific_use_at",
        "authorized_from",
        "authorized_to",
    }
)


class _ReadPort:
    def __init__(self, result: CalibrationAuxiliaryAuthorityRecord) -> None:
        self.result = result

    def read_calibration_auxiliary_authority(self, **_: object) -> CalibrationAuxiliaryAuthorityRecord:
        return self.result


def _record(**overrides: object) -> CalibrationAuxiliaryAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "authority_reference": AUTHORITY_REFERENCE,
        "auxiliary_projection_reference": PROJECTION_REFERENCE,
        "auxiliary_projection_digest": PROJECTION_DIGEST,
        "scientific_purpose_reference": PURPOSE_REFERENCE,
        "scientific_purpose_digest": PURPOSE_DIGEST,
        "owner_contract_reference": OWNER_REFERENCE,
        "owner_contract_version": 7,
        "owner_contract_digest": OWNER_DIGEST,
        "authorization_receipt_reference": AUTHORIZATION_REFERENCE,
        "authorization_receipt_digest": AUTHORIZATION_DIGEST,
        "scientific_use_receipt_reference": USE_REFERENCE,
        "scientific_use_receipt_digest": USE_DIGEST,
        "scientific_use_at": USED_AT,
        "authorized_from": datetime(2026, 9, 1, tzinfo=timezone.utc),
        "authorized_to": datetime(2026, 10, 1, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return CalibrationAuxiliaryAuthorityRecord(**values)


def _resolve(*, record: CalibrationAuxiliaryAuthorityRecord, **overrides: object) -> object:
    values: dict[str, object] = {
        "principal": ValidationPrincipal(
            tenant_record_id=TENANT,
            actor_reference="person:validation-analyst-1",
            granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
        ),
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "authority_reference": AUTHORITY_REFERENCE,
        "auxiliary_projection_reference": PROJECTION_REFERENCE,
        "auxiliary_projection_digest": PROJECTION_DIGEST,
        "scientific_purpose_reference": PURPOSE_REFERENCE,
        "scientific_purpose_digest": PURPOSE_DIGEST,
        "owner_contract_reference": OWNER_REFERENCE,
        "owner_contract_version": 7,
        "owner_contract_digest": OWNER_DIGEST,
        "authorization_receipt_reference": AUTHORIZATION_REFERENCE,
        "authorization_receipt_digest": AUTHORIZATION_DIGEST,
        "scientific_use_receipt_reference": USE_REFERENCE,
        "scientific_use_receipt_digest": USE_DIGEST,
        "used_at": USED_AT,
        "purpose_code": "selection_validity_analysis",
        "policy": PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="calibration-authority-read-v1",
            resource_kind="calibration_auxiliary_authority",
            purpose_code="selection_validity_analysis",
            operation_code="read",
            required_scope_code="orgmetra.workforce_validation.read",
            permitted_fields=READ_FIELDS,
        ),
        "read_port": _ReadPort(record),
    }
    values.update(overrides)
    return resolve_calibration_auxiliary_authority(**values)


def test_exact_leaf_coordinates_are_accepted() -> None:
    view = _resolve(record=_record())
    assert dict(view.fields)["authority_reference"] == AUTHORITY_REFERENCE
    assert dict(view.fields)["owner_contract_digest"] == OWNER_DIGEST
    assert dict(view.fields)["authorization_receipt_reference"] == AUTHORIZATION_REFERENCE
    assert dict(view.fields)["scientific_use_receipt_reference"] == USE_REFERENCE


@pytest.mark.parametrize(
    ("record_overrides", "request_overrides"),
    [
        (
            {"authority_reference": "scientific_auxiliary_authority:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"},
            {},
        ),
        ({"owner_contract_digest": "a" * 64}, {}),
        (
            {"authorization_receipt_reference": "scientific_data_authorization:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"},
            {},
        ),
        (
            {"scientific_use_receipt_reference": "scientific_use_receipt:cccccccc-cccc-4ccc-8ccc-cccccccccccc"},
            {},
        ),
    ],
)
def test_owner_evidence_cannot_substitute_unrequested_leaf_coordinates(
    record_overrides: dict[str, object], request_overrides: dict[str, object]
) -> None:
    with pytest.raises(CalibrationAuxiliaryAuthorityIntegrityError):
        _resolve(record=_record(**record_overrides), **request_overrides)
