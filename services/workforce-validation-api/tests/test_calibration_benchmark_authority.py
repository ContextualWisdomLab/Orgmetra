"""Fail-closed contract for released calibration benchmark authority."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.benchmark_authority import (
    CalibrationBenchmarkAuthorityIntegrityError,
    CalibrationBenchmarkAuthorityNotFound,
    CalibrationBenchmarkAuthorityReadPort,
    CalibrationBenchmarkAuthorityRecord,
    CalibrationBenchmarkAuthorityView,
    resolve_calibration_benchmark_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000002")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
OTHER_STUDY = UUID("00000000-0000-7000-8000-0000000000d2")
BENCHMARK_REFERENCE = "calibration_benchmark_receipt:11111111-1111-4111-8111-111111111111"
OWNER_CONTRACT_REFERENCE = "released_owner_contract:22222222-2222-4222-8222-222222222222"
BENCHMARK_DIGEST = "1" * 64
OWNER_CONTRACT_DIGEST = "2" * 64
BENCHMARK_REFERENCE_AT = datetime(2026, 6, 30, tzinfo=timezone.utc)
BENCHMARK_RELEASED_AT = datetime(2026, 7, 15, tzinfo=timezone.utc)
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 7, 1, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "benchmark_receipt_reference",
        "benchmark_receipt_version",
        "benchmark_receipt_digest",
        "benchmark_owner_contract_reference",
        "benchmark_owner_contract_version",
        "benchmark_owner_contract_digest",
        "benchmark_reference_at",
        "benchmark_receipt_released_at",
        "owner_contract_released_at",
    }
)


class _ReadPort:
    """Return configured benchmark authority and retain exact lookup coordinates."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[tuple[object, ...]] = []

    def read_calibration_benchmark_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        benchmark_receipt_reference: str,
        benchmark_receipt_version: int,
        benchmark_receipt_digest: str,
        benchmark_owner_contract_reference: str,
        benchmark_owner_contract_version: int,
        benchmark_owner_contract_digest: str,
        benchmark_reference_at: datetime,
    ) -> object:
        """Capture the owner lookup and return configured evidence."""
        self.calls.append(
            (
                tenant_record_id,
                validity_study_id,
                benchmark_receipt_reference,
                benchmark_receipt_version,
                benchmark_receipt_digest,
                benchmark_owner_contract_reference,
                benchmark_owner_contract_version,
                benchmark_owner_contract_digest,
                benchmark_reference_at,
            )
        )
        return self.result


class _NoReadMethod:
    """Deliberately fail the owner-port protocol."""


class _ProtocolOnly(CalibrationBenchmarkAuthorityReadPort):
    """Inherit only the Protocol placeholder, not a concrete owner capability."""


class _DescriptorReadPort:
    """Expose a descriptor that must be rejected without executing it."""

    @property
    def read_calibration_benchmark_authority(self) -> object:
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
        policy_version_code="calibration-benchmark-authority-read-v1",
        resource_kind="calibration_benchmark_authority",
        purpose_code=purpose_code,
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def _record(**overrides: object) -> CalibrationBenchmarkAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "benchmark_receipt_reference": BENCHMARK_REFERENCE,
        "benchmark_receipt_version": 4,
        "benchmark_receipt_digest": BENCHMARK_DIGEST,
        "benchmark_owner_contract_reference": OWNER_CONTRACT_REFERENCE,
        "benchmark_owner_contract_version": 3,
        "benchmark_owner_contract_digest": OWNER_CONTRACT_DIGEST,
        "benchmark_reference_at": BENCHMARK_REFERENCE_AT,
        "benchmark_receipt_released_at": BENCHMARK_RELEASED_AT,
        "owner_contract_released_at": OWNER_CONTRACT_RELEASED_AT,
    }
    values.update(overrides)
    return CalibrationBenchmarkAuthorityRecord(**values)


def _resolve(*, read_port: object, **overrides: object) -> CalibrationBenchmarkAuthorityView:
    values: dict[str, object] = {
        "principal": _principal(),
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "benchmark_receipt_reference": BENCHMARK_REFERENCE,
        "benchmark_receipt_version": 4,
        "benchmark_receipt_digest": BENCHMARK_DIGEST,
        "benchmark_owner_contract_reference": OWNER_CONTRACT_REFERENCE,
        "benchmark_owner_contract_version": 3,
        "benchmark_owner_contract_digest": OWNER_CONTRACT_DIGEST,
        "benchmark_reference_at": BENCHMARK_REFERENCE_AT,
        "used_at": USED_AT,
        "purpose_code": "selection_validity_analysis",
        "policy": _policy(),
        "read_port": read_port,
    }
    values.update(overrides)
    return resolve_calibration_benchmark_authority(**values)


def test_resolution_authorizes_then_returns_released_minimized_evidence() -> None:
    port = _ReadPort(_record())

    view = _resolve(read_port=port)

    assert isinstance(port, CalibrationBenchmarkAuthorityReadPort)
    assert port.calls == [
        (
            TENANT,
            STUDY,
            BENCHMARK_REFERENCE,
            4,
            BENCHMARK_DIGEST,
            OWNER_CONTRACT_REFERENCE,
            3,
            OWNER_CONTRACT_DIGEST,
            BENCHMARK_REFERENCE_AT,
        )
    ]
    assert view.tenant_record_id == TENANT
    assert view.validity_study_id == STUDY
    assert view.fields == (
        ("benchmark_owner_contract_digest", OWNER_CONTRACT_DIGEST),
        ("benchmark_owner_contract_reference", OWNER_CONTRACT_REFERENCE),
        ("benchmark_owner_contract_version", 3),
        ("benchmark_receipt_digest", BENCHMARK_DIGEST),
        ("benchmark_receipt_reference", BENCHMARK_REFERENCE),
        ("benchmark_receipt_released_at", BENCHMARK_RELEASED_AT),
        ("benchmark_receipt_version", 4),
        ("benchmark_reference_at", BENCHMARK_REFERENCE_AT),
        ("owner_contract_released_at", OWNER_CONTRACT_RELEASED_AT),
    )


def test_authorization_denial_happens_before_owner_resolution() -> None:
    port = _ReadPort(_record())

    with pytest.raises(AuthorizationDeniedError):
        _resolve(read_port=port, policy=_policy(purpose_code="audit_review"))

    assert port.calls == []


def test_missing_or_noncanonical_owner_evidence_fails_closed() -> None:
    with pytest.raises(CalibrationBenchmarkAuthorityNotFound):
        _resolve(read_port=_ReadPort(None))

    with pytest.raises(CalibrationBenchmarkAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(object()))


@pytest.mark.parametrize(
    "record_overrides",
    [
        {"tenant_record_id": OTHER_TENANT},
        {"validity_study_id": OTHER_STUDY},
        {
            "benchmark_receipt_reference": (
                "calibration_benchmark_receipt:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
            )
        },
        {"benchmark_receipt_version": 5},
        {"benchmark_receipt_digest": "a" * 64},
        {
            "benchmark_owner_contract_reference": (
                "released_owner_contract:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
            )
        },
        {"benchmark_owner_contract_version": 4},
        {"benchmark_owner_contract_digest": "b" * 64},
        {"benchmark_reference_at": BENCHMARK_REFERENCE_AT + timedelta(seconds=1)},
    ],
)
def test_owner_evidence_must_match_every_leaf_benchmark_coordinate(
    record_overrides: dict[str, object]
) -> None:
    with pytest.raises(CalibrationBenchmarkAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(**record_overrides)))


def test_owner_evidence_must_have_existed_before_scientific_use() -> None:
    for overrides in (
        {"benchmark_receipt_released_at": USED_AT + timedelta(seconds=1)},
        {"owner_contract_released_at": USED_AT + timedelta(seconds=1)},
        {"benchmark_reference_at": USED_AT + timedelta(seconds=1)},
    ):
        port = _ReadPort(_record(**overrides))
        with pytest.raises(CalibrationBenchmarkAuthorityIntegrityError):
            _resolve(
                read_port=port,
                benchmark_reference_at=overrides.get(
                    "benchmark_reference_at", BENCHMARK_REFERENCE_AT
                ),
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
        ("benchmark_receipt_reference", "wrong:benchmark", ValueError),
        ("benchmark_receipt_version", True, ValueError),
        ("benchmark_receipt_digest", "ABC", ValueError),
        ("benchmark_owner_contract_reference", "wrong:contract", ValueError),
        ("benchmark_owner_contract_version", 0, ValueError),
        ("benchmark_owner_contract_digest", "2" * 63, ValueError),
        ("benchmark_reference_at", datetime(2026, 6, 30), ValueError),
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
        ("benchmark_receipt_reference", "wrong:benchmark"),
        ("benchmark_receipt_version", 0),
        ("benchmark_receipt_digest", "1" * 63),
        ("benchmark_owner_contract_reference", "wrong:contract"),
        ("benchmark_owner_contract_version", True),
        ("benchmark_owner_contract_digest", "2" * 65),
        ("benchmark_reference_at", datetime(2026, 6, 30)),
        ("benchmark_receipt_released_at", datetime(2026, 7, 15)),
        ("owner_contract_released_at", "not-a-datetime"),
    ],
)
def test_record_rejects_invalid_released_benchmark_evidence(key: str, value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        _record(**{key: value})


def test_record_and_view_are_structurally_immutable_and_uuid_views_are_detached() -> None:
    tenant = UUID(str(TENANT))
    record = _record(tenant_record_id=tenant)
    object.__setattr__(tenant, "int", OTHER_TENANT.int)
    assert record.tenant_record_id == TENANT

    with pytest.raises(AttributeError):
        object.__setattr__(record, "benchmark_receipt_version", 999)

    view = _resolve(read_port=_ReadPort(record))
    returned_tenant = view.tenant_record_id
    object.__setattr__(returned_tenant, "int", OTHER_TENANT.int)
    assert view.tenant_record_id == TENANT

    with pytest.raises(AttributeError):
        object.__setattr__(view, "fields", ())
    with pytest.raises(TypeError):
        CalibrationBenchmarkAuthorityView(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            fields=(),
        )
