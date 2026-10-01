"""Append-only correction contract for released base/design-weight authority."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.base_weight_supersession_authority import (
    BaseWeightSupersessionAuthorityIntegrityError,
    BaseWeightSupersessionAuthorityNotFound,
    BaseWeightSupersessionAuthorityReadPort,
    BaseWeightSupersessionAuthorityRecord,
    BaseWeightSupersessionAuthorityView,
    resolve_base_weight_supersession_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000002")
STUDY = UUID("00000000-0000-7000-8000-0000000000f1")
OTHER_STUDY = UUID("00000000-0000-7000-8000-0000000000f2")
RECEIPT = "base_weight_evidence_receipt:11111111-1111-4111-8111-111111111111"
SUCCESSOR = "base_weight_evidence_receipt:22222222-2222-4222-8222-222222222222"
OWNER = "released_owner_contract:33333333-3333-4333-8333-333333333333"
DIGEST = "1" * 64
SUCCESSOR_DIGEST = "2" * 64
OWNER_DIGEST = "3" * 64
OWNER_RELEASED = datetime(2026, 9, 17, 6, 45, tzinfo=timezone.utc)
RELEASED = datetime(2026, 9, 17, 7, 30, tzinfo=timezone.utc)
CUTOVER = datetime(2026, 9, 18, 7, 30, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "base_weight_evidence_receipt_reference",
        "base_weight_evidence_receipt_digest",
        "evidence_version",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
        "successor_base_weight_evidence_receipt_reference",
        "successor_base_weight_evidence_receipt_digest",
        "successor_evidence_version",
        "successor_released_at",
    }
)


class _ReadPort:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def read_base_weight_supersession_authority(self, **coordinates: object) -> object:
        self.calls.append(dict(coordinates))
        return self.result


class _ProtocolOnly(BaseWeightSupersessionAuthorityReadPort):
    pass


class _DescriptorReadPort:
    @property
    def read_base_weight_supersession_authority(self) -> object:
        raise AssertionError("descriptor must not execute")


class _NoReadMethod:
    pass


def _principal() -> ValidationPrincipal:
    return ValidationPrincipal(
        tenant_record_id=TENANT,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )


def _policy(*, purpose_code: str = "selection_validity_analysis") -> PurposeBoundAccessPolicy:
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="base-weight-supersession-read-v1",
        resource_kind="base_weight_supersession_authority",
        purpose_code=purpose_code,
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def _record(**overrides: object) -> BaseWeightSupersessionAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "base_weight_evidence_receipt_reference": RECEIPT,
        "base_weight_evidence_receipt_digest": DIGEST,
        "evidence_version": 1,
        "owner_contract_reference": OWNER,
        "owner_contract_version": 1,
        "owner_contract_digest": OWNER_DIGEST,
        "owner_contract_released_at": OWNER_RELEASED,
        "released_at": RELEASED,
        "superseded_at": CUTOVER,
        "successor_base_weight_evidence_receipt_reference": SUCCESSOR,
        "successor_base_weight_evidence_receipt_digest": SUCCESSOR_DIGEST,
        "successor_evidence_version": 1,
        "successor_released_at": CUTOVER,
    }
    values.update(overrides)
    return BaseWeightSupersessionAuthorityRecord(**values)


def _resolve(*, read_port: object, used_at: datetime, **overrides: object):
    values: dict[str, object] = {
        "principal": _principal(),
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "base_weight_evidence_receipt_reference": RECEIPT,
        "base_weight_evidence_receipt_digest": DIGEST,
        "evidence_version": 1,
        "owner_contract_reference": OWNER,
        "owner_contract_version": 1,
        "owner_contract_digest": OWNER_DIGEST,
        "used_at": used_at,
        "purpose_code": "selection_validity_analysis",
        "policy": _policy(),
        "read_port": read_port,
    }
    values.update(overrides)
    return resolve_base_weight_supersession_authority(**values)


def test_successor_edge_requires_complete_atomic_released_coordinates() -> None:
    with pytest.raises(ValueError, match="evidence_version must remain 1"):
        _record(evidence_version=2)
    with pytest.raises(ValueError, match="complete released successor coordinates"):
        _record(successor_released_at=None)
    with pytest.raises(ValueError, match="later than base-weight receipt release"):
        _record(superseded_at=RELEASED)
    with pytest.raises(ValueError, match="new reference"):
        _record(successor_base_weight_evidence_receipt_reference=RECEIPT)
    with pytest.raises(ValueError, match="new evidence"):
        _record(successor_base_weight_evidence_receipt_digest=DIGEST)
    with pytest.raises(ValueError, match="successor_evidence_version must remain 1"):
        _record(successor_evidence_version=2)
    with pytest.raises(ValueError, match="released after its predecessor"):
        _record(superseded_at=RELEASED + timedelta(seconds=1), successor_released_at=RELEASED)
    with pytest.raises(ValueError, match="exactly at supersession"):
        _record(successor_released_at=CUTOVER - timedelta(seconds=1))
    with pytest.raises(ValueError, match="exactly at supersession"):
        _record(successor_released_at=CUTOVER + timedelta(seconds=1))


def test_chronology_requires_released_owner_and_timezone_aware_instants() -> None:
    with pytest.raises(ValueError, match="owner contract"):
        _record(owner_contract_released_at=RELEASED + timedelta(seconds=1))
    with pytest.raises(ValueError):
        _record(owner_contract_released_at=datetime(2026, 9, 17, 6, 45))
    with pytest.raises(ValueError):
        _record(released_at=datetime(2026, 9, 17, 7, 30))
    with pytest.raises(ValueError):
        _record(superseded_at=datetime(2026, 9, 18, 7, 30))
    with pytest.raises(ValueError):
        _record(successor_released_at=datetime(2026, 9, 18, 7, 30))


def test_historical_use_is_allowed_but_cutover_use_fails_closed() -> None:
    record = _record()
    port = _ReadPort(record)
    view = _resolve(read_port=port, used_at=CUTOVER - timedelta(microseconds=1))

    assert view.validity_study_id == STUDY

    assert isinstance(port, BaseWeightSupersessionAuthorityReadPort)
    assert port.calls == [
        {
            "tenant_record_id": TENANT,
            "validity_study_id": STUDY,
            "base_weight_evidence_receipt_reference": RECEIPT,
            "base_weight_evidence_receipt_digest": DIGEST,
            "evidence_version": 1,
            "owner_contract_reference": OWNER,
            "owner_contract_version": 1,
            "owner_contract_digest": OWNER_DIGEST,
        }
    ]
    assert ("base_weight_evidence_receipt_reference", RECEIPT) in view.fields
    assert ("released_at", RELEASED) in view.fields
    assert ("superseded_at", CUTOVER) in view.fields
    assert all(not name.startswith("successor_") for name, _ in view.fields)

    with pytest.raises(BaseWeightSupersessionAuthorityIntegrityError, match="superseded"):
        _resolve(read_port=_ReadPort(record), used_at=CUTOVER)


def test_open_interval_without_successor_remains_current() -> None:
    record = _record(
        superseded_at=None,
        successor_base_weight_evidence_receipt_reference=None,
        successor_base_weight_evidence_receipt_digest=None,
        successor_evidence_version=None,
        successor_released_at=None,
    )
    view = _resolve(read_port=_ReadPort(record), used_at=CUTOVER + timedelta(days=30))
    assert ("superseded_at", None) in view.fields


def test_missing_noncanonical_and_pre_release_evidence_fail_closed() -> None:
    with pytest.raises(BaseWeightSupersessionAuthorityNotFound):
        _resolve(read_port=_ReadPort(None), used_at=RELEASED)
    with pytest.raises(BaseWeightSupersessionAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(object()), used_at=RELEASED)
    with pytest.raises(BaseWeightSupersessionAuthorityIntegrityError, match="released before scientific use"):
        _resolve(read_port=_ReadPort(_record()), used_at=RELEASED - timedelta(seconds=1))


@pytest.mark.parametrize(
    "record_overrides",
    [
        {"tenant_record_id": OTHER_TENANT},
        {"validity_study_id": OTHER_STUDY},
        {"base_weight_evidence_receipt_reference": SUCCESSOR},
        {"base_weight_evidence_receipt_digest": "4" * 64},
        {"owner_contract_reference": "released_owner_contract:44444444-4444-4444-8444-444444444444"},
        {"owner_contract_version": 2},
        {"owner_contract_digest": "5" * 64},
    ],
)
def test_owner_evidence_must_match_every_requested_coordinate(record_overrides: dict[str, object]) -> None:
    if "base_weight_evidence_receipt_reference" in record_overrides:
        record_overrides = {
            **record_overrides,
            "successor_base_weight_evidence_receipt_reference": RECEIPT,
        }
    with pytest.raises(BaseWeightSupersessionAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(**record_overrides)), used_at=RELEASED)


def test_authorization_denial_precedes_owner_read() -> None:
    port = _ReadPort(_record())
    with pytest.raises(AuthorizationDeniedError):
        _resolve(read_port=port, used_at=RELEASED, policy=_policy(purpose_code="audit_review"))
    assert port.calls == []


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
        ("base_weight_evidence_receipt_reference", "wrong:receipt", ValueError),
        ("base_weight_evidence_receipt_digest", "ABC", ValueError),
        ("evidence_version", 2, ValueError),
        ("owner_contract_reference", "wrong:contract", ValueError),
        ("owner_contract_version", 0, ValueError),
        ("owner_contract_digest", "3" * 63, ValueError),
        ("used_at", datetime(2026, 9, 18, 7, 0), ValueError),
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
        _resolve(read_port=port, **{"used_at": RELEASED, **overrides})
    if isinstance(port, _ReadPort):
        assert port.calls == []


def test_record_and_view_are_immutable_and_uuid_views_detached() -> None:
    tenant = UUID(str(TENANT))
    record = _record(tenant_record_id=tenant)
    object.__setattr__(tenant, "int", OTHER_TENANT.int)
    assert record.tenant_record_id == TENANT

    with pytest.raises(AttributeError):
        object.__setattr__(record, "released_at", CUTOVER)

    view = _resolve(read_port=_ReadPort(record), used_at=RELEASED)
    returned_tenant = view.tenant_record_id
    object.__setattr__(returned_tenant, "int", OTHER_TENANT.int)
    assert view.tenant_record_id == TENANT

    with pytest.raises(TypeError):
        BaseWeightSupersessionAuthorityView(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            fields=(),
        )


def test_exact_typed_hidden_tail_record_fails_closed() -> None:
    canonical = _record()
    forged = tuple.__new__(
        BaseWeightSupersessionAuthorityRecord,
        tuple(canonical) + (("hidden_owner_coordinate", "must-not-normalize-away"),),
    )

    with pytest.raises(BaseWeightSupersessionAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(forged), used_at=RELEASED)


def test_exact_typed_truncated_record_maps_to_integrity_error() -> None:
    canonical = _record()
    forged = tuple.__new__(BaseWeightSupersessionAuthorityRecord, tuple(canonical)[:-1])

    with pytest.raises(BaseWeightSupersessionAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(forged), used_at=RELEASED)
