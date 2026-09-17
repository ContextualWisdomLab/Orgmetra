"""Fail-closed contract for complete released final analysis-weight provenance."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.final_weight_authority import (
    FinalAnalysisWeightAuthorityIntegrityError,
    FinalAnalysisWeightAuthorityNotFound,
    FinalAnalysisWeightAuthorityReadPort,
    FinalAnalysisWeightAuthorityRecord,
    FinalAnalysisWeightAuthorityView,
    FinalWeightAdjustmentCoordinate,
    resolve_final_analysis_weight_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000002")
STUDY = UUID("00000000-0000-7000-8000-0000000000f1")
OTHER_STUDY = UUID("00000000-0000-7000-8000-0000000000f2")
WEIGHT_RECEIPT_REFERENCE = "analysis_weight_receipt:11111111-1111-4111-8111-111111111111"
ESTIMAND_REFERENCE = "validation_estimand:criterion-validity-q3"
TARGET_REFERENCE = "analysis_target_population:workers-2026q3"
WINDOW_REFERENCE = "analysis_window:2026q3"
DURATION_REFERENCE = "analysis_reference_duration:2026q3"
SOURCE_REFERENCE = "source_universe_receipt:22222222-2222-4222-8222-222222222222"
SAMPLING_REFERENCE = "sampling_design_receipt:33333333-3333-4333-8333-333333333333"
ELIGIBILITY_REFERENCE = "weight_eligibility_receipt:44444444-4444-4444-8444-444444444444"
OWNER_REFERENCE = "released_owner_contract:55555555-5555-4555-8555-555555555555"
METHOD_REFERENCE = "weight_method:nonresponse-cell-adjustment"
WEIGHT_RECEIPT_DIGEST = "1" * 64
ESTIMAND_DIGEST = "2" * 64
TARGET_DIGEST = "3" * 64
DURATION_DIGEST = "4" * 64
ELIGIBLE_CASE_DIGEST = "5" * 64
ANALYTIC_CASE_DIGEST = "6" * 64
SOURCE_DIGEST = "7" * 64
SAMPLING_DIGEST = "8" * 64
BASE_EVIDENCE_DIGEST = "9" * 64
BASE_ARTIFACT_DIGEST = "a" * 64
ADJUSTED_ARTIFACT_DIGEST = "b" * 64
ADJUSTMENT_CONFIG_DIGEST = "c" * 64
ADJUSTMENT_RECEIPT_DIGEST = "d" * 64
ELIGIBILITY_DIGEST = "e" * 64
OWNER_DIGEST = "f" * 64
SUPERSEDES_DIGEST = "0" * 64
CONSTRUCTED_AT = datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 8, 30, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, 9, 0, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "analysis_weight_receipt_reference",
        "analysis_weight_receipt_digest",
        "evidence_version",
        "estimand_reference",
        "estimand_digest",
        "estimand_scope_code",
        "target_population_reference",
        "target_population_digest",
        "analysis_unit_code",
        "analysis_window_reference",
        "reference_duration_reference",
        "reference_duration_digest",
        "eligible_case_set_digest",
        "analytic_case_occurrence_set_digest",
        "source_universe_receipt_reference",
        "source_universe_receipt_version",
        "source_universe_receipt_digest",
        "sampling_design_receipt_reference",
        "sampling_design_receipt_version",
        "sampling_design_receipt_digest",
        "base_weight_method_code",
        "base_weight_method_version",
        "base_weight_evidence_digest",
        "base_weight_artifact_digest",
        "adjustments",
        "final_weight_artifact_digest",
        "weight_eligibility_receipt_reference",
        "weight_eligibility_receipt_digest",
        "analytic_case_count",
        "constructed_at",
        "correction_sequence",
        "supersedes_receipt_digest",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "released_at",
    }
)


class _ReadPort:
    """Return configured released final-weight authority and capture lookup coordinates."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def read_final_analysis_weight_authority(self, **coordinates: object) -> object:
        self.calls.append(dict(coordinates))
        return self.result


class _ProtocolOnly(FinalAnalysisWeightAuthorityReadPort):
    """Inherit only the Protocol placeholder."""


class _DescriptorReadPort:
    """Expose a descriptor that must not execute."""

    @property
    def read_final_analysis_weight_authority(self) -> object:
        raise AssertionError("descriptor must not execute")


class _NoReadMethod:
    """Deliberately omit the owner capability."""


def _principal(*, tenant_record_id: UUID = TENANT) -> ValidationPrincipal:
    return ValidationPrincipal(
        tenant_record_id=tenant_record_id,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )


def _policy(*, purpose_code: str = "selection_validity_analysis") -> PurposeBoundAccessPolicy:
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="final-analysis-weight-authority-read-v1",
        resource_kind="final_analysis_weight_authority",
        purpose_code=purpose_code,
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def _adjustment(**overrides: object) -> FinalWeightAdjustmentCoordinate:
    values: dict[str, object] = {
        "sequence_number": 1,
        "adjustment_code": "nonresponse_adjustment",
        "method_reference": METHOD_REFERENCE,
        "method_version": 2,
        "input_weight_artifact_digest": BASE_ARTIFACT_DIGEST,
        "output_weight_artifact_digest": ADJUSTED_ARTIFACT_DIGEST,
        "configuration_digest": ADJUSTMENT_CONFIG_DIGEST,
        "evidence_receipt_digest": ADJUSTMENT_RECEIPT_DIGEST,
        "evidence_kind": "nonresponse_adjustment_receipt",
    }
    values.update(overrides)
    return FinalWeightAdjustmentCoordinate(**values)


def _record(**overrides: object) -> FinalAnalysisWeightAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "analysis_weight_receipt_reference": WEIGHT_RECEIPT_REFERENCE,
        "analysis_weight_receipt_digest": WEIGHT_RECEIPT_DIGEST,
        "evidence_version": 1,
        "estimand_reference": ESTIMAND_REFERENCE,
        "estimand_digest": ESTIMAND_DIGEST,
        "estimand_scope_code": "longitudinal",
        "target_population_reference": TARGET_REFERENCE,
        "target_population_digest": TARGET_DIGEST,
        "analysis_unit_code": "person_occurrence",
        "analysis_window_reference": WINDOW_REFERENCE,
        "reference_duration_reference": DURATION_REFERENCE,
        "reference_duration_digest": DURATION_DIGEST,
        "eligible_case_set_digest": ELIGIBLE_CASE_DIGEST,
        "analytic_case_occurrence_set_digest": ANALYTIC_CASE_DIGEST,
        "source_universe_receipt_reference": SOURCE_REFERENCE,
        "source_universe_receipt_version": 4,
        "source_universe_receipt_digest": SOURCE_DIGEST,
        "sampling_design_receipt_reference": SAMPLING_REFERENCE,
        "sampling_design_receipt_version": 3,
        "sampling_design_receipt_digest": SAMPLING_DIGEST,
        "base_weight_method_code": "inverse_inclusion_probability",
        "base_weight_method_version": 1,
        "base_weight_evidence_digest": BASE_EVIDENCE_DIGEST,
        "base_weight_artifact_digest": BASE_ARTIFACT_DIGEST,
        "adjustments": (_adjustment(),),
        "final_weight_artifact_digest": ADJUSTED_ARTIFACT_DIGEST,
        "weight_eligibility_receipt_reference": ELIGIBILITY_REFERENCE,
        "weight_eligibility_receipt_digest": ELIGIBILITY_DIGEST,
        "analytic_case_count": 1200,
        "constructed_at": CONSTRUCTED_AT,
        "correction_sequence": 1,
        "supersedes_receipt_digest": None,
        "owner_contract_reference": OWNER_REFERENCE,
        "owner_contract_version": 7,
        "owner_contract_digest": OWNER_DIGEST,
        "released_at": RELEASED_AT,
    }
    values.update(overrides)
    return FinalAnalysisWeightAuthorityRecord(**values)


def _resolve(*, read_port: object, **overrides: object) -> FinalAnalysisWeightAuthorityView:
    values = dict(_record().fields)
    values.update(
        {
            "principal": _principal(),
            "tenant_record_id": TENANT,
            "validity_study_id": STUDY,
            "used_at": USED_AT,
            "purpose_code": "selection_validity_analysis",
            "policy": _policy(),
            "read_port": read_port,
        }
    )
    values.update(overrides)
    return resolve_final_analysis_weight_authority(**values)


def test_resolution_binds_complete_estimand_source_base_adjustment_and_final_artifact() -> None:
    port = _ReadPort(_record())

    view = _resolve(read_port=port)

    assert isinstance(port, FinalAnalysisWeightAuthorityReadPort)
    assert len(port.calls) == 1
    assert port.calls[0]["source_universe_receipt_reference"] == SOURCE_REFERENCE
    assert port.calls[0]["sampling_design_receipt_version"] == 3
    assert view.tenant_record_id == TENANT
    assert view.validity_study_id == STUDY
    assert ("estimand_reference", ESTIMAND_REFERENCE) in view.fields
    assert ("source_universe_receipt_digest", SOURCE_DIGEST) in view.fields
    assert ("base_weight_evidence_digest", BASE_EVIDENCE_DIGEST) in view.fields
    assert ("final_weight_artifact_digest", ADJUSTED_ARTIFACT_DIGEST) in view.fields
    assert ("released_at", RELEASED_AT) in view.fields
    adjustment = dict(view.fields)["adjustments"][0]
    assert tuple(adjustment) == tuple(_adjustment())
    assert adjustment.sequence_number == 1
    assert adjustment.adjustment_code == "nonresponse_adjustment"
    assert adjustment.method_reference == METHOD_REFERENCE
    assert adjustment.method_version == 2
    assert adjustment.input_weight_artifact_digest == BASE_ARTIFACT_DIGEST
    assert adjustment.output_weight_artifact_digest == ADJUSTED_ARTIFACT_DIGEST
    assert adjustment.configuration_digest == ADJUSTMENT_CONFIG_DIGEST
    assert adjustment.evidence_receipt_digest == ADJUSTMENT_RECEIPT_DIGEST
    assert adjustment.evidence_kind == "nonresponse_adjustment_receipt"


def test_authorization_denial_happens_before_owner_resolution() -> None:
    port = _ReadPort(_record())
    with pytest.raises(AuthorizationDeniedError):
        _resolve(read_port=port, policy=_policy(purpose_code="audit_review"))
    assert port.calls == []


def test_missing_or_noncanonical_owner_evidence_fails_closed() -> None:
    with pytest.raises(FinalAnalysisWeightAuthorityNotFound):
        _resolve(read_port=_ReadPort(None))
    with pytest.raises(FinalAnalysisWeightAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(object()))


@pytest.mark.parametrize(
    "record_overrides",
    [
        {"tenant_record_id": OTHER_TENANT},
        {"validity_study_id": OTHER_STUDY},
        {"estimand_digest": "a" * 64},
        {"estimand_scope_code": "cross_sectional"},
        {"target_population_digest": "b" * 64},
        {"analysis_unit_code": "household"},
        {"analysis_window_reference": "analysis_window:other"},
        {"reference_duration_digest": "c" * 64},
        {"eligible_case_set_digest": "d" * 64},
        {"analytic_case_occurrence_set_digest": "e" * 64},
        {"source_universe_receipt_version": 5},
        {"source_universe_receipt_digest": "f" * 64},
        {"sampling_design_receipt_version": 4},
        {"sampling_design_receipt_digest": "0" * 64},
        {"base_weight_method_code": "equal_weight"},
        {"base_weight_method_version": 2},
        {"base_weight_evidence_digest": "a" * 64},
        {"weight_eligibility_receipt_digest": "b" * 64},
        {"analytic_case_count": 1199},
        {"constructed_at": CONSTRUCTED_AT + timedelta(seconds=1)},
        {"owner_contract_version": 8},
        {"owner_contract_digest": "c" * 64},
    ],
)
def test_owner_evidence_must_match_every_material_requested_coordinate(
    record_overrides: dict[str, object],
) -> None:
    with pytest.raises(FinalAnalysisWeightAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(**record_overrides)))


def test_chain_correction_and_release_chronology_fail_closed() -> None:
    with pytest.raises(ValueError):
        _record(adjustments=[])
    with pytest.raises(ValueError):
        _record(adjustments=(_adjustment(sequence_number=2),))
    with pytest.raises(ValueError):
        _record(adjustments=(_adjustment(input_weight_artifact_digest="0" * 64),))
    with pytest.raises(ValueError):
        _record(final_weight_artifact_digest="0" * 64)
    with pytest.raises(ValueError):
        _record(correction_sequence=1, supersedes_receipt_digest=SUPERSEDES_DIGEST)
    with pytest.raises(ValueError):
        _record(correction_sequence=2, supersedes_receipt_digest=None)
    with pytest.raises(ValueError):
        _record(correction_sequence=2, supersedes_receipt_digest=WEIGHT_RECEIPT_DIGEST)
    corrected = _record(correction_sequence=2, supersedes_receipt_digest=SUPERSEDES_DIGEST)
    assert ("correction_sequence", 2) in corrected.fields
    with pytest.raises(ValueError):
        _record(released_at=CONSTRUCTED_AT - timedelta(seconds=1))
    with pytest.raises(FinalAnalysisWeightAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(released_at=USED_AT + timedelta(seconds=1))))


def test_adjustment_semantics_are_typed_and_no_op_transform_is_rejected() -> None:
    with pytest.raises(ValueError):
        _adjustment(evidence_kind="generic_weight_evidence")
    with pytest.raises(ValueError):
        _adjustment(output_weight_artifact_digest=BASE_ARTIFACT_DIGEST)
    generic = _adjustment(
        adjustment_code="custom_transform",
        evidence_kind="custom_transform_receipt",
    )
    assert generic.evidence_kind == "custom_transform_receipt"


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
        ("analysis_weight_receipt_reference", "wrong:receipt", ValueError),
        ("analysis_weight_receipt_digest", "ABC", ValueError),
        ("evidence_version", False, ValueError),
        ("estimand_reference", "wrong:estimand", ValueError),
        ("estimand_digest", "2" * 63, ValueError),
        ("estimand_scope_code", "panel", ValueError),
        ("target_population_reference", "wrong:population", ValueError),
        ("target_population_digest", "3" * 63, ValueError),
        ("analysis_unit_code", "Person Occurrence", ValueError),
        ("analysis_window_reference", "wrong:window", ValueError),
        ("reference_duration_reference", "wrong:duration", ValueError),
        ("reference_duration_digest", "4" * 63, ValueError),
        ("eligible_case_set_digest", "5" * 63, ValueError),
        ("analytic_case_occurrence_set_digest", "6" * 63, ValueError),
        ("source_universe_receipt_reference", "wrong:source", ValueError),
        ("source_universe_receipt_version", 0, ValueError),
        ("source_universe_receipt_digest", "7" * 63, ValueError),
        ("sampling_design_receipt_reference", "wrong:sampling", ValueError),
        ("sampling_design_receipt_version", 0, ValueError),
        ("sampling_design_receipt_digest", "8" * 63, ValueError),
        ("base_weight_method_code", "Inverse Probability", ValueError),
        ("base_weight_method_version", False, ValueError),
        ("base_weight_evidence_digest", "9" * 63, ValueError),
        ("base_weight_artifact_digest", "a" * 63, ValueError),
        ("adjustments", (_adjustment(), object()), ValueError),
        ("final_weight_artifact_digest", "b" * 63, ValueError),
        ("weight_eligibility_receipt_reference", "wrong:eligibility", ValueError),
        ("weight_eligibility_receipt_digest", "e" * 63, ValueError),
        ("analytic_case_count", 0, ValueError),
        ("constructed_at", datetime(2026, 9, 17, 8, 0), ValueError),
        ("correction_sequence", False, ValueError),
        ("owner_contract_reference", "wrong:contract", ValueError),
        ("owner_contract_version", 0, ValueError),
        ("owner_contract_digest", "f" * 63, ValueError),
        ("used_at", datetime(2026, 9, 17, 9, 0), ValueError),
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


def test_record_adjustment_and_view_are_structurally_immutable() -> None:
    adjustment = _adjustment()
    with pytest.raises(AttributeError):
        object.__setattr__(adjustment, "sequence_number", 2)

    tenant = UUID(str(TENANT))
    record = _record(tenant_record_id=tenant)
    object.__setattr__(tenant, "int", OTHER_TENANT.int)
    assert record.tenant_record_id == TENANT
    assert record.validity_study_id == STUDY
    assert record.released_at == RELEASED_AT
    with pytest.raises(AttributeError):
        object.__setattr__(record, "fields", ())

    view = _resolve(read_port=_ReadPort(record))
    returned_tenant = view.tenant_record_id
    object.__setattr__(returned_tenant, "int", OTHER_TENANT.int)
    assert view.tenant_record_id == TENANT
    with pytest.raises(AttributeError):
        object.__setattr__(view, "fields", ())
    with pytest.raises(TypeError):
        FinalAnalysisWeightAuthorityView(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            fields=(),
        )
