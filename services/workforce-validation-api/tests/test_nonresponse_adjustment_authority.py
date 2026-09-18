"""Fail-closed contract for released typed nonresponse-adjustment authority."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.nonresponse_adjustment_authority import (
    NonresponseAdjustmentAuthorityIntegrityError,
    NonresponseAdjustmentAuthorityNotFound,
    NonresponseAdjustmentAuthorityReadPort,
    NonresponseAdjustmentAuthorityRecord,
    NonresponseAdjustmentAuthorityView,
    resolve_nonresponse_adjustment_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000002")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
OTHER_STUDY = UUID("00000000-0000-7000-8000-0000000000d2")
RECEIPT_REFERENCE = "nonresponse_adjustment_receipt:11111111-1111-4111-8111-111111111111"
DISPOSITION_REFERENCE = "response_disposition_receipt:22222222-2222-4222-8222-222222222222"
OWNER_CONTRACT_REFERENCE = "released_owner_contract:33333333-3333-4333-8333-333333333333"
RECEIPT_DIGEST = "1" * 64
DISPOSITION_DIGEST = "2" * 64
POPULATION_DIGEST = "3" * 64
CONFIGURATION_DIGEST = "4" * 64
INPUT_WEIGHT_DIGEST = "5" * 64
OUTPUT_WEIGHT_DIGEST = "6" * 64
OWNER_CONTRACT_DIGEST = "7" * 64
DISPOSITION_RELEASED_AT = datetime(2026, 9, 16, 10, 0, tzinfo=timezone.utc)
CONSTRUCTED_AT = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 9, 16, 12, 30, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "nonresponse_receipt_reference",
        "nonresponse_receipt_digest",
        "evidence_version",
        "response_disposition_receipt_reference",
        "response_disposition_receipt_version",
        "response_disposition_receipt_digest",
        "response_disposition_receipt_released_at",
        "adjustment_population_digest",
        "method_reference",
        "method_version",
        "configuration_digest",
        "ineligible_treatment_code",
        "unknown_treatment_code",
        "unavailable_treatment_code",
        "input_weight_artifact_digest",
        "output_weight_artifact_digest",
        "constructed_at",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
    }
)


class _ReadPort:
    """Return configured nonresponse authority and retain lookup coordinates."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def read_nonresponse_adjustment_authority(self, **coordinates: object) -> object:
        """Capture the owner lookup and return configured evidence."""
        self.calls.append(dict(coordinates))
        return self.result


class _NoReadMethod:
    """Deliberately fail the owner-port protocol."""


class _ProtocolOnly(NonresponseAdjustmentAuthorityReadPort):
    """Inherit only the Protocol placeholder, not a concrete owner capability."""


class _DescriptorReadPort:
    """Expose a descriptor that must be rejected without executing it."""

    @property
    def read_nonresponse_adjustment_authority(self) -> object:
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
        policy_version_code="nonresponse-adjustment-authority-read-v1",
        resource_kind="nonresponse_adjustment_authority",
        purpose_code=purpose_code,
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def _record(**overrides: object) -> NonresponseAdjustmentAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "nonresponse_receipt_reference": RECEIPT_REFERENCE,
        "nonresponse_receipt_digest": RECEIPT_DIGEST,
        "evidence_version": 1,
        "response_disposition_receipt_reference": DISPOSITION_REFERENCE,
        "response_disposition_receipt_version": 4,
        "response_disposition_receipt_digest": DISPOSITION_DIGEST,
        "response_disposition_receipt_released_at": DISPOSITION_RELEASED_AT,
        "adjustment_population_digest": POPULATION_DIGEST,
        "method_reference": "weight_method:response_propensity_cells",
        "method_version": 3,
        "configuration_digest": CONFIGURATION_DIGEST,
        "ineligible_treatment_code": "exclude_ineligible",
        "unknown_treatment_code": "retain_unknown_class",
        "unavailable_treatment_code": "retain_unavailable_class",
        "input_weight_artifact_digest": INPUT_WEIGHT_DIGEST,
        "output_weight_artifact_digest": OUTPUT_WEIGHT_DIGEST,
        "constructed_at": CONSTRUCTED_AT,
        "owner_contract_reference": OWNER_CONTRACT_REFERENCE,
        "owner_contract_version": 5,
        "owner_contract_digest": OWNER_CONTRACT_DIGEST,
        "owner_contract_released_at": OWNER_CONTRACT_RELEASED_AT,
        "released_at": RELEASED_AT,
    }
    values.update(overrides)
    return NonresponseAdjustmentAuthorityRecord(**values)


def _resolve(*, read_port: object, **overrides: object) -> NonresponseAdjustmentAuthorityView:
    values: dict[str, object] = {
        "principal": _principal(),
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "nonresponse_receipt_reference": RECEIPT_REFERENCE,
        "nonresponse_receipt_digest": RECEIPT_DIGEST,
        "evidence_version": 1,
        "response_disposition_receipt_reference": DISPOSITION_REFERENCE,
        "response_disposition_receipt_version": 4,
        "response_disposition_receipt_digest": DISPOSITION_DIGEST,
        "adjustment_population_digest": POPULATION_DIGEST,
        "method_reference": "weight_method:response_propensity_cells",
        "method_version": 3,
        "configuration_digest": CONFIGURATION_DIGEST,
        "ineligible_treatment_code": "exclude_ineligible",
        "unknown_treatment_code": "retain_unknown_class",
        "unavailable_treatment_code": "retain_unavailable_class",
        "input_weight_artifact_digest": INPUT_WEIGHT_DIGEST,
        "output_weight_artifact_digest": OUTPUT_WEIGHT_DIGEST,
        "constructed_at": CONSTRUCTED_AT,
        "owner_contract_reference": OWNER_CONTRACT_REFERENCE,
        "owner_contract_version": 5,
        "owner_contract_digest": OWNER_CONTRACT_DIGEST,
        "used_at": USED_AT,
        "purpose_code": "selection_validity_analysis",
        "policy": _policy(),
        "read_port": read_port,
    }
    values.update(overrides)
    return resolve_nonresponse_adjustment_authority(**values)


def test_resolution_binds_versioned_disposition_and_treatment_evidence() -> None:
    port = _ReadPort(_record())

    view = _resolve(read_port=port)

    assert isinstance(port, NonresponseAdjustmentAuthorityReadPort)
    assert len(port.calls) == 1
    assert port.calls[0]["response_disposition_receipt_reference"] == DISPOSITION_REFERENCE
    assert port.calls[0]["response_disposition_receipt_version"] == 4
    assert port.calls[0]["response_disposition_receipt_digest"] == DISPOSITION_DIGEST
    assert view.tenant_record_id == TENANT
    assert view.validity_study_id == STUDY
    assert ("method_reference", "weight_method:response_propensity_cells") in view.fields
    assert ("ineligible_treatment_code", "exclude_ineligible") in view.fields
    assert ("unknown_treatment_code", "retain_unknown_class") in view.fields
    assert ("unavailable_treatment_code", "retain_unavailable_class") in view.fields
    assert ("response_disposition_receipt_released_at", DISPOSITION_RELEASED_AT) in view.fields
    assert ("owner_contract_released_at", OWNER_CONTRACT_RELEASED_AT) in view.fields
    assert ("superseded_at", None) in view.fields


def test_authorization_denial_happens_before_owner_resolution() -> None:
    port = _ReadPort(_record())

    with pytest.raises(AuthorizationDeniedError):
        _resolve(read_port=port, policy=_policy(purpose_code="audit_review"))

    assert port.calls == []


def test_missing_or_noncanonical_owner_evidence_fails_closed() -> None:
    with pytest.raises(NonresponseAdjustmentAuthorityNotFound):
        _resolve(read_port=_ReadPort(None))

    with pytest.raises(NonresponseAdjustmentAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(object()))


@pytest.mark.parametrize(
    "record_overrides",
    [
        {"tenant_record_id": OTHER_TENANT},
        {"validity_study_id": OTHER_STUDY},
        {"nonresponse_receipt_digest": "a" * 64},
        {"response_disposition_receipt_reference": "response_disposition_receipt:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"},
        {"response_disposition_receipt_version": 5},
        {"response_disposition_receipt_digest": "b" * 64},
        {"adjustment_population_digest": "c" * 64},
        {"method_reference": "weight_method:response_propensity_model"},
        {"method_version": 4},
        {"configuration_digest": "d" * 64},
        {"unknown_treatment_code": "exclude_unknown"},
        {"input_weight_artifact_digest": "e" * 64},
        {"output_weight_artifact_digest": "f" * 64},
        {"owner_contract_version": 6},
        {"owner_contract_digest": "0" * 64},
    ],
)
def test_owner_evidence_must_match_every_requested_coordinate(
    record_overrides: dict[str, object]
) -> None:
    with pytest.raises(NonresponseAdjustmentAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(**record_overrides)))


def test_owner_resolved_input_release_and_currentness_chronology_fail_closed() -> None:
    with pytest.raises(ValueError):
        _record(response_disposition_receipt_released_at=CONSTRUCTED_AT + timedelta(seconds=1))

    with pytest.raises(ValueError):
        _record(released_at=CONSTRUCTED_AT - timedelta(seconds=1))

    with pytest.raises(ValueError, match="superseded_at must be later"):
        _record(superseded_at=RELEASED_AT)

    with pytest.raises(ValueError, match="timezone-aware"):
        _record(superseded_at=datetime(2026, 9, 16, 14, 0))

    with pytest.raises(NonresponseAdjustmentAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(released_at=USED_AT + timedelta(seconds=1))))

    cutover = RELEASED_AT + timedelta(hours=1)
    historical = _resolve(
        read_port=_ReadPort(_record(superseded_at=cutover)),
        used_at=cutover - timedelta(seconds=1),
    )
    assert ("superseded_at", cutover) in historical.fields

    with pytest.raises(
        NonresponseAdjustmentAuthorityIntegrityError,
        match="superseded for this scientific-use instant",
    ):
        _resolve(
            read_port=_ReadPort(_record(superseded_at=cutover)),
            used_at=cutover,
        )


def test_weight_artifact_aliasing_fails_closed() -> None:
    with pytest.raises(ValueError):
        _record(output_weight_artifact_digest=INPUT_WEIGHT_DIGEST)


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
        ("nonresponse_receipt_reference", "wrong:receipt", ValueError),
        ("nonresponse_receipt_digest", "ABC", ValueError),
        ("evidence_version", False, ValueError),
        ("response_disposition_receipt_reference", "wrong:receipt", ValueError),
        ("response_disposition_receipt_version", 0, ValueError),
        ("response_disposition_receipt_digest", "2" * 63, ValueError),
        ("adjustment_population_digest", "3" * 65, ValueError),
        ("method_reference", "wrong:method", ValueError),
        ("method_version", True, ValueError),
        ("configuration_digest", "4" * 63, ValueError),
        ("ineligible_treatment_code", "Exclude Ineligible", ValueError),
        ("unknown_treatment_code", "Unknown Treatment", ValueError),
        ("unavailable_treatment_code", "Unavailable Treatment", ValueError),
        ("constructed_at", datetime(2026, 9, 16, 12, 0), ValueError),
        ("owner_contract_reference", "wrong:contract", ValueError),
        ("owner_contract_version", 0, ValueError),
        ("owner_contract_digest", "7" * 63, ValueError),
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
        object.__setattr__(record, "method_version", 99)

    view = _resolve(read_port=_ReadPort(record))
    returned_tenant = view.tenant_record_id
    object.__setattr__(returned_tenant, "int", OTHER_TENANT.int)
    assert view.tenant_record_id == TENANT

    with pytest.raises(AttributeError):
        object.__setattr__(view, "fields", ())
    with pytest.raises(TypeError):
        NonresponseAdjustmentAuthorityView(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            fields=(),
        )
