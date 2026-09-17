"""Fail-closed contract for released cross-sectional/longitudinal weight eligibility."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.weight_eligibility_authority import (
    WeightEligibilityAuthorityIntegrityError,
    WeightEligibilityAuthorityNotFound,
    WeightEligibilityAuthorityReadPort,
    WeightEligibilityAuthorityRecord,
    WeightEligibilityAuthorityView,
    resolve_weight_eligibility_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000002")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
OTHER_STUDY = UUID("00000000-0000-7000-8000-0000000000d2")
RECEIPT_REFERENCE = "weight_eligibility_receipt:11111111-1111-4111-8111-111111111111"
TARGET_POPULATION_REFERENCE = "analysis_target_population:workers-2026q3"
REFERENCE_DURATION_REFERENCE = "analysis_reference_duration:2026q3"
OWNER_CONTRACT_REFERENCE = "released_owner_contract:22222222-2222-4222-8222-222222222222"
RECEIPT_DIGEST = "1" * 64
TARGET_POPULATION_DIGEST = "2" * 64
REFERENCE_DURATION_DIGEST = "3" * 64
ELIGIBLE_CASE_SET_DIGEST = "4" * 64
WEIGHT_ARTIFACT_DIGEST = "5" * 64
OWNER_CONTRACT_DIGEST = "6" * 64
CONSTRUCTED_AT = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "eligibility_receipt_reference",
        "eligibility_receipt_digest",
        "evidence_version",
        "weight_scope_code",
        "target_population_reference",
        "target_population_digest",
        "reference_duration_reference",
        "reference_duration_digest",
        "eligible_case_set_digest",
        "weight_artifact_digest",
        "constructed_at",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "released_at",
    }
)


class _ReadPort:
    """Return configured eligibility authority and retain lookup coordinates."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def read_weight_eligibility_authority(self, **coordinates: object) -> object:
        """Capture the owner lookup and return configured evidence."""
        self.calls.append(dict(coordinates))
        return self.result


class _NoReadMethod:
    """Deliberately fail the owner-port protocol."""


class _ProtocolOnly(WeightEligibilityAuthorityReadPort):
    """Inherit only the Protocol placeholder, not a concrete owner capability."""


class _DescriptorReadPort:
    """Expose a descriptor that must be rejected without executing it."""

    @property
    def read_weight_eligibility_authority(self) -> object:
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
        policy_version_code="weight-eligibility-authority-read-v1",
        resource_kind="weight_eligibility_authority",
        purpose_code=purpose_code,
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def _record(**overrides: object) -> WeightEligibilityAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "eligibility_receipt_reference": RECEIPT_REFERENCE,
        "eligibility_receipt_digest": RECEIPT_DIGEST,
        "evidence_version": 1,
        "weight_scope_code": "longitudinal",
        "target_population_reference": TARGET_POPULATION_REFERENCE,
        "target_population_digest": TARGET_POPULATION_DIGEST,
        "reference_duration_reference": REFERENCE_DURATION_REFERENCE,
        "reference_duration_digest": REFERENCE_DURATION_DIGEST,
        "eligible_case_set_digest": ELIGIBLE_CASE_SET_DIGEST,
        "weight_artifact_digest": WEIGHT_ARTIFACT_DIGEST,
        "constructed_at": CONSTRUCTED_AT,
        "owner_contract_reference": OWNER_CONTRACT_REFERENCE,
        "owner_contract_version": 3,
        "owner_contract_digest": OWNER_CONTRACT_DIGEST,
        "released_at": RELEASED_AT,
    }
    values.update(overrides)
    return WeightEligibilityAuthorityRecord(**values)


def _resolve(*, read_port: object, **overrides: object) -> WeightEligibilityAuthorityView:
    values: dict[str, object] = {
        "principal": _principal(),
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "eligibility_receipt_reference": RECEIPT_REFERENCE,
        "eligibility_receipt_digest": RECEIPT_DIGEST,
        "evidence_version": 1,
        "weight_scope_code": "longitudinal",
        "target_population_reference": TARGET_POPULATION_REFERENCE,
        "target_population_digest": TARGET_POPULATION_DIGEST,
        "reference_duration_reference": REFERENCE_DURATION_REFERENCE,
        "reference_duration_digest": REFERENCE_DURATION_DIGEST,
        "eligible_case_set_digest": ELIGIBLE_CASE_SET_DIGEST,
        "weight_artifact_digest": WEIGHT_ARTIFACT_DIGEST,
        "constructed_at": CONSTRUCTED_AT,
        "owner_contract_reference": OWNER_CONTRACT_REFERENCE,
        "owner_contract_version": 3,
        "owner_contract_digest": OWNER_CONTRACT_DIGEST,
        "used_at": USED_AT,
        "purpose_code": "selection_validity_analysis",
        "policy": _policy(),
        "read_port": read_port,
    }
    values.update(overrides)
    return resolve_weight_eligibility_authority(**values)


def test_longitudinal_resolution_binds_population_duration_case_set_and_artifact() -> None:
    port = _ReadPort(_record())

    view = _resolve(read_port=port)

    assert isinstance(port, WeightEligibilityAuthorityReadPort)
    assert len(port.calls) == 1
    assert port.calls[0]["weight_scope_code"] == "longitudinal"
    assert port.calls[0]["reference_duration_reference"] == REFERENCE_DURATION_REFERENCE
    assert port.calls[0]["eligible_case_set_digest"] == ELIGIBLE_CASE_SET_DIGEST
    assert port.calls[0]["weight_artifact_digest"] == WEIGHT_ARTIFACT_DIGEST
    assert view.tenant_record_id == TENANT
    assert view.validity_study_id == STUDY
    assert ("weight_scope_code", "longitudinal") in view.fields
    assert ("target_population_reference", TARGET_POPULATION_REFERENCE) in view.fields
    assert ("reference_duration_reference", REFERENCE_DURATION_REFERENCE) in view.fields
    assert ("eligible_case_set_digest", ELIGIBLE_CASE_SET_DIGEST) in view.fields
    assert ("weight_artifact_digest", WEIGHT_ARTIFACT_DIGEST) in view.fields


def test_cross_sectional_scope_is_distinct_released_authority() -> None:
    record = _record(weight_scope_code="cross_sectional")
    view = _resolve(read_port=_ReadPort(record), weight_scope_code="cross_sectional")
    assert ("weight_scope_code", "cross_sectional") in view.fields


def test_authorization_denial_happens_before_owner_resolution() -> None:
    port = _ReadPort(_record())
    with pytest.raises(AuthorizationDeniedError):
        _resolve(read_port=port, policy=_policy(purpose_code="audit_review"))
    assert port.calls == []


def test_missing_or_noncanonical_owner_evidence_fails_closed() -> None:
    with pytest.raises(WeightEligibilityAuthorityNotFound):
        _resolve(read_port=_ReadPort(None))
    with pytest.raises(WeightEligibilityAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(object()))


@pytest.mark.parametrize(
    "record_overrides",
    [
        {"tenant_record_id": OTHER_TENANT},
        {"validity_study_id": OTHER_STUDY},
        {"eligibility_receipt_digest": "a" * 64},
        {"weight_scope_code": "cross_sectional"},
        {"target_population_reference": "analysis_target_population:other"},
        {"target_population_digest": "b" * 64},
        {"reference_duration_reference": "analysis_reference_duration:other"},
        {"reference_duration_digest": "c" * 64},
        {"eligible_case_set_digest": "d" * 64},
        {"weight_artifact_digest": "e" * 64},
        {"constructed_at": CONSTRUCTED_AT + timedelta(seconds=1)},
        {"owner_contract_version": 4},
        {"owner_contract_digest": "f" * 64},
    ],
)
def test_owner_evidence_must_match_every_requested_coordinate(
    record_overrides: dict[str, object]
) -> None:
    with pytest.raises(WeightEligibilityAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(**record_overrides)))


def test_release_chronology_and_use_fail_closed() -> None:
    with pytest.raises(ValueError):
        _record(released_at=CONSTRUCTED_AT - timedelta(seconds=1))
    with pytest.raises(WeightEligibilityAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(released_at=USED_AT + timedelta(seconds=1))))


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
        ("eligibility_receipt_reference", "wrong:receipt", ValueError),
        ("eligibility_receipt_digest", "ABC", ValueError),
        ("evidence_version", False, ValueError),
        ("weight_scope_code", "panel", ValueError),
        ("target_population_reference", "wrong:population", ValueError),
        ("target_population_digest", "2" * 63, ValueError),
        ("reference_duration_reference", "wrong:duration", ValueError),
        ("reference_duration_digest", "3" * 65, ValueError),
        ("eligible_case_set_digest", "4" * 63, ValueError),
        ("weight_artifact_digest", "5" * 65, ValueError),
        ("constructed_at", datetime(2026, 9, 16, 12, 0), ValueError),
        ("owner_contract_reference", "wrong:contract", ValueError),
        ("owner_contract_version", 0, ValueError),
        ("owner_contract_digest", "6" * 63, ValueError),
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


def test_record_and_view_are_structurally_immutable_and_uuid_views_are_detached() -> None:
    tenant = UUID(str(TENANT))
    record = _record(tenant_record_id=tenant)
    object.__setattr__(tenant, "int", OTHER_TENANT.int)
    assert record.tenant_record_id == TENANT
    with pytest.raises(AttributeError):
        object.__setattr__(record, "weight_scope_code", "cross_sectional")

    view = _resolve(read_port=_ReadPort(record))
    returned_tenant = view.tenant_record_id
    object.__setattr__(returned_tenant, "int", OTHER_TENANT.int)
    assert view.tenant_record_id == TENANT
    with pytest.raises(AttributeError):
        object.__setattr__(view, "fields", ())
    with pytest.raises(TypeError):
        WeightEligibilityAuthorityView(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            fields=(),
        )
