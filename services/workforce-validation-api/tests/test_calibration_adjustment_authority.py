"""Fail-closed contract for released typed calibration-adjustment authority."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.calibration_adjustment_authority import (
    CalibrationAdjustmentAuthorityIntegrityError,
    CalibrationAdjustmentAuthorityNotFound,
    CalibrationAdjustmentAuthorityReadPort,
    CalibrationAdjustmentAuthorityRecord,
    CalibrationAdjustmentAuthorityView,
    resolve_calibration_adjustment_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000002")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
OTHER_STUDY = UUID("00000000-0000-7000-8000-0000000000d2")
RECEIPT_REFERENCE = "calibration_adjustment_receipt:11111111-1111-4111-8111-111111111111"
OWNER_CONTRACT_REFERENCE = "released_owner_contract:22222222-2222-4222-8222-222222222222"
RECEIPT_DIGEST = "1" * 64
AUXILIARY_PROJECTION_DIGEST = "2" * 64
BENCHMARK_RECEIPT_DIGEST = "3" * 64
CONSTRAINTS_DIGEST = "4" * 64
INPUT_WEIGHT_DIGEST = "5" * 64
OUTPUT_WEIGHT_DIGEST = "6" * 64
FALLBACK_RULE_DIGEST = "7" * 64
FALLBACK_CONFIGURATION_DIGEST = "8" * 64
OWNER_CONTRACT_DIGEST = "9" * 64
CONSTRUCTED_AT = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 9, 16, 12, 30, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "calibration_receipt_reference",
        "calibration_receipt_digest",
        "evidence_version",
        "auxiliary_projection_digest",
        "benchmark_receipt_digest",
        "algorithm_reference",
        "algorithm_version",
        "constraints_digest",
        "termination_code",
        "input_weight_artifact_digest",
        "output_weight_artifact_digest",
        "constructed_at",
        "fallback_reason_code",
        "fallback_rule_reference",
        "fallback_rule_digest",
        "fallback_algorithm_reference",
        "fallback_algorithm_version",
        "fallback_configuration_digest",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
    }
)


class _ReadPort:
    """Return configured calibration authority and retain lookup coordinates."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def read_calibration_adjustment_authority(self, **coordinates: object) -> object:
        """Capture the owner lookup and return configured evidence."""
        self.calls.append(dict(coordinates))
        return self.result


class _NoReadMethod:
    """Deliberately fail the owner-port protocol."""


class _ProtocolOnly(CalibrationAdjustmentAuthorityReadPort):
    """Inherit only the Protocol placeholder, not a concrete owner capability."""


class _DescriptorReadPort:
    """Expose a descriptor that must be rejected without executing it."""

    @property
    def read_calibration_adjustment_authority(self) -> object:
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
        policy_version_code="calibration-adjustment-authority-read-v1",
        resource_kind="calibration_adjustment_authority",
        purpose_code=purpose_code,
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def _fallback_values() -> dict[str, object]:
    return {
        "termination_code": "fallback_applied",
        "fallback_reason_code": "primary_nonconvergence",
        "fallback_rule_reference": "calibration_fallback_rule:cell-collapse-v2",
        "fallback_rule_digest": FALLBACK_RULE_DIGEST,
        "fallback_algorithm_reference": "calibration_algorithm:raking",
        "fallback_algorithm_version": 4,
        "fallback_configuration_digest": FALLBACK_CONFIGURATION_DIGEST,
    }


def _record(**overrides: object) -> CalibrationAdjustmentAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "calibration_receipt_reference": RECEIPT_REFERENCE,
        "calibration_receipt_digest": RECEIPT_DIGEST,
        "evidence_version": 1,
        "auxiliary_projection_digest": AUXILIARY_PROJECTION_DIGEST,
        "benchmark_receipt_digest": BENCHMARK_RECEIPT_DIGEST,
        "algorithm_reference": "calibration_algorithm:generalized_regression",
        "algorithm_version": 3,
        "constraints_digest": CONSTRAINTS_DIGEST,
        "termination_code": "converged",
        "input_weight_artifact_digest": INPUT_WEIGHT_DIGEST,
        "output_weight_artifact_digest": OUTPUT_WEIGHT_DIGEST,
        "constructed_at": CONSTRUCTED_AT,
        "fallback_reason_code": None,
        "fallback_rule_reference": None,
        "fallback_rule_digest": None,
        "fallback_algorithm_reference": None,
        "fallback_algorithm_version": None,
        "fallback_configuration_digest": None,
        "owner_contract_reference": OWNER_CONTRACT_REFERENCE,
        "owner_contract_version": 6,
        "owner_contract_digest": OWNER_CONTRACT_DIGEST,
        "owner_contract_released_at": OWNER_CONTRACT_RELEASED_AT,
        "released_at": RELEASED_AT,
    }
    values.update(overrides)
    return CalibrationAdjustmentAuthorityRecord(**values)


def _resolve(*, read_port: object, **overrides: object) -> CalibrationAdjustmentAuthorityView:
    values: dict[str, object] = {
        "principal": _principal(),
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "calibration_receipt_reference": RECEIPT_REFERENCE,
        "calibration_receipt_digest": RECEIPT_DIGEST,
        "evidence_version": 1,
        "auxiliary_projection_digest": AUXILIARY_PROJECTION_DIGEST,
        "benchmark_receipt_digest": BENCHMARK_RECEIPT_DIGEST,
        "algorithm_reference": "calibration_algorithm:generalized_regression",
        "algorithm_version": 3,
        "constraints_digest": CONSTRAINTS_DIGEST,
        "termination_code": "converged",
        "input_weight_artifact_digest": INPUT_WEIGHT_DIGEST,
        "output_weight_artifact_digest": OUTPUT_WEIGHT_DIGEST,
        "constructed_at": CONSTRUCTED_AT,
        "fallback_reason_code": None,
        "fallback_rule_reference": None,
        "fallback_rule_digest": None,
        "fallback_algorithm_reference": None,
        "fallback_algorithm_version": None,
        "fallback_configuration_digest": None,
        "owner_contract_reference": OWNER_CONTRACT_REFERENCE,
        "owner_contract_version": 6,
        "owner_contract_digest": OWNER_CONTRACT_DIGEST,
        "used_at": USED_AT,
        "purpose_code": "selection_validity_analysis",
        "policy": _policy(),
        "read_port": read_port,
    }
    values.update(overrides)
    return resolve_calibration_adjustment_authority(**values)


def test_fallback_resolution_binds_actual_generating_method() -> None:
    fallback = _fallback_values()
    record = _record(**fallback)
    port = _ReadPort(record)

    view = _resolve(read_port=port, **fallback)

    assert isinstance(port, CalibrationAdjustmentAuthorityReadPort)
    assert len(port.calls) == 1
    assert port.calls[0]["calibration_receipt_digest"] == RECEIPT_DIGEST
    assert port.calls[0]["fallback_algorithm_reference"] == "calibration_algorithm:raking"
    assert view.tenant_record_id == TENANT
    assert view.validity_study_id == STUDY
    assert ("termination_code", "fallback_applied") in view.fields
    assert ("fallback_reason_code", "primary_nonconvergence") in view.fields
    assert ("fallback_rule_reference", "calibration_fallback_rule:cell-collapse-v2") in view.fields
    assert ("fallback_algorithm_reference", "calibration_algorithm:raking") in view.fields
    assert ("fallback_algorithm_version", 4) in view.fields
    assert ("fallback_configuration_digest", FALLBACK_CONFIGURATION_DIGEST) in view.fields
    assert ("owner_contract_released_at", OWNER_CONTRACT_RELEASED_AT) in view.fields


def test_converged_resolution_omits_fallback_only_projection() -> None:
    view = _resolve(read_port=_ReadPort(_record()))

    assert ("termination_code", "converged") in view.fields
    assert all(not field.startswith("fallback_") for field, _ in view.fields)


def test_authorization_denial_happens_before_owner_resolution() -> None:
    port = _ReadPort(_record())

    with pytest.raises(AuthorizationDeniedError):
        _resolve(read_port=port, policy=_policy(purpose_code="audit_review"))

    assert port.calls == []


def test_missing_or_noncanonical_owner_evidence_fails_closed() -> None:
    with pytest.raises(CalibrationAdjustmentAuthorityNotFound):
        _resolve(read_port=_ReadPort(None))

    with pytest.raises(CalibrationAdjustmentAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(object()))


@pytest.mark.parametrize(
    "record_overrides",
    [
        {"tenant_record_id": OTHER_TENANT},
        {"validity_study_id": OTHER_STUDY},
        {"calibration_receipt_digest": "a" * 64},
        {"auxiliary_projection_digest": "b" * 64},
        {"benchmark_receipt_digest": "c" * 64},
        {"algorithm_reference": "calibration_algorithm:raking"},
        {"algorithm_version": 9},
        {"constraints_digest": "d" * 64},
        {"input_weight_artifact_digest": "e" * 64},
        {"output_weight_artifact_digest": "f" * 64},
        {"owner_contract_version": 7},
        {"owner_contract_digest": "0" * 64},
    ],
)
def test_owner_evidence_must_match_every_requested_coordinate(
    record_overrides: dict[str, object]
) -> None:
    with pytest.raises(CalibrationAdjustmentAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(**record_overrides)))


def test_owner_evidence_must_be_released_before_scientific_use() -> None:
    with pytest.raises(CalibrationAdjustmentAuthorityIntegrityError):
        _resolve(
            read_port=_ReadPort(_record(released_at=USED_AT + timedelta(seconds=1)))
        )


@pytest.mark.parametrize(
    "missing_field",
    [
        "fallback_reason_code",
        "fallback_rule_reference",
        "fallback_rule_digest",
        "fallback_algorithm_reference",
        "fallback_algorithm_version",
        "fallback_configuration_digest",
    ],
)
def test_fallback_requires_complete_actual_method_provenance(missing_field: str) -> None:
    fallback = _fallback_values()
    fallback[missing_field] = None
    with pytest.raises(ValueError):
        _record(**fallback)


def test_converged_receipt_rejects_fallback_only_evidence() -> None:
    with pytest.raises(ValueError):
        _record(fallback_reason_code="should_not_exist")


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("evidence_version", 2),
        ("termination_code", "nonconverged"),
        ("algorithm_reference", "wrong:method"),
        ("algorithm_version", True),
        ("fallback_reason_code", "Primary Failure"),
        ("fallback_rule_reference", "wrong:rule"),
        ("fallback_rule_digest", "7" * 63),
        ("fallback_algorithm_reference", "wrong:algorithm"),
        ("fallback_algorithm_version", 0),
        ("fallback_configuration_digest", "8" * 65),
    ],
)
def test_malformed_calibration_or_fallback_evidence_fails_closed(
    key: str, value: object
) -> None:
    overrides = _fallback_values()
    overrides[key] = value
    with pytest.raises(ValueError):
        _record(**overrides)


def test_weight_artifact_and_release_chronology_fail_closed() -> None:
    with pytest.raises(ValueError):
        _record(output_weight_artifact_digest=INPUT_WEIGHT_DIGEST)

    with pytest.raises(ValueError):
        _record(released_at=CONSTRUCTED_AT - timedelta(seconds=1))


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
        ("calibration_receipt_reference", "wrong:receipt", ValueError),
        ("calibration_receipt_digest", "ABC", ValueError),
        ("evidence_version", False, ValueError),
        ("auxiliary_projection_digest", "2" * 63, ValueError),
        ("benchmark_receipt_digest", "3" * 65, ValueError),
        ("algorithm_reference", "wrong:algorithm", ValueError),
        ("algorithm_version", 0, ValueError),
        ("constraints_digest", "4" * 63, ValueError),
        ("termination_code", "failed", ValueError),
        ("constructed_at", datetime(2026, 9, 16, 12, 0), ValueError),
        ("owner_contract_reference", "wrong:contract", ValueError),
        ("owner_contract_version", 0, ValueError),
        ("owner_contract_digest", "9" * 63, ValueError),
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
        object.__setattr__(record, "termination_code", "fallback_applied")

    view = _resolve(read_port=_ReadPort(record))
    returned_tenant = view.tenant_record_id
    object.__setattr__(returned_tenant, "int", OTHER_TENANT.int)
    assert view.tenant_record_id == TENANT

    with pytest.raises(AttributeError):
        object.__setattr__(view, "fields", ())
    with pytest.raises(TypeError):
        CalibrationAdjustmentAuthorityView(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            fields=(),
        )
