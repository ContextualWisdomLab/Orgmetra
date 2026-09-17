"""Branch and hostile-input coverage for weight/variance authority resolution."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.variance_authority import (
    WeightVarianceAuthorityIntegrityError,
    WeightVarianceAuthorityReadPort,
    WeightVarianceAuthorityRecord,
    resolve_weight_variance_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000002")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
OTHER_STUDY = UUID("00000000-0000-7000-8000-0000000000d2")
AUTHORITY_REFERENCE = "variance_compatibility_authority:11111111-1111-4111-8111-111111111111"
SAMPLING_REFERENCE = "sampling_design_receipt:22222222-2222-4222-8222-222222222222"
VARIANCE_REFERENCE = "variance_design_receipt:33333333-3333-4333-8333-333333333333"
METHOD_REFERENCE = "variance_method:44444444-4444-4444-8444-444444444444"
OWNER_REFERENCE = "released_owner_contract:55555555-5555-4555-8555-555555555555"
SAMPLING_DIGEST = "1" * 64
ANALYSIS_WEIGHT_DIGEST = "2" * 64
CASE_SET_DIGEST = "3" * 64
ELIGIBILITY_DIGEST = "4" * 64
CORRECTION_SEQUENCE = 9
FINAL_WEIGHT_DIGEST = "6" * 64
VARIANCE_DIGEST = "7" * 64
OWNER_DIGEST = "8" * 64
OWNER_RELEASED_AT = datetime(2026, 9, 17, 0, 30, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 1, 0, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, 2, 0, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "authority_reference",
        "sampling_receipt_reference",
        "sampling_receipt_version",
        "sampling_receipt_digest",
        "analysis_weight_receipt_digest",
        "analytic_case_occurrence_set_digest",
        "weight_eligibility_receipt_digest",
        "weight_correction_sequence",
        "final_weight_artifact_digest",
        "variance_design_receipt_reference",
        "variance_design_receipt_version",
        "variance_design_receipt_digest",
        "variance_method_reference",
        "variance_method_version",
        "variance_evidence_mode",
        "variance_semantics",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
    }
)


class _Port:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls = 0

    def read_weight_variance_authority(self, **_: object) -> object:
        self.calls += 1
        return self.result


class _NoMethod:
    pass


class _ProtocolOnly(WeightVarianceAuthorityReadPort):
    pass


class _Descriptor:
    @property
    def read_weight_variance_authority(self) -> object:
        raise AssertionError("descriptor must not execute")


def _principal() -> ValidationPrincipal:
    return ValidationPrincipal(
        tenant_record_id=TENANT,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )


def _policy() -> PurposeBoundAccessPolicy:
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="weight-variance-authority-read-v2",
        resource_kind="weight_variance_authority",
        purpose_code="selection_validity_analysis",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def _record(**overrides: object) -> WeightVarianceAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "authority_reference": AUTHORITY_REFERENCE,
        "sampling_receipt_reference": SAMPLING_REFERENCE,
        "sampling_receipt_version": 3,
        "sampling_receipt_digest": SAMPLING_DIGEST,
        "analysis_weight_receipt_digest": ANALYSIS_WEIGHT_DIGEST,
        "analytic_case_occurrence_set_digest": CASE_SET_DIGEST,
        "weight_eligibility_receipt_digest": ELIGIBILITY_DIGEST,
        "weight_correction_sequence": CORRECTION_SEQUENCE,
        "final_weight_artifact_digest": FINAL_WEIGHT_DIGEST,
        "variance_design_receipt_reference": VARIANCE_REFERENCE,
        "variance_design_receipt_version": 5,
        "variance_design_receipt_digest": VARIANCE_DIGEST,
        "variance_method_reference": METHOD_REFERENCE,
        "variance_method_version": 2,
        "variance_evidence_mode": "replicate_weights",
        "variance_semantics": "exact",
        "owner_contract_reference": OWNER_REFERENCE,
        "owner_contract_version": 4,
        "owner_contract_digest": OWNER_DIGEST,
        "owner_contract_released_at": OWNER_RELEASED_AT,
        "released_at": RELEASED_AT,
        "superseded_at": None,
    }
    values.update(overrides)
    return WeightVarianceAuthorityRecord(**values)


def _resolve(*, result: object | None = None, read_port: object | None = None, **overrides: object):
    port = _Port(_record() if result is None else result) if read_port is None else read_port
    values: dict[str, object] = {
        "principal": _principal(),
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "sampling_receipt_reference": SAMPLING_REFERENCE,
        "sampling_receipt_version": 3,
        "sampling_receipt_digest": SAMPLING_DIGEST,
        "analysis_weight_receipt_digest": ANALYSIS_WEIGHT_DIGEST,
        "analytic_case_occurrence_set_digest": CASE_SET_DIGEST,
        "weight_eligibility_receipt_digest": ELIGIBILITY_DIGEST,
        "weight_correction_sequence": CORRECTION_SEQUENCE,
        "final_weight_artifact_digest": FINAL_WEIGHT_DIGEST,
        "variance_design_receipt_reference": VARIANCE_REFERENCE,
        "variance_design_receipt_version": 5,
        "variance_design_receipt_digest": VARIANCE_DIGEST,
        "variance_method_reference": METHOD_REFERENCE,
        "variance_method_version": 2,
        "variance_evidence_mode": "replicate_weights",
        "variance_semantics": "exact",
        "owner_contract_reference": OWNER_REFERENCE,
        "owner_contract_version": 4,
        "used_at": USED_AT,
        "purpose_code": "selection_validity_analysis",
        "policy": _policy(),
        "read_port": port,
    }
    values.update(overrides)
    return resolve_weight_variance_authority(**values)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("tenant_record_id", "not-a-uuid"),
        ("validity_study_id", UUID(int=0)),
        ("authority_reference", 42),
        ("authority_reference", "not-a-reference"),
        ("authority_reference", "wrong:authority"),
        ("sampling_receipt_reference", "wrong:sampling"),
        ("sampling_receipt_version", True),
        ("sampling_receipt_version", 0),
        ("sampling_receipt_digest", 42),
        ("sampling_receipt_digest", "1" * 63),
        ("analysis_weight_receipt_digest", "2" * 63),
        ("analytic_case_occurrence_set_digest", "3" * 65),
        ("weight_eligibility_receipt_digest", "4" * 63),
        ("weight_correction_sequence", True),
        ("weight_correction_sequence", 0),
        ("final_weight_artifact_digest", "6" * 63),
        ("variance_design_receipt_reference", "wrong:variance"),
        ("variance_design_receipt_version", 0),
        ("variance_design_receipt_digest", "7" * 63),
        ("variance_method_reference", "wrong:method"),
        ("variance_method_version", False),
        ("variance_evidence_mode", 42),
        ("variance_evidence_mode", "unknown"),
        ("variance_semantics", 42),
        ("variance_semantics", "unknown"),
        ("owner_contract_reference", "wrong:owner"),
        ("owner_contract_version", 0),
        ("owner_contract_digest", "8" * 63),
        ("owner_contract_released_at", datetime(2026, 9, 17, 0, 30)),
        ("released_at", datetime(2026, 9, 17, 1, 0)),
        ("superseded_at", datetime(2026, 9, 17, 3, 0)),
        ("superseded_at", RELEASED_AT),
    ],
)
def test_record_rejects_malformed_authority_evidence(key: str, value: object) -> None:
    with pytest.raises(ValueError):
        _record(**{key: value})


def test_approximation_mode_accepts_only_explicit_approximate_semantics() -> None:
    record = _record(variance_evidence_mode="approximation", variance_semantics="approximate")
    assert record.variance_evidence_mode == "approximation"
    assert record.variance_semantics == "approximate"


@pytest.mark.parametrize(
    ("key", "value", "error"),
    [
        ("principal", object(), TypeError),
        ("policy", object(), TypeError),
        ("tenant_record_id", "not-a-uuid", ValueError),
        ("validity_study_id", UUID(int=0), ValueError),
        ("sampling_receipt_reference", "wrong:sampling", ValueError),
        ("sampling_receipt_version", True, ValueError),
        ("sampling_receipt_digest", "1" * 63, ValueError),
        ("analysis_weight_receipt_digest", "2" * 63, ValueError),
        ("analytic_case_occurrence_set_digest", "3" * 63, ValueError),
        ("weight_eligibility_receipt_digest", "4" * 63, ValueError),
        ("weight_correction_sequence", 0, ValueError),
        ("final_weight_artifact_digest", "6" * 63, ValueError),
        ("variance_design_receipt_reference", "wrong:variance", ValueError),
        ("variance_design_receipt_version", 0, ValueError),
        ("variance_design_receipt_digest", "7" * 63, ValueError),
        ("variance_method_reference", "wrong:method", ValueError),
        ("variance_method_version", 0, ValueError),
        ("variance_evidence_mode", "unknown", ValueError),
        ("variance_semantics", "unknown", ValueError),
        ("owner_contract_reference", "wrong:owner", ValueError),
        ("owner_contract_version", False, ValueError),
        ("used_at", datetime(2026, 9, 17, 2, 0), ValueError),
        ("purpose_code", "Selection Validity Analysis", ValueError),
    ],
)
def test_invalid_request_fails_before_owner_resolution(
    key: str, value: object, error: type[Exception]
) -> None:
    port = _Port(_record())
    with pytest.raises(error):
        _resolve(read_port=port, **{key: value})
    assert port.calls == 0


@pytest.mark.parametrize("read_port", [_NoMethod(), _ProtocolOnly(), _Descriptor()])
def test_nonconcrete_owner_capabilities_are_rejected_without_execution(read_port: object) -> None:
    with pytest.raises(TypeError):
        _resolve(read_port=read_port)


@pytest.mark.parametrize(
    "record_overrides",
    [
        {"tenant_record_id": OTHER_TENANT},
        {"validity_study_id": OTHER_STUDY},
        {"sampling_receipt_reference": "sampling_design_receipt:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"},
        {"sampling_receipt_version": 4},
        {"sampling_receipt_digest": "a" * 64},
        {"analysis_weight_receipt_digest": "b" * 64},
        {"analytic_case_occurrence_set_digest": "c" * 64},
        {"weight_eligibility_receipt_digest": "d" * 64},
        {"weight_correction_sequence": 10},
        {"final_weight_artifact_digest": "f" * 64},
        {"variance_design_receipt_reference": "variance_design_receipt:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"},
        {"variance_design_receipt_version": 6},
        {"variance_design_receipt_digest": "a" * 64},
        {"variance_method_reference": "variance_method:cccccccc-cccc-4ccc-8ccc-cccccccccccc"},
        {"variance_method_version": 3},
        {"variance_evidence_mode": "joint_inclusion"},
        {"variance_semantics": "approximate"},
        {"owner_contract_reference": "released_owner_contract:dddddddd-dddd-4ddd-8ddd-dddddddddddd"},
        {"owner_contract_version": 5},
    ],
)
def test_every_requested_coordinate_must_match_owner_evidence(
    record_overrides: dict[str, object]
) -> None:
    with pytest.raises(WeightVarianceAuthorityIntegrityError):
        _resolve(result=_record(**record_overrides))


def test_uuid_views_are_detached_from_retained_references() -> None:
    tenant = UUID(str(TENANT))
    record = _record(tenant_record_id=tenant)
    object.__setattr__(tenant, "int", OTHER_TENANT.int)
    assert record.tenant_record_id == TENANT

    view = _resolve(result=record)
    returned = view.tenant_record_id
    object.__setattr__(returned, "int", OTHER_TENANT.int)
    assert view.tenant_record_id == TENANT
