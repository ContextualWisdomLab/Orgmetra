"""Reject retroactive owner contracts and stale weight/variance compatibility use."""

from __future__ import annotations

from datetime import datetime, timezone
from inspect import signature
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.variance_authority import (
    WeightVarianceAuthorityIntegrityError,
    WeightVarianceAuthorityRecord,
    resolve_weight_variance_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
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
FINAL_WEIGHT_DIGEST = "6" * 64
VARIANCE_DIGEST = "7" * 64
OWNER_DIGEST = "8" * 64
OWNER_RELEASED_AT = datetime(2026, 9, 17, 0, 30, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 1, 0, tzinfo=timezone.utc)
SUPERSEDED_AT = datetime(2026, 9, 17, 3, 0, tzinfo=timezone.utc)
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
    def __init__(self, record: WeightVarianceAuthorityRecord) -> None:
        self.record = record

    def read_weight_variance_authority(self, **_: object) -> WeightVarianceAuthorityRecord:
        return self.record


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
        "weight_correction_sequence": 9,
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
        "superseded_at": SUPERSEDED_AT,
    }
    values.update(overrides)
    return WeightVarianceAuthorityRecord(**values)


def _resolve(*, used_at: datetime) -> object:
    return resolve_weight_variance_authority(
        principal=ValidationPrincipal(
            tenant_record_id=TENANT,
            actor_reference="person:validation-analyst-1",
            granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
        ),
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        sampling_receipt_reference=SAMPLING_REFERENCE,
        sampling_receipt_version=3,
        sampling_receipt_digest=SAMPLING_DIGEST,
        analysis_weight_receipt_digest=ANALYSIS_WEIGHT_DIGEST,
        analytic_case_occurrence_set_digest=CASE_SET_DIGEST,
        weight_eligibility_receipt_digest=ELIGIBILITY_DIGEST,
        weight_correction_sequence=9,
        final_weight_artifact_digest=FINAL_WEIGHT_DIGEST,
        variance_design_receipt_reference=VARIANCE_REFERENCE,
        variance_design_receipt_version=5,
        variance_design_receipt_digest=VARIANCE_DIGEST,
        variance_method_reference=METHOD_REFERENCE,
        variance_method_version=2,
        variance_evidence_mode="replicate_weights",
        variance_semantics="exact",
        owner_contract_reference=OWNER_REFERENCE,
        owner_contract_version=4,
        used_at=used_at,
        purpose_code="selection_validity_analysis",
        policy=PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="weight-variance-authority-read-v2",
            resource_kind="weight_variance_authority",
            purpose_code="selection_validity_analysis",
            operation_code="read",
            required_scope_code="orgmetra.workforce_validation.read",
            permitted_fields=READ_FIELDS,
        ),
        read_port=_ReadPort(_record()),
    )


def test_chronology_is_owner_evidence_not_caller_input() -> None:
    parameters = signature(resolve_weight_variance_authority).parameters
    assert "owner_contract_released_at" not in parameters
    assert "superseded_at" not in parameters


def test_owner_contract_cannot_retroactively_authorize_compatibility() -> None:
    with pytest.raises(ValueError, match="owner contract"):
        _record(
            owner_contract_released_at=datetime(
                2026, 9, 17, 1, 1, tzinfo=timezone.utc
            )
        )


def test_compatibility_uses_owner_resolved_half_open_authority_interval() -> None:
    historical = _resolve(used_at=datetime(2026, 9, 17, 2, 59, tzinfo=timezone.utc))
    fields = dict(historical.fields)
    assert fields["owner_contract_released_at"] == OWNER_RELEASED_AT
    assert fields["superseded_at"] == SUPERSEDED_AT

    with pytest.raises(WeightVarianceAuthorityIntegrityError, match="supersession"):
        _resolve(used_at=SUPERSEDED_AT)
