"""Fail-closed and branch coverage for calibration supporting-authority evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy

from orgmetra_workforce_validation_api import ValidationPrincipal
import orgmetra_workforce_validation_api.calibration_support_authority as target
from orgmetra_workforce_validation_api.calibration_support_authority import (
    CalibrationSupportAuthorityIntegrityError,
    CalibrationSupportAuthorityNotFound,
    CalibrationSupportAuthorityReadPort,
    CalibrationSupportAuthorityRecord,
    CalibrationSupportAuthorityView,
    resolve_calibration_support_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000002")
STUDY = UUID("00000000-0000-7000-8000-0000000000f2")
OTHER_STUDY = UUID("00000000-0000-7000-8000-0000000000f3")
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
    """Return configured support evidence and retain whether persistence was invoked."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.calls = 0

    def read_calibration_support_authority(self, **_: object) -> object:
        """Return configured evidence after counting the owner read."""
        self.calls += 1
        return self.result


class _NoReadMethod:
    """Deliberately omit the owner-read capability."""


class _ProtocolOnly(CalibrationSupportAuthorityReadPort):
    """Inherit only the Protocol placeholder."""


class _DescriptorReadPort:
    """Expose a descriptor that must not execute during static capability inspection."""

    @property
    def read_calibration_support_authority(self) -> object:
        raise AssertionError("descriptor must not execute")


def _principal() -> ValidationPrincipal:
    return ValidationPrincipal(
        tenant_record_id=TENANT,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )


def _policy(*, purpose_code: str = "selection_validity_analysis") -> PurposeBoundAccessPolicy:
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="calibration-support-read-v1",
        resource_kind="calibration_support_authority",
        purpose_code=purpose_code,
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=target._READ_FIELDS,
    )


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
        "auxiliary_authorized_to": AUX_AUTHORIZED_TO,
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


def _resolve(*, read_port: object, **overrides: object) -> CalibrationSupportAuthorityView:
    values: dict[str, object] = {
        "principal": _principal(),
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
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
        "auxiliary_authorization_receipt_reference": (
            "scientific_data_authorization:66666666-6666-4666-8666-666666666666"
        ),
        "auxiliary_authorization_receipt_digest": "5" * 64,
        "auxiliary_scientific_use_receipt_reference": (
            "scientific_use_receipt:77777777-7777-4777-8777-777777777777"
        ),
        "auxiliary_scientific_use_receipt_digest": "6" * 64,
        "auxiliary_scientific_use_at": AUX_USE_AT,
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
        "benchmark_reference_at": BENCHMARK_REFERENCE_AT,
        "constructed_at": CONSTRUCTED_AT,
        "owner_contract_reference": (
            "released_owner_contract:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        ),
        "owner_contract_version": 10,
        "owner_contract_digest": "9" * 64,
        "used_at": USED_AT,
        "purpose_code": "selection_validity_analysis",
        "policy": _policy(),
        "read_port": read_port,
    }
    values.update(overrides)
    return resolve_calibration_support_authority(**values)  # type: ignore[arg-type]


def test_resolution_returns_complete_owner_resolved_support_chronology() -> None:
    port = _ReadPort(_record())
    view = _resolve(read_port=port)

    assert isinstance(port, CalibrationSupportAuthorityReadPort)
    assert port.calls == 1
    assert view.tenant_record_id == TENANT
    assert view.validity_study_id == STUDY
    fields = dict(view.fields)
    assert fields["support_authority_digest"] == "0" * 64
    assert fields["auxiliary_owner_contract_released_at"] == AUX_OWNER_RELEASED_AT
    assert fields["auxiliary_authorization_receipt_released_at"] == AUX_AUTH_RELEASED_AT
    assert fields["benchmark_receipt_released_at"] == BENCHMARK_RECEIPT_RELEASED_AT
    assert fields["benchmark_receipt_superseded_at"] is None
    assert fields["released_at"] == RELEASED_AT


def test_open_ended_auxiliary_interval_and_future_benchmark_cutover_remain_reproducible() -> None:
    future_cutover = CONSTRUCTED_AT + timedelta(hours=1)
    view = _resolve(
        read_port=_ReadPort(
            _record(
                auxiliary_authorized_to=None,
                benchmark_receipt_superseded_at=future_cutover,
            )
        )
    )
    fields = dict(view.fields)
    assert fields["auxiliary_authorized_to"] is None
    assert fields["benchmark_receipt_superseded_at"] == future_cutover


def test_authorization_denial_happens_before_owner_resolution() -> None:
    port = _ReadPort(_record())
    with pytest.raises(AuthorizationDeniedError):
        _resolve(read_port=port, policy=_policy(purpose_code="audit_review"))
    assert port.calls == 0


def test_missing_or_noncanonical_owner_evidence_fails_closed() -> None:
    with pytest.raises(CalibrationSupportAuthorityNotFound):
        _resolve(read_port=_ReadPort(None))
    with pytest.raises(CalibrationSupportAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(object()))


def test_owner_result_must_match_requested_coordinates() -> None:
    with pytest.raises(CalibrationSupportAuthorityIntegrityError, match="does not match"):
        _resolve(read_port=_ReadPort(_record(tenant_record_id=OTHER_TENANT)))
    with pytest.raises(CalibrationSupportAuthorityIntegrityError, match="does not match"):
        _resolve(read_port=_ReadPort(_record(validity_study_id=OTHER_STUDY)))
    with pytest.raises(CalibrationSupportAuthorityIntegrityError, match="does not match"):
        _resolve(read_port=_ReadPort(_record(calibration_receipt_digest="a" * 64)))


def test_support_binding_must_be_released_before_scientific_use() -> None:
    with pytest.raises(CalibrationSupportAuthorityIntegrityError, match="released before scientific use"):
        _resolve(read_port=_ReadPort(_record()), used_at=RELEASED_AT - timedelta(seconds=1))


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"evidence_version": 2}, "evidence_version must remain 1"),
        (
            {"auxiliary_owner_contract_released_at": AUX_AUTH_RELEASED_AT + timedelta(seconds=1)},
            "auxiliary owner contract cannot postdate authorization",
        ),
        (
            {"auxiliary_authorization_receipt_released_at": AUX_USE_AT + timedelta(seconds=1)},
            "authorization receipt must be released no later",
        ),
        (
            {"auxiliary_authorized_to": AUX_AUTHORIZED_FROM},
            "auxiliary_authorized_to must be later",
        ),
        (
            {"auxiliary_authorized_from": AUX_USE_AT + timedelta(seconds=1)},
            "auxiliary scientific use must fall inside",
        ),
        (
            {"auxiliary_authorized_to": AUX_USE_AT},
            "auxiliary scientific use must fall inside",
        ),
        (
            {"benchmark_owner_contract_released_at": BENCHMARK_RECEIPT_RELEASED_AT + timedelta(seconds=1)},
            "benchmark owner contract cannot postdate",
        ),
        (
            {"benchmark_receipt_superseded_at": BENCHMARK_RECEIPT_RELEASED_AT},
            "benchmark supersession must be later",
        ),
        (
            {"auxiliary_scientific_use_at": CONSTRUCTED_AT + timedelta(seconds=1)},
            "auxiliary scientific use cannot be later",
        ),
        (
            {"benchmark_reference_at": CONSTRUCTED_AT + timedelta(seconds=1)},
            "benchmark reference cannot be later",
        ),
        (
            {"benchmark_receipt_released_at": CONSTRUCTED_AT + timedelta(seconds=1)},
            "benchmark receipt must be released no later",
        ),
        (
            {"benchmark_receipt_superseded_at": CONSTRUCTED_AT},
            "superseded benchmark cannot support calibration",
        ),
        (
            {"owner_contract_released_at": RELEASED_AT + timedelta(seconds=1)},
            "owner contract cannot be released after support evidence",
        ),
        (
            {
                "owner_contract_released_at": CONSTRUCTED_AT - timedelta(seconds=2),
                "released_at": CONSTRUCTED_AT - timedelta(seconds=1),
            },
            "support evidence cannot be released before calibration construction",
        ),
    ],
)
def test_record_rejects_incoherent_owner_chronology(
    override: dict[str, object], match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        _record(**override)


def test_view_cannot_be_constructed_by_callers() -> None:
    with pytest.raises(TypeError):
        CalibrationSupportAuthorityView(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            fields=(),
        )


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
        ("calibration_receipt_reference", "wrong:calibration", ValueError),
        ("calibration_receipt_digest", "ABC", ValueError),
        ("auxiliary_authority_reference", "wrong:aux", ValueError),
        ("auxiliary_projection_reference", "wrong:projection", ValueError),
        ("auxiliary_projection_version", 0, ValueError),
        ("auxiliary_projection_digest", "2" * 63, ValueError),
        ("auxiliary_purpose_reference", "wrong:purpose", ValueError),
        ("auxiliary_purpose_digest", "3" * 63, ValueError),
        ("auxiliary_owner_contract_reference", "wrong:contract", ValueError),
        ("auxiliary_owner_contract_version", True, ValueError),
        ("auxiliary_owner_contract_digest", "4" * 63, ValueError),
        ("auxiliary_authorization_receipt_reference", "wrong:authorization", ValueError),
        ("auxiliary_authorization_receipt_digest", "5" * 63, ValueError),
        ("auxiliary_scientific_use_receipt_reference", "wrong:use", ValueError),
        ("auxiliary_scientific_use_receipt_digest", "6" * 63, ValueError),
        ("auxiliary_scientific_use_at", datetime(2026, 9, 17, 8, 30), ValueError),
        ("benchmark_receipt_reference", "wrong:benchmark", ValueError),
        ("benchmark_receipt_version", 0, ValueError),
        ("benchmark_receipt_digest", "7" * 63, ValueError),
        ("benchmark_owner_contract_reference", "wrong:contract", ValueError),
        ("benchmark_owner_contract_version", 0, ValueError),
        ("benchmark_owner_contract_digest", "8" * 63, ValueError),
        ("benchmark_reference_at", datetime(2026, 9, 17, 8, 15), ValueError),
        ("constructed_at", datetime(2026, 9, 17, 9, 0), ValueError),
        ("owner_contract_reference", "wrong:contract", ValueError),
        ("owner_contract_version", 0, ValueError),
        ("owner_contract_digest", "9" * 63, ValueError),
        ("used_at", datetime(2026, 9, 17, 10, 0), ValueError),
        ("purpose_code", "Selection Validity Analysis", ValueError),
    ],
)
def test_invalid_request_or_dependency_fails_before_owner_resolution(
    key: str, value: object, error: type[Exception]
) -> None:
    port: object = _ReadPort(_record())
    overrides = {key: value}
    if key == "read_port":
        port = value
        overrides = {}
    with pytest.raises(error):
        _resolve(read_port=port, **overrides)
    if isinstance(port, _ReadPort):
        assert port.calls == 0
