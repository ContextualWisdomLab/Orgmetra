"""Fail-closed owner contract for point-weight/variance evidence compatibility."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.variance_authority import (
    WeightVarianceAuthorityIntegrityError,
    WeightVarianceAuthorityNotFound,
    WeightVarianceAuthorityReadPort,
    WeightVarianceAuthorityRecord,
    WeightVarianceAuthorityView,
    resolve_weight_variance_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000002")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
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


class _ReadPort:
    """Return one configured owner record and retain the exact lookup coordinates."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[tuple[object, ...]] = []

    def read_weight_variance_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        sampling_receipt_reference: str,
        sampling_receipt_version: int,
        sampling_receipt_digest: str,
        analysis_weight_receipt_digest: str,
        variance_design_receipt_reference: str,
        variance_design_receipt_version: int,
        variance_design_receipt_digest: str,
        owner_contract_reference: str,
        owner_contract_version: int,
    ) -> object:
        """Capture the owner lookup and return the configured result."""
        self.calls.append(
            (
                tenant_record_id,
                validity_study_id,
                sampling_receipt_reference,
                sampling_receipt_version,
                sampling_receipt_digest,
                analysis_weight_receipt_digest,
                variance_design_receipt_reference,
                variance_design_receipt_version,
                variance_design_receipt_digest,
                owner_contract_reference,
                owner_contract_version,
            )
        )
        return self.result


class _ProtocolOnly(WeightVarianceAuthorityReadPort):
    """Inherit only the Protocol placeholder, not a concrete owner capability."""


def _principal() -> ValidationPrincipal:
    return ValidationPrincipal(
        tenant_record_id=TENANT,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )


def _policy(*, purpose_code: str = "selection_validity_analysis") -> PurposeBoundAccessPolicy:
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="weight-variance-authority-read-v2",
        resource_kind="weight_variance_authority",
        purpose_code=purpose_code,
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


def _resolve(*, read_port: object, **overrides: object) -> WeightVarianceAuthorityView:
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
        "read_port": read_port,
    }
    values.update(overrides)
    return resolve_weight_variance_authority(**values)


def test_resolution_authorizes_then_returns_owner_corroborated_compatibility() -> None:
    port = _ReadPort(_record())

    view = _resolve(read_port=port)

    assert isinstance(port, WeightVarianceAuthorityReadPort)
    assert port.calls == [
        (
            TENANT,
            STUDY,
            SAMPLING_REFERENCE,
            3,
            SAMPLING_DIGEST,
            ANALYSIS_WEIGHT_DIGEST,
            VARIANCE_REFERENCE,
            5,
            VARIANCE_DIGEST,
            OWNER_REFERENCE,
            4,
        )
    ]
    assert view.tenant_record_id == TENANT
    assert view.validity_study_id == STUDY
    fields = dict(view.fields)
    assert fields["final_weight_artifact_digest"] == FINAL_WEIGHT_DIGEST
    assert fields["weight_correction_sequence"] == CORRECTION_SEQUENCE
    assert fields["variance_design_receipt_digest"] == VARIANCE_DIGEST
    assert fields["owner_contract_digest"] == OWNER_DIGEST
    assert fields["owner_contract_released_at"] == OWNER_RELEASED_AT
    assert fields["released_at"] == RELEASED_AT
    assert fields["superseded_at"] is None


def test_authorization_denial_happens_before_owner_resolution() -> None:
    port = _ReadPort(_record())

    with pytest.raises(AuthorizationDeniedError):
        _resolve(read_port=port, policy=_policy(purpose_code="audit_review"))

    assert port.calls == []


def test_missing_noncanonical_or_mismatched_owner_evidence_fails_closed() -> None:
    with pytest.raises(WeightVarianceAuthorityNotFound):
        _resolve(read_port=_ReadPort(None))
    with pytest.raises(WeightVarianceAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(object()))
    with pytest.raises(WeightVarianceAuthorityIntegrityError):
        _resolve(
            read_port=_ReadPort(
                _record(analytic_case_occurrence_set_digest="a" * 64)
            )
        )
    with pytest.raises(WeightVarianceAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(final_weight_artifact_digest="b" * 64)))


def test_point_and_variance_receipts_must_be_distinct() -> None:
    with pytest.raises(ValueError):
        _record(variance_design_receipt_digest=ANALYSIS_WEIGHT_DIGEST)
    with pytest.raises(ValueError):
        _resolve(
            read_port=_ReadPort(_record()),
            variance_design_receipt_digest=ANALYSIS_WEIGHT_DIGEST,
        )


def test_approximation_mode_cannot_claim_exact_variance_semantics() -> None:
    with pytest.raises(ValueError):
        _record(variance_evidence_mode="approximation", variance_semantics="exact")


def test_invalid_dependency_and_pre_release_use_fail_closed() -> None:
    with pytest.raises(TypeError):
        _resolve(read_port=_ProtocolOnly())

    port = _ReadPort(_record())
    with pytest.raises(WeightVarianceAuthorityIntegrityError):
        _resolve(read_port=port, used_at=datetime(2026, 9, 17, 0, 59, tzinfo=timezone.utc))
    assert len(port.calls) == 1


def test_record_and_view_are_immutable_and_public_view_construction_is_blocked() -> None:
    record = _record()
    with pytest.raises(AttributeError):
        object.__setattr__(record, "variance_method_version", 999)

    view = _resolve(read_port=_ReadPort(record))
    with pytest.raises(AttributeError):
        object.__setattr__(view, "fields", ())
    with pytest.raises(TypeError):
        WeightVarianceAuthorityView(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            fields=(),
        )


def test_cross_tenant_owner_evidence_is_rejected() -> None:
    with pytest.raises(WeightVarianceAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(tenant_record_id=OTHER_TENANT)))
