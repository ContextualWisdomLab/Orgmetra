"""Fail-closed contract for resolving calibration auxiliary-use authority."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.scientific_authority import (
    CalibrationAuxiliaryAuthorityIntegrityError,
    CalibrationAuxiliaryAuthorityNotFound,
    CalibrationAuxiliaryAuthorityReadPort,
    CalibrationAuxiliaryAuthorityRecord,
    CalibrationAuxiliaryAuthorityView,
    resolve_calibration_auxiliary_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000002")
STUDY = UUID("00000000-0000-7000-8000-0000000000c1")
OTHER_STUDY = UUID("00000000-0000-7000-8000-0000000000c2")
AUTHORITY_REFERENCE = (
    "scientific_auxiliary_authority:11111111-1111-4111-8111-111111111111"
)
PROJECTION_REFERENCE = (
    "calibration_auxiliary_projection:22222222-2222-4222-8222-222222222222"
)
PROJECTION_VERSION = 4
PURPOSE_REFERENCE = (
    "scientific_data_use_purpose:33333333-3333-4333-8333-333333333333"
)
OWNER_CONTRACT_REFERENCE = (
    "released_owner_contract:44444444-4444-4444-8444-444444444444"
)
AUTHORIZATION_REFERENCE = (
    "scientific_data_authorization:55555555-5555-4555-8555-555555555555"
)
SCIENTIFIC_USE_REFERENCE = (
    "scientific_use_receipt:66666666-6666-4666-8666-666666666666"
)
PROJECTION_DIGEST = "1" * 64
PURPOSE_DIGEST = "2" * 64
OWNER_CONTRACT_DIGEST = "3" * 64
AUTHORIZATION_DIGEST = "4" * 64
SCIENTIFIC_USE_DIGEST = "5" * 64
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 8, 31, tzinfo=timezone.utc)
AUTHORIZED_FROM = datetime(2026, 9, 1, tzinfo=timezone.utc)
AUTHORIZED_TO = datetime(2026, 10, 1, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "authority_reference",
        "auxiliary_projection_reference",
        "auxiliary_projection_version",
        "auxiliary_projection_digest",
        "scientific_purpose_reference",
        "scientific_purpose_digest",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
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
    """Return one configured authority record and retain the exact lookup coordinates."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[tuple[object, ...]] = []

    def read_calibration_auxiliary_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        authority_reference: str,
        auxiliary_projection_reference: str,
        auxiliary_projection_version: int,
        auxiliary_projection_digest: str,
        scientific_purpose_reference: str,
        scientific_purpose_digest: str,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
        authorization_receipt_reference: str,
        authorization_receipt_digest: str,
        scientific_use_receipt_reference: str,
        scientific_use_receipt_digest: str,
    ) -> object:
        """Capture the owner lookup and return the configured result."""
        self.calls.append(
            (
                tenant_record_id,
                validity_study_id,
                authority_reference,
                auxiliary_projection_reference,
                auxiliary_projection_version,
                auxiliary_projection_digest,
                scientific_purpose_reference,
                scientific_purpose_digest,
                owner_contract_reference,
                owner_contract_version,
                owner_contract_digest,
                authorization_receipt_reference,
                authorization_receipt_digest,
                scientific_use_receipt_reference,
                scientific_use_receipt_digest,
            )
        )
        return self.result


class _NoReadMethod:
    """Deliberately fail the owner-port protocol."""


class _ProtocolOnly(CalibrationAuxiliaryAuthorityReadPort):
    """Inherit only the Protocol placeholder, not a concrete owner capability."""


class _DescriptorReadPort:
    """Expose a descriptor that must be rejected without executing it."""

    @property
    def read_calibration_auxiliary_authority(self) -> object:
        raise AssertionError("descriptor must not execute")


def _principal(*, tenant_record_id: UUID = TENANT) -> ValidationPrincipal:
    return ValidationPrincipal(
        tenant_record_id=tenant_record_id,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )


def _policy(*, purpose_code: str = "selection_validity_analysis") -> PurposeBoundAccessPolicy:
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="calibration-authority-read-v1",
        resource_kind="calibration_auxiliary_authority",
        purpose_code=purpose_code,
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def _record(**overrides: object) -> CalibrationAuxiliaryAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "authority_reference": AUTHORITY_REFERENCE,
        "auxiliary_projection_reference": PROJECTION_REFERENCE,
        "auxiliary_projection_version": PROJECTION_VERSION,
        "auxiliary_projection_digest": PROJECTION_DIGEST,
        "scientific_purpose_reference": PURPOSE_REFERENCE,
        "scientific_purpose_digest": PURPOSE_DIGEST,
        "owner_contract_reference": OWNER_CONTRACT_REFERENCE,
        "owner_contract_version": 7,
        "owner_contract_digest": OWNER_CONTRACT_DIGEST,
        "owner_contract_released_at": OWNER_CONTRACT_RELEASED_AT,
        "authorization_receipt_reference": AUTHORIZATION_REFERENCE,
        "authorization_receipt_digest": AUTHORIZATION_DIGEST,
        "scientific_use_receipt_reference": SCIENTIFIC_USE_REFERENCE,
        "scientific_use_receipt_digest": SCIENTIFIC_USE_DIGEST,
        "scientific_use_at": USED_AT,
        "authorized_from": AUTHORIZED_FROM,
        "authorized_to": AUTHORIZED_TO,
    }
    values.update(overrides)
    return CalibrationAuxiliaryAuthorityRecord(**values)


def _resolve(*, read_port: object, **overrides: object) -> CalibrationAuxiliaryAuthorityView:
    values: dict[str, object] = {
        "principal": _principal(),
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "authority_reference": AUTHORITY_REFERENCE,
        "auxiliary_projection_reference": PROJECTION_REFERENCE,
        "auxiliary_projection_version": PROJECTION_VERSION,
        "auxiliary_projection_digest": PROJECTION_DIGEST,
        "scientific_purpose_reference": PURPOSE_REFERENCE,
        "scientific_purpose_digest": PURPOSE_DIGEST,
        "owner_contract_reference": OWNER_CONTRACT_REFERENCE,
        "owner_contract_version": 7,
        "owner_contract_digest": OWNER_CONTRACT_DIGEST,
        "authorization_receipt_reference": AUTHORIZATION_REFERENCE,
        "authorization_receipt_digest": AUTHORIZATION_DIGEST,
        "scientific_use_receipt_reference": SCIENTIFIC_USE_REFERENCE,
        "scientific_use_receipt_digest": SCIENTIFIC_USE_DIGEST,
        "used_at": USED_AT,
        "purpose_code": "selection_validity_analysis",
        "policy": _policy(),
        "read_port": read_port,
    }
    values.update(overrides)
    return resolve_calibration_auxiliary_authority(**values)


def test_resolution_authorizes_then_returns_minimized_corroborated_evidence() -> None:
    port = _ReadPort(_record())

    view = _resolve(read_port=port)

    assert isinstance(port, CalibrationAuxiliaryAuthorityReadPort)
    assert port.calls == [
        (
            TENANT,
            STUDY,
            AUTHORITY_REFERENCE,
            PROJECTION_REFERENCE,
            PROJECTION_VERSION,
            PROJECTION_DIGEST,
            PURPOSE_REFERENCE,
            PURPOSE_DIGEST,
            OWNER_CONTRACT_REFERENCE,
            7,
            OWNER_CONTRACT_DIGEST,
            AUTHORIZATION_REFERENCE,
            AUTHORIZATION_DIGEST,
            SCIENTIFIC_USE_REFERENCE,
            SCIENTIFIC_USE_DIGEST,
        )
    ]
    assert view.tenant_record_id == TENANT
    assert view.validity_study_id == STUDY
    assert view.fields == (
        ("authority_reference", AUTHORITY_REFERENCE),
        ("authorization_receipt_digest", AUTHORIZATION_DIGEST),
        ("authorization_receipt_reference", AUTHORIZATION_REFERENCE),
        ("authorized_from", AUTHORIZED_FROM),
        ("authorized_to", AUTHORIZED_TO),
        ("auxiliary_projection_digest", PROJECTION_DIGEST),
        ("auxiliary_projection_reference", PROJECTION_REFERENCE),
        ("auxiliary_projection_version", PROJECTION_VERSION),
        ("owner_contract_digest", OWNER_CONTRACT_DIGEST),
        ("owner_contract_reference", OWNER_CONTRACT_REFERENCE),
        ("owner_contract_released_at", OWNER_CONTRACT_RELEASED_AT),
        ("owner_contract_version", 7),
        ("scientific_purpose_digest", PURPOSE_DIGEST),
        ("scientific_purpose_reference", PURPOSE_REFERENCE),
        ("scientific_use_at", USED_AT),
        ("scientific_use_receipt_digest", SCIENTIFIC_USE_DIGEST),
        ("scientific_use_receipt_reference", SCIENTIFIC_USE_REFERENCE),
    )


def test_authorization_denial_happens_before_owner_resolution() -> None:
    port = _ReadPort(_record())

    with pytest.raises(AuthorizationDeniedError):
        _resolve(read_port=port, policy=_policy(purpose_code="audit_review"))

    assert port.calls == []


def test_missing_or_noncanonical_owner_evidence_fails_closed() -> None:
    with pytest.raises(CalibrationAuxiliaryAuthorityNotFound):
        _resolve(read_port=_ReadPort(None))

    with pytest.raises(CalibrationAuxiliaryAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(object()))


@pytest.mark.parametrize(
    ("record_overrides", "request_overrides"),
    [
        ({"tenant_record_id": OTHER_TENANT}, {}),
        ({"validity_study_id": OTHER_STUDY}, {}),
        (
            {
                "authority_reference": (
                    "scientific_auxiliary_authority:dddddddd-dddd-4ddd-8ddd-dddddddddddd"
                )
            },
            {},
        ),
        (
            {
                "auxiliary_projection_reference": (
                    "calibration_auxiliary_projection:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
                )
            },
            {},
        ),
        ({"auxiliary_projection_version": PROJECTION_VERSION + 1}, {}),
        ({"auxiliary_projection_digest": "a" * 64}, {}),
        (
            {
                "scientific_purpose_reference": (
                    "scientific_data_use_purpose:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
                )
            },
            {},
        ),
        ({"scientific_purpose_digest": "b" * 64}, {}),
        (
            {
                "owner_contract_reference": (
                    "released_owner_contract:cccccccc-cccc-4ccc-8ccc-cccccccccccc"
                )
            },
            {},
        ),
        ({"owner_contract_version": 8}, {}),
        ({"owner_contract_digest": "c" * 64}, {}),
        (
            {
                "authorization_receipt_reference": (
                    "scientific_data_authorization:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
                )
            },
            {},
        ),
        ({"authorization_receipt_digest": "c" * 64}, {}),
        (
            {
                "scientific_use_receipt_reference": (
                    "scientific_use_receipt:ffffffff-ffff-4fff-8fff-ffffffffffff"
                )
            },
            {},
        ),
        ({"scientific_use_receipt_digest": "d" * 64}, {}),
        ({}, {"used_at": USED_AT + timedelta(seconds=1)}),
    ],
)
def test_resolved_authority_must_match_every_requested_coordinate_and_use_time(
    record_overrides: dict[str, object], request_overrides: dict[str, object]
) -> None:
    with pytest.raises(CalibrationAuxiliaryAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(**record_overrides)), **request_overrides)


def test_record_requires_owner_resolved_use_time_inside_authorization_interval() -> None:
    for invalid_use in (
        AUTHORIZED_FROM - timedelta(seconds=1),
        AUTHORIZED_TO,
    ):
        with pytest.raises(ValueError):
            _record(scientific_use_at=invalid_use)


def test_open_ended_authority_interval_accepts_later_owner_resolved_use() -> None:
    later_use = AUTHORIZED_TO + timedelta(days=30)
    view = _resolve(
        read_port=_ReadPort(
            _record(
                scientific_use_at=later_use,
                authorized_to=None,
            )
        ),
        used_at=later_use,
    )
    assert dict(view.fields)["authorized_to"] is None
    assert dict(view.fields)["scientific_use_at"] == later_use


@pytest.mark.parametrize(
    ("key", "value", "error"),
    [
        ("principal", object(), TypeError),
        ("policy", object(), TypeError),
        ("read_port", _NoReadMethod(), TypeError),
        ("read_port", _ProtocolOnly(), TypeError),
        ("read_port", _DescriptorReadPort(), TypeError),
        ("tenant_record_id", "not-a-uuid", ValueError),
        ("validity_study_id", UUID(int=0), ValueError),
        ("authority_reference", "wrong:authority", ValueError),
        ("auxiliary_projection_reference", "wrong:projection", ValueError),
        ("auxiliary_projection_version", 0, ValueError),
        ("auxiliary_projection_version", True, ValueError),
        ("auxiliary_projection_digest", "ABC", ValueError),
        ("scientific_purpose_reference", "wrong:purpose", ValueError),
        ("scientific_purpose_digest", "2" * 63, ValueError),
        ("owner_contract_reference", "wrong:contract", ValueError),
        ("owner_contract_version", True, ValueError),
        ("owner_contract_digest", "3" * 63, ValueError),
        ("authorization_receipt_reference", "wrong:authorization", ValueError),
        ("authorization_receipt_digest", "4" * 65, ValueError),
        ("scientific_use_receipt_reference", "wrong:use", ValueError),
        ("scientific_use_receipt_digest", "5" * 65, ValueError),
        ("used_at", datetime(2026, 9, 17), ValueError),
        ("purpose_code", "Selection Validity Analysis", ValueError),
    ],
)
def test_invalid_request_or_dependency_fails_before_owner_resolution(
    key: str, value: object, error: type[Exception]
) -> None:
    port = _ReadPort(_record())
    overrides = {key: value}
    if key == "read_port":
        port = value  # type: ignore[assignment]
        overrides = {}
    with pytest.raises(error):
        _resolve(read_port=port, **overrides)
    if isinstance(port, _ReadPort):
        assert port.calls == []


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("tenant_record_id", UUID(int=0)),
        ("validity_study_id", "not-a-uuid"),
        ("authority_reference", "wrong:authority"),
        ("auxiliary_projection_reference", "wrong:projection"),
        ("auxiliary_projection_version", 0),
        ("auxiliary_projection_version", True),
        ("auxiliary_projection_digest", "1" * 63),
        ("scientific_purpose_reference", "wrong:purpose"),
        ("scientific_purpose_digest", "2" * 65),
        ("owner_contract_reference", "wrong:contract"),
        ("owner_contract_version", 0),
        ("owner_contract_digest", "3" * 63),
        ("owner_contract_released_at", datetime(2026, 8, 31)),
        ("authorization_receipt_reference", "wrong:authorization"),
        ("authorization_receipt_digest", "4" * 63),
        ("scientific_use_receipt_reference", "wrong:use"),
        ("scientific_use_receipt_digest", "5" * 63),
        ("scientific_use_at", datetime(2026, 9, 17)),
        ("authorized_from", datetime(2026, 9, 1)),
        ("authorized_to", "not-a-datetime"),
    ],
)
def test_record_rejects_invalid_authority_evidence(key: str, value: object) -> None:
    with pytest.raises(ValueError):
        _record(**{key: value})


def test_record_rejects_empty_or_reversed_authorization_interval() -> None:
    for invalid_end in (AUTHORIZED_FROM, AUTHORIZED_FROM - timedelta(seconds=1)):
        with pytest.raises(ValueError):
            _record(authorized_to=invalid_end)


def test_record_and_view_are_structurally_immutable_and_uuid_views_are_detached() -> None:
    tenant = UUID(str(TENANT))
    record = _record(tenant_record_id=tenant)
    object.__setattr__(tenant, "int", OTHER_TENANT.int)
    assert record.tenant_record_id == TENANT

    with pytest.raises(AttributeError):
        object.__setattr__(record, "owner_contract_version", 999)

    view = _resolve(read_port=_ReadPort(record))
    returned_tenant = view.tenant_record_id
    object.__setattr__(returned_tenant, "int", OTHER_TENANT.int)
    assert view.tenant_record_id == TENANT

    with pytest.raises(AttributeError):
        object.__setattr__(view, "fields", ())
    with pytest.raises(TypeError):
        CalibrationAuxiliaryAuthorityView(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            fields=(),
        )
