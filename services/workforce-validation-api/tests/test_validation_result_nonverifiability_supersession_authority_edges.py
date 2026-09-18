"""Hostile edges for append-only non-verifiability successor authority."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.result_nonverifiability_supersession_authority import (
    ValidationResultNonVerifiabilitySupersessionAuthorityIntegrityError,
    ValidationResultNonVerifiabilitySupersessionAuthorityNotFound,
    ValidationResultNonVerifiabilitySupersessionAuthorityReadPort,
    ValidationResultNonVerifiabilitySupersessionAuthorityRecord,
    ValidationResultNonVerifiabilitySupersessionAuthorityView,
    resolve_validation_result_nonverifiability_supersession_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000002")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
OTHER_STUDY = UUID("00000000-0000-7000-8000-0000000000d2")
RESULT_REFERENCE = "validation_analysis_result:11111111-1111-4111-8111-111111111111"
OTHER_RESULT_REFERENCE = "validation_analysis_result:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
ATTEMPT_REFERENCE = "validation_evidence_verification_attempt:33333333-3333-4333-8333-333333333333"
OTHER_ATTEMPT_REFERENCE = "validation_evidence_verification_attempt:44444444-4444-4444-8444-444444444444"
SUCCESSOR_ATTEMPT_REFERENCE = "validation_evidence_verification_attempt:55555555-5555-4555-8555-555555555555"
OWNER_CONTRACT_REFERENCE = "released_owner_contract:22222222-2222-4222-8222-222222222222"
OTHER_OWNER_CONTRACT_REFERENCE = "released_owner_contract:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
RESULT_DIGEST = "1" * 64
ATTEMPT_DIGEST = "3" * 64
SUCCESSOR_ATTEMPT_DIGEST = "5" * 64
OWNER_CONTRACT_DIGEST = "2" * 64
RELEASED_AT = datetime(2026, 9, 18, 8, tzinfo=timezone.utc)
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 9, 1, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 18, 10, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "result_reference",
        "result_digest",
        "failed_evidence_kind",
        "failure_mode",
        "verification_attempt_reference",
        "verification_attempt_digest",
        "evidence_version",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
        "successor_target_result_reference",
        "successor_target_result_digest",
        "successor_verification_attempt_reference",
        "successor_verification_attempt_digest",
        "successor_verification_attempt_released_at",
    }
)


class _ReadPort:
    """Return configured authority while retaining exact lookup coordinates."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def read_validation_result_nonverifiability_supersession_authority(
        self, **coordinates: object
    ) -> object:
        """Capture the owner lookup and return configured evidence."""
        self.calls.append(dict(coordinates))
        return self.result


class _NoReadMethod:
    """Deliberately fail the owner-port protocol."""


class _ProtocolOnly(ValidationResultNonVerifiabilitySupersessionAuthorityReadPort):
    """Inherit only the Protocol placeholder, not a concrete owner capability."""


class _DescriptorReadPort:
    """Expose a descriptor that static capability validation must reject."""

    @property
    def read_validation_result_nonverifiability_supersession_authority(self) -> object:
        """Fail if descriptor execution leaks through static capability validation."""
        raise AssertionError("descriptor must not execute")


def _principal(*, tenant_record_id: UUID = TENANT) -> ValidationPrincipal:
    """Return a tenant-scoped validation principal."""
    return ValidationPrincipal(
        tenant_record_id=tenant_record_id,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )


def _policy(*, purpose_code: str = "selection_validity_analysis") -> PurposeBoundAccessPolicy:
    """Return the exact purpose-bound policy for successor evidence."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="validation-result-nonverifiability-supersession-read-v1",
        resource_kind="validation_result_nonverifiability_supersession_authority",
        purpose_code=purpose_code,
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def _record(**overrides: object) -> ValidationResultNonVerifiabilitySupersessionAuthorityRecord:
    """Build canonical owner evidence with optional hostile overrides."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "result_reference": RESULT_REFERENCE,
        "result_digest": RESULT_DIGEST,
        "failed_evidence_kind": "analysis_weight_receipt",
        "failure_mode": "missing",
        "verification_attempt_reference": ATTEMPT_REFERENCE,
        "verification_attempt_digest": ATTEMPT_DIGEST,
        "evidence_version": 1,
        "owner_contract_reference": OWNER_CONTRACT_REFERENCE,
        "owner_contract_version": 3,
        "owner_contract_digest": OWNER_CONTRACT_DIGEST,
        "owner_contract_released_at": OWNER_CONTRACT_RELEASED_AT,
        "released_at": RELEASED_AT,
        "superseded_at": None,
        "successor_target_result_reference": None,
        "successor_target_result_digest": None,
        "successor_verification_attempt_reference": None,
        "successor_verification_attempt_digest": None,
        "successor_verification_attempt_released_at": None,
    }
    values.update(overrides)
    if (
        "successor_target_result_reference" not in overrides
        and values["successor_verification_attempt_reference"] is not None
    ):
        values["successor_target_result_reference"] = values["result_reference"]
    if (
        "successor_target_result_digest" not in overrides
        and values["successor_verification_attempt_reference"] is not None
    ):
        values["successor_target_result_digest"] = values["result_digest"]
    return ValidationResultNonVerifiabilitySupersessionAuthorityRecord(**values)


def _resolve(
    *, read_port: object, **overrides: object
) -> ValidationResultNonVerifiabilitySupersessionAuthorityView:
    """Resolve canonical request coordinates with optional hostile overrides."""
    values: dict[str, object] = {
        "principal": _principal(),
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "result_reference": RESULT_REFERENCE,
        "result_digest": RESULT_DIGEST,
        "failed_evidence_kind": "analysis_weight_receipt",
        "failure_mode": "missing",
        "verification_attempt_reference": ATTEMPT_REFERENCE,
        "verification_attempt_digest": ATTEMPT_DIGEST,
        "evidence_version": 1,
        "owner_contract_reference": OWNER_CONTRACT_REFERENCE,
        "owner_contract_version": 3,
        "owner_contract_digest": OWNER_CONTRACT_DIGEST,
        "used_at": USED_AT,
        "purpose_code": "selection_validity_analysis",
        "policy": _policy(),
        "read_port": read_port,
    }
    values.update(overrides)
    return resolve_validation_result_nonverifiability_supersession_authority(**values)


def test_current_negative_outcome_resolves_without_successor_coordinates() -> None:
    """Use owner chronology while keeping successor and cutover data private."""
    port = _ReadPort(_record())
    view = _resolve(read_port=port)

    assert isinstance(port, ValidationResultNonVerifiabilitySupersessionAuthorityReadPort)
    assert len(port.calls) == 1
    assert port.calls[0]["verification_attempt_reference"] == ATTEMPT_REFERENCE
    assert "owner_contract_released_at" not in port.calls[0]
    assert "released_at" not in port.calls[0]
    assert "superseded_at" not in port.calls[0]
    assert view.tenant_record_id == TENANT
    assert view.validity_study_id == STUDY
    fields = dict(view.fields)
    assert fields["owner_contract_released_at"] == OWNER_CONTRACT_RELEASED_AT
    assert fields["released_at"] == RELEASED_AT
    assert "superseded_at" not in fields
    assert "successor_verification_attempt_reference" not in fields
    assert "successor_target_result_reference" not in fields


def test_authorization_denial_happens_before_owner_resolution() -> None:
    """Keep denial ahead of any owner evidence lookup."""
    port = _ReadPort(_record())
    with pytest.raises(AuthorizationDeniedError):
        _resolve(read_port=port, policy=_policy(purpose_code="audit_review"))
    assert port.calls == []


def test_missing_or_noncanonical_owner_evidence_fails_closed() -> None:
    """Reject absence and foreign record types after authorization."""
    with pytest.raises(ValidationResultNonVerifiabilitySupersessionAuthorityNotFound):
        _resolve(read_port=_ReadPort(None))
    with pytest.raises(ValidationResultNonVerifiabilitySupersessionAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(object()))


@pytest.mark.parametrize(
    "record_overrides",
    [
        {"tenant_record_id": OTHER_TENANT},
        {"validity_study_id": OTHER_STUDY},
        {"result_reference": OTHER_RESULT_REFERENCE},
        {"result_digest": "a" * 64},
        {"failed_evidence_kind": "variance_design_receipt"},
        {"failure_mode": "non_reproducible"},
        {"verification_attempt_reference": OTHER_ATTEMPT_REFERENCE},
        {"verification_attempt_digest": "c" * 64},
        {"owner_contract_reference": OTHER_OWNER_CONTRACT_REFERENCE},
        {"owner_contract_version": 4},
        {"owner_contract_digest": "b" * 64},
    ],
)
def test_owner_evidence_must_match_every_requested_coordinate(
    record_overrides: dict[str, object]
) -> None:
    """Reject owner evidence selected by an incomplete or different lookup tuple."""
    if record_overrides.get("failure_mode") == "non_reproducible":
        record_overrides = {"failure_mode": "non_reproducible"}
    with pytest.raises((ValueError, ValidationResultNonVerifiabilitySupersessionAuthorityIntegrityError)):
        _resolve(read_port=_ReadPort(_record(**record_overrides)))


def test_release_chronology_and_historical_use_are_half_open() -> None:
    """Reject pre-release use while preserving reproducible historical reads."""
    with pytest.raises(ValidationResultNonVerifiabilitySupersessionAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(released_at=USED_AT + timedelta(seconds=1))))

    cutover = USED_AT + timedelta(seconds=1)
    record = _record(
        superseded_at=cutover,
        successor_verification_attempt_reference=SUCCESSOR_ATTEMPT_REFERENCE,
        successor_verification_attempt_digest=SUCCESSOR_ATTEMPT_DIGEST,
        successor_verification_attempt_released_at=cutover,
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
        ("failed_evidence_kind", "unknown", ValueError),
        ("failure_mode", "green", ValueError),
        ("verification_attempt_reference", "wrong:attempt", ValueError),
        ("verification_attempt_digest", "3" * 63, ValueError),
        ("evidence_version", False, ValueError),
        ("evidence_version", 2, ValueError),
        ("owner_contract_reference", "wrong:contract", ValueError),
        ("owner_contract_version", 0, ValueError),
        ("owner_contract_digest", "2" * 63, ValueError),
        ("used_at", datetime(2026, 9, 18), ValueError),
        ("purpose_code", "Selection Validity Analysis", ValueError),
    ],
)
def test_invalid_request_or_dependency_fails_before_owner_resolution(
    key: str, value: object, error: type[Exception]
) -> None:
    """Validate request and dependency shapes before any owner read occurs."""
    port: object = _ReadPort(_record())
    overrides = {key: value}
    if key == "read_port":
        port = value
        overrides = {}
    with pytest.raises(error):
        _resolve(read_port=port, **overrides)
    if isinstance(port, _ReadPort):
        assert port.calls == []


def test_record_rejects_non_v1_and_public_view_construction() -> None:
    """Keep evidence version governed and view issuance resolver-only."""
    with pytest.raises(ValueError, match="evidence_version must remain 1"):
        _record(evidence_version=2)
    with pytest.raises(TypeError, match="issued only by"):
        ValidationResultNonVerifiabilitySupersessionAuthorityView(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            fields=(),
        )


def test_record_rejects_naive_chronology_and_malformed_successor() -> None:
    """Reject malformed owner chronology before it can become current evidence."""
    with pytest.raises(ValueError):
        _record(owner_contract_released_at=datetime(2026, 9, 1))
    with pytest.raises(ValueError):
        _record(released_at=datetime(2026, 9, 18, 8))
    with pytest.raises(ValueError):
        _record(owner_contract_released_at=RELEASED_AT + timedelta(seconds=1))
    with pytest.raises(ValueError):
        _record(
            superseded_at=datetime(2026, 9, 18, 11),
            successor_verification_attempt_reference=SUCCESSOR_ATTEMPT_REFERENCE,
            successor_verification_attempt_digest=SUCCESSOR_ATTEMPT_DIGEST,
            successor_verification_attempt_released_at=USED_AT,
        )
    with pytest.raises(ValueError):
        _record(
            superseded_at=USED_AT + timedelta(hours=1),
            successor_verification_attempt_reference="analysis_weight_receipt:55555555-5555-4555-8555-555555555555",
            successor_verification_attempt_digest=SUCCESSOR_ATTEMPT_DIGEST,
            successor_verification_attempt_released_at=USED_AT + timedelta(hours=1),
        )
    with pytest.raises(ValueError):
        _record(
            superseded_at=USED_AT + timedelta(hours=1),
            successor_verification_attempt_reference=SUCCESSOR_ATTEMPT_REFERENCE,
            successor_verification_attempt_digest="not-a-digest",
            successor_verification_attempt_released_at=USED_AT + timedelta(hours=1),
        )


@pytest.mark.parametrize("alias_digest", [RESULT_DIGEST, ATTEMPT_DIGEST, OWNER_CONTRACT_DIGEST])
def test_successor_digest_must_not_alias_existing_evidence(alias_digest: str) -> None:
    """Require the successor attempt to identify genuinely new immutable evidence."""
    cutover = USED_AT + timedelta(hours=1)
    with pytest.raises(ValueError, match="must identify new evidence"):
        _record(
            superseded_at=cutover,
            successor_verification_attempt_reference=SUCCESSOR_ATTEMPT_REFERENCE,
            successor_verification_attempt_digest=alias_digest,
            successor_verification_attempt_released_at=cutover,
        )


def test_record_and_view_are_structurally_immutable_and_uuid_views_are_detached() -> None:
    """Prevent retained UUID aliases or attribute writes from mutating accepted authority."""
    tenant = UUID(str(TENANT))
    record = _record(tenant_record_id=tenant)
    object.__setattr__(tenant, "int", OTHER_TENANT.int)
    assert record.tenant_record_id == TENANT
    assert record.validity_study_id == STUDY
    assert record.released_at == RELEASED_AT
    assert record.superseded_at is None
    assert record.successor_fields is None
    assert dict(record.fields)["evidence_version"] == 1
    with pytest.raises(AttributeError):
        object.__setattr__(record, "evidence_version", 2)

    view = _resolve(read_port=_ReadPort(record))
    returned_tenant = view.tenant_record_id
    object.__setattr__(returned_tenant, "int", OTHER_TENANT.int)
    assert view.tenant_record_id == TENANT
    with pytest.raises(AttributeError):
        object.__setattr__(view, "fields", ())
