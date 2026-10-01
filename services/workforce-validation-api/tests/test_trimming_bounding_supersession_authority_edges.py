"""Hostile edges for append-only trimming-bounding correction authority."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.trimming_bounding_supersession_authority import (
    TrimmingBoundingSupersessionAuthorityIntegrityError,
    TrimmingBoundingSupersessionAuthorityNotFound,
    TrimmingBoundingSupersessionAuthorityReadPort,
    TrimmingBoundingSupersessionAuthorityRecord,
    TrimmingBoundingSupersessionAuthorityView,
    resolve_trimming_bounding_supersession_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000002")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
OTHER_STUDY = UUID("00000000-0000-7000-8000-0000000000d2")
RECEIPT = "trimming_bounding_adjustment_receipt:11111111-1111-4111-8111-111111111111"
OTHER_RECEIPT = "trimming_bounding_adjustment_receipt:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
SUCCESSOR = "trimming_bounding_adjustment_receipt:22222222-2222-4222-8222-222222222222"
OWNER = "released_owner_contract:33333333-3333-4333-8333-333333333333"
OTHER_OWNER = "released_owner_contract:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
RECEIPT_DIGEST = "1" * 64
SUCCESSOR_DIGEST = "2" * 64
OWNER_DIGEST = "3" * 64
OWNER_RELEASED_AT = datetime(2026, 9, 17, 0, 30, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 1, 0, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, 2, 0, tzinfo=timezone.utc)
CUTOVER = datetime(2026, 9, 18, 1, 0, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "adjustment_receipt_reference",
        "adjustment_receipt_digest",
        "evidence_version",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
        "successor_adjustment_receipt_reference",
        "successor_adjustment_receipt_digest",
        "successor_evidence_version",
        "successor_released_at",
    }
)


class _ReadPort:
    """Return configured authority and retain lookup coordinates."""

    def __init__(self, result: object) -> None:
        """Store one owner result and initialize the call ledger."""
        self.result = result
        self.calls: list[dict[str, object]] = []

    def read_trimming_bounding_supersession_authority(
        self, **coordinates: object
    ) -> object:
        """Capture the owner lookup and return configured evidence."""
        self.calls.append(dict(coordinates))
        return self.result


class _NoReadMethod:
    """Deliberately omit the required owner-read capability."""


class _ProtocolOnly(TrimmingBoundingSupersessionAuthorityReadPort):
    """Inherit only the Protocol declaration, not a concrete capability."""


class _DescriptorReadPort:
    """Expose a descriptor that static capability validation must reject."""

    @property
    def read_trimming_bounding_supersession_authority(self) -> object:
        """Trip if dependency validation executes the descriptor."""
        raise AssertionError("descriptor must not execute")


def _principal(*, tenant_record_id: UUID = TENANT) -> ValidationPrincipal:
    """Return one exact workforce-validation principal."""
    return ValidationPrincipal(
        tenant_record_id=tenant_record_id,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )


def _policy(*, purpose_code: str = "selection_validity_analysis") -> PurposeBoundAccessPolicy:
    """Return the purpose-bound policy for trimming correction evidence."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="trimming-bounding-supersession-read-v1",
        resource_kind="trimming_bounding_supersession_authority",
        purpose_code=purpose_code,
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def _record(**overrides: object) -> TrimmingBoundingSupersessionAuthorityRecord:
    """Build one current trimming correction state."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "adjustment_receipt_reference": RECEIPT,
        "adjustment_receipt_digest": RECEIPT_DIGEST,
        "evidence_version": 1,
        "owner_contract_reference": OWNER,
        "owner_contract_version": 1,
        "owner_contract_digest": OWNER_DIGEST,
        "owner_contract_released_at": OWNER_RELEASED_AT,
        "released_at": RELEASED_AT,
        "superseded_at": None,
        "successor_adjustment_receipt_reference": None,
        "successor_adjustment_receipt_digest": None,
        "successor_evidence_version": None,
        "successor_released_at": None,
    }
    values.update(overrides)
    return TrimmingBoundingSupersessionAuthorityRecord(**values)


def _resolve(
    *, read_port: object, **overrides: object
) -> TrimmingBoundingSupersessionAuthorityView:
    """Resolve current trimming authority with caller-known coordinates only."""
    values: dict[str, object] = {
        "principal": _principal(),
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "adjustment_receipt_reference": RECEIPT,
        "adjustment_receipt_digest": RECEIPT_DIGEST,
        "evidence_version": 1,
        "owner_contract_reference": OWNER,
        "owner_contract_version": 1,
        "owner_contract_digest": OWNER_DIGEST,
        "used_at": USED_AT,
        "purpose_code": "selection_validity_analysis",
        "policy": _policy(),
        "read_port": read_port,
    }
    values.update(overrides)
    return resolve_trimming_bounding_supersession_authority(**values)


def test_current_receipt_resolution_uses_owner_chronology_without_successor() -> None:
    """Resolve a current receipt and keep chronology out of the lookup key."""
    port = _ReadPort(_record())
    view = _resolve(read_port=port)

    assert isinstance(port, TrimmingBoundingSupersessionAuthorityReadPort)
    assert len(port.calls) == 1
    assert "released_at" not in port.calls[0]
    assert "superseded_at" not in port.calls[0]
    assert view.tenant_record_id == TENANT
    assert view.validity_study_id == STUDY
    assert dict(view.fields)["released_at"] == RELEASED_AT


def test_authorization_denial_happens_before_owner_resolution() -> None:
    """Do not consult owner evidence when purpose authorization fails."""
    port = _ReadPort(_record())
    with pytest.raises(AuthorizationDeniedError):
        _resolve(read_port=port, policy=_policy(purpose_code="audit_review"))
    assert port.calls == []


def test_missing_or_noncanonical_owner_evidence_fails_closed() -> None:
    """Reject absent and non-canonical owner evidence."""
    with pytest.raises(TrimmingBoundingSupersessionAuthorityNotFound):
        _resolve(read_port=_ReadPort(None))
    with pytest.raises(TrimmingBoundingSupersessionAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(object()))


@pytest.mark.parametrize(
    "record_overrides",
    [
        {"tenant_record_id": OTHER_TENANT},
        {"validity_study_id": OTHER_STUDY},
        {"adjustment_receipt_reference": OTHER_RECEIPT},
        {"adjustment_receipt_digest": "a" * 64},
        {"owner_contract_reference": OTHER_OWNER},
        {"owner_contract_version": 2},
        {"owner_contract_digest": "b" * 64},
    ],
)
def test_owner_evidence_must_match_every_requested_coordinate(
    record_overrides: dict[str, object]
) -> None:
    """Fail closed if owner evidence differs from any requested coordinate."""
    with pytest.raises(TrimmingBoundingSupersessionAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(**record_overrides)))


def test_release_chronology_and_historical_use_are_distinct() -> None:
    """Reject pre-release use while preserving history before a later cutover."""
    with pytest.raises(TrimmingBoundingSupersessionAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(released_at=USED_AT + timedelta(seconds=1))))

    record = _record(
        superseded_at=CUTOVER,
        successor_adjustment_receipt_reference=SUCCESSOR,
        successor_adjustment_receipt_digest=SUCCESSOR_DIGEST,
        successor_evidence_version=1,
        successor_released_at=CUTOVER,
    )
    assert dict(_resolve(read_port=_ReadPort(record)).fields)[
        "adjustment_receipt_digest"
    ] == RECEIPT_DIGEST
    with pytest.raises(TrimmingBoundingSupersessionAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(record), used_at=CUTOVER)


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
        ("adjustment_receipt_reference", "wrong:receipt", ValueError),
        ("adjustment_receipt_digest", "ABC", ValueError),
        ("evidence_version", 2, ValueError),
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
    """Validate caller-controlled coordinates before touching the owner port."""
    port: object = _ReadPort(_record())
    overrides = {key: value}
    if key == "read_port":
        port = value
        overrides = {}
    with pytest.raises(error):
        _resolve(read_port=port, **overrides)
    if isinstance(port, _ReadPort):
        assert port.calls == []


def test_record_rejects_invalid_chronology_schema_and_public_view() -> None:
    """Keep chronology atomic, evidence v1, and minimized views issuer-only."""
    with pytest.raises(ValueError, match="evidence_version must remain 1"):
        _record(evidence_version=2)
    with pytest.raises(ValueError, match="owner contract"):
        _record(owner_contract_released_at=RELEASED_AT + timedelta(seconds=1))
    with pytest.raises(ValueError, match="later than trimming"):
        _record(
            superseded_at=RELEASED_AT,
            successor_adjustment_receipt_reference=SUCCESSOR,
            successor_adjustment_receipt_digest=SUCCESSOR_DIGEST,
            successor_evidence_version=1,
            successor_released_at=RELEASED_AT,
        )
    with pytest.raises(ValueError, match="successor_evidence_version"):
        _record(
            superseded_at=CUTOVER,
            successor_adjustment_receipt_reference=SUCCESSOR,
            successor_adjustment_receipt_digest=SUCCESSOR_DIGEST,
            successor_evidence_version=2,
            successor_released_at=CUTOVER,
        )
    with pytest.raises(ValueError, match="released after"):
        _record(
            superseded_at=RELEASED_AT + timedelta(seconds=1),
            successor_adjustment_receipt_reference=SUCCESSOR,
            successor_adjustment_receipt_digest=SUCCESSOR_DIGEST,
            successor_evidence_version=1,
            successor_released_at=RELEASED_AT,
        )
    with pytest.raises(TypeError, match="issued only by"):
        TrimmingBoundingSupersessionAuthorityView(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            fields=(),
        )


def test_record_and_view_are_immutable_and_uuid_views_detached() -> None:
    """Detach UUIDs and reject mutation of owner records and minimized views."""
    tenant = UUID(str(TENANT))
    record = _record(tenant_record_id=tenant)
    object.__setattr__(tenant, "int", OTHER_TENANT.int)
    assert record.tenant_record_id == TENANT
    assert record.validity_study_id == STUDY
    assert record.released_at == RELEASED_AT
    assert record.superseded_at is None
    assert record.successor_fields is None
    with pytest.raises(AttributeError):
        object.__setattr__(record, "released_at", USED_AT)

    view = _resolve(read_port=_ReadPort(record))
    returned_tenant = view.tenant_record_id
    object.__setattr__(returned_tenant, "int", OTHER_TENANT.int)
    assert view.tenant_record_id == TENANT
    with pytest.raises(AttributeError):
        object.__setattr__(view, "fields", ())
