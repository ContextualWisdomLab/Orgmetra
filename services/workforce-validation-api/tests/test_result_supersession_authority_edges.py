"""Hostile edges for append-only validation-result correction authority."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.result_supersession_authority import (
    ValidationResultSupersessionAuthorityIntegrityError,
    ValidationResultSupersessionAuthorityNotFound,
    ValidationResultSupersessionAuthorityReadPort,
    ValidationResultSupersessionAuthorityRecord,
    ValidationResultSupersessionAuthorityView,
    resolve_validation_result_supersession_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000002")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
OTHER_STUDY = UUID("00000000-0000-7000-8000-0000000000d2")
RESULT_REFERENCE = "validation_analysis_result:11111111-1111-4111-8111-111111111111"
OTHER_RESULT_REFERENCE = "validation_analysis_result:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
SUCCESSOR_REFERENCE = "validation_analysis_result:33333333-3333-4333-8333-333333333333"
OWNER_CONTRACT_REFERENCE = "released_owner_contract:22222222-2222-4222-8222-222222222222"
OTHER_OWNER_CONTRACT_REFERENCE = "released_owner_contract:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
RESULT_DIGEST = "1" * 64
SUCCESSOR_DIGEST = "3" * 64
OWNER_CONTRACT_DIGEST = "2" * 64
RELEASED_AT = datetime(2026, 9, 17, 10, tzinfo=timezone.utc)
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 9, 1, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, 12, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "result_reference",
        "result_digest",
        "evidence_version",
        "correction_sequence",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
        "successor_result_reference",
        "successor_correction_sequence",
        "successor_result_digest",
        "successor_released_at",
    }
)


class _ReadPort:
    """Return configured authority and retain lookup coordinates."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def read_validation_result_supersession_authority(self, **coordinates: object) -> object:
        """Capture the owner lookup and return configured evidence."""
        self.calls.append(dict(coordinates))
        return self.result


class _NoReadMethod:
    """Deliberately fail the owner-port protocol."""


class _ProtocolOnly(ValidationResultSupersessionAuthorityReadPort):
    """Inherit only the Protocol placeholder, not a concrete owner capability."""


class _DescriptorReadPort:
    """Expose a descriptor that static capability validation must reject."""

    @property
    def read_validation_result_supersession_authority(self) -> object:
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
        policy_version_code="validation-result-supersession-authority-read-v1",
        resource_kind="validation_result_supersession_authority",
        purpose_code=purpose_code,
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def _record(**overrides: object) -> ValidationResultSupersessionAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "result_reference": RESULT_REFERENCE,
        "result_digest": RESULT_DIGEST,
        "evidence_version": 1,
        "correction_sequence": 2,
        "owner_contract_reference": OWNER_CONTRACT_REFERENCE,
        "owner_contract_version": 3,
        "owner_contract_digest": OWNER_CONTRACT_DIGEST,
        "owner_contract_released_at": OWNER_CONTRACT_RELEASED_AT,
        "released_at": RELEASED_AT,
        "superseded_at": None,
        "successor_result_reference": None,
        "successor_correction_sequence": None,
        "successor_result_digest": None,
        "successor_released_at": None,
    }
    values.update(overrides)
    return ValidationResultSupersessionAuthorityRecord(**values)


def _resolve(*, read_port: object, **overrides: object) -> ValidationResultSupersessionAuthorityView:
    values: dict[str, object] = {
        "principal": _principal(),
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "result_reference": RESULT_REFERENCE,
        "result_digest": RESULT_DIGEST,
        "evidence_version": 1,
        "correction_sequence": 2,
        "owner_contract_reference": OWNER_CONTRACT_REFERENCE,
        "owner_contract_version": 3,
        "owner_contract_digest": OWNER_CONTRACT_DIGEST,
        "used_at": USED_AT,
        "purpose_code": "selection_validity_analysis",
        "policy": _policy(),
        "read_port": read_port,
    }
    values.update(overrides)
    return resolve_validation_result_supersession_authority(**values)


def test_current_result_resolution_uses_owner_release_chronology_without_successor() -> None:
    port = _ReadPort(_record())
    view = _resolve(read_port=port)

    assert isinstance(port, ValidationResultSupersessionAuthorityReadPort)
    assert len(port.calls) == 1
    assert port.calls[0]["result_reference"] == RESULT_REFERENCE
    assert "owner_contract_released_at" not in port.calls[0]
    assert "released_at" not in port.calls[0]
    assert "superseded_at" not in port.calls[0]
    assert view.tenant_record_id == TENANT
    assert view.validity_study_id == STUDY
    fields = dict(view.fields)
    assert fields["owner_contract_released_at"] == OWNER_CONTRACT_RELEASED_AT
    assert fields["released_at"] == RELEASED_AT
    assert "superseded_at" not in fields
    assert "successor_result_reference" not in fields


def test_authorization_denial_happens_before_owner_resolution() -> None:
    port = _ReadPort(_record())
    with pytest.raises(AuthorizationDeniedError):
        _resolve(read_port=port, policy=_policy(purpose_code="audit_review"))
    assert port.calls == []


def test_missing_or_noncanonical_owner_evidence_fails_closed() -> None:
    with pytest.raises(ValidationResultSupersessionAuthorityNotFound):
        _resolve(read_port=_ReadPort(None))
    with pytest.raises(ValidationResultSupersessionAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(object()))


@pytest.mark.parametrize(
    "record_overrides",
    [
        {"tenant_record_id": OTHER_TENANT},
        {"validity_study_id": OTHER_STUDY},
        {"result_reference": OTHER_RESULT_REFERENCE},
        {"result_digest": "a" * 64},
        {"correction_sequence": 3},
        {"owner_contract_reference": OTHER_OWNER_CONTRACT_REFERENCE},
        {"owner_contract_version": 4},
        {"owner_contract_digest": "b" * 64},
    ],
)
def test_owner_evidence_must_match_every_requested_coordinate(
    record_overrides: dict[str, object]
) -> None:
    with pytest.raises(ValidationResultSupersessionAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(**record_overrides)))


def test_release_chronology_and_historical_use_fail_closed_or_remain_reproducible() -> None:
    with pytest.raises(ValidationResultSupersessionAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(released_at=USED_AT + timedelta(seconds=1))))

    record = _record(
        superseded_at=USED_AT + timedelta(seconds=1),
        successor_result_reference=SUCCESSOR_REFERENCE,
        successor_correction_sequence=3,
        successor_result_digest=SUCCESSOR_DIGEST,
        successor_released_at=USED_AT,
    )
    view = _resolve(read_port=_ReadPort(record))
    assert dict(view.fields)["result_digest"] == RESULT_DIGEST


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
        ("result_reference", "wrong:result", ValueError),
        ("result_digest", "ABC", ValueError),
        ("evidence_version", False, ValueError),
        ("evidence_version", 2, ValueError),
        ("correction_sequence", 0, ValueError),
        ("owner_contract_reference", "wrong:contract", ValueError),
        ("owner_contract_version", 0, ValueError),
        ("owner_contract_digest", "2" * 63, ValueError),
        ("used_at", datetime(2026, 9, 17), ValueError),
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
        assert port.calls == []


def test_record_rejects_non_v1_evidence_and_public_view_construction() -> None:
    with pytest.raises(ValueError, match="evidence_version must remain 1"):
        _record(evidence_version=2)
    with pytest.raises(TypeError, match="issued only by"):
        ValidationResultSupersessionAuthorityView(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            fields=(),
        )


def test_record_rejects_naive_owner_resolved_timestamps_and_malformed_successor() -> None:
    with pytest.raises(ValueError):
        _record(owner_contract_released_at=datetime(2026, 9, 1))
    with pytest.raises(ValueError):
        _record(released_at=datetime(2026, 9, 17, 10))
    with pytest.raises(ValueError):
        _record(
            superseded_at=datetime(2026, 9, 17, 13),
            successor_result_reference=SUCCESSOR_REFERENCE,
            successor_correction_sequence=3,
            successor_result_digest=SUCCESSOR_DIGEST,
            successor_released_at=USED_AT,
        )
    with pytest.raises(ValueError):
        _record(
            superseded_at=USED_AT + timedelta(hours=1),
            successor_result_reference="analysis_weight_receipt:33333333-3333-4333-8333-333333333333",
            successor_correction_sequence=3,
            successor_result_digest=SUCCESSOR_DIGEST,
            successor_released_at=USED_AT,
        )
    with pytest.raises(ValueError):
        _record(
            superseded_at=USED_AT + timedelta(hours=1),
            successor_result_reference=SUCCESSOR_REFERENCE,
            successor_correction_sequence=True,
            successor_result_digest=SUCCESSOR_DIGEST,
            successor_released_at=USED_AT,
        )
    with pytest.raises(ValueError):
        _record(
            superseded_at=USED_AT + timedelta(hours=1),
            successor_result_reference=SUCCESSOR_REFERENCE,
            successor_correction_sequence=3,
            successor_result_digest="not-a-digest",
            successor_released_at=USED_AT,
        )


def test_record_and_view_are_structurally_immutable_and_uuid_views_are_detached() -> None:
    tenant = UUID(str(TENANT))
    record = _record(tenant_record_id=tenant)
    object.__setattr__(tenant, "int", OTHER_TENANT.int)
    assert record.tenant_record_id == TENANT
    assert record.validity_study_id == STUDY
    assert record.released_at == RELEASED_AT
    assert record.superseded_at is None
    assert record.successor_fields is None
    assert dict(record.fields)["correction_sequence"] == 2
    with pytest.raises(AttributeError):
        object.__setattr__(record, "correction_sequence", 3)

    view = _resolve(read_port=_ReadPort(record))
    returned_tenant = view.tenant_record_id
    object.__setattr__(returned_tenant, "int", OTHER_TENANT.int)
    assert view.tenant_record_id == TENANT
    with pytest.raises(AttributeError):
        object.__setattr__(view, "fields", ())
