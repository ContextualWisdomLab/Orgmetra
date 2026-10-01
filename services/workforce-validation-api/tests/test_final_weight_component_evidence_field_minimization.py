"""Field-minimized authorization for final-weight component evidence reads."""

from __future__ import annotations

import pytest

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api.final_weight_component_evidence_resolution import (
    corroborate_final_weight_component_evidence,
)
from test_final_weight_component_evidence_resolution import (
    BASE_ARTIFACT_DIGEST,
    TENANT,
    USED_AT,
    _ReadPort,
    _binding,
    _final_weight,
    _principal,
)

OWNER_PROVENANCE_READ_FIELDS = frozenset(
    {
        "tenant_record_id",
        "validity_study_id",
        "analysis_weight_receipt_reference",
        "analysis_weight_receipt_digest",
        "analysis_weight_evidence_version",
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
        "binding_reference",
        "binding_digest",
        "binding_version",
        "base_weight_evidence_receipt_reference",
        "base_weight_evidence_receipt_digest",
        "base_weight_evidence_version",
        "adjustment_bindings",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
    }
)
BASE_COMPONENT_READ_FIELDS = frozenset(
    {
        "tenant_record_id",
        "validity_study_id",
        "receipt_reference",
        "receipt_digest",
        "evidence_version",
        "method_code",
        "method_version",
        "output_weight_artifact_digest",
        "released_at",
        "superseded_at",
    }
)
BASE_ONLY_READ_FIELDS = OWNER_PROVENANCE_READ_FIELDS | BASE_COMPONENT_READ_FIELDS


def _base_only_policy(*, permitted_fields: frozenset[str]) -> PurposeBoundAccessPolicy:
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="final-weight-component-evidence-resolution-base-only-v1",
        resource_kind="final_weight_component_evidence_resolution",
        purpose_code="selection_validity_analysis",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=permitted_fields,
    )


def _corroborate_base_only(*, policy: PurposeBoundAccessPolicy, port: _ReadPort):
    final_record = _final_weight(
        adjustments=(),
        final_weight_artifact_digest=BASE_ARTIFACT_DIGEST,
    )
    binding_record = _binding(adjustment_bindings=())
    port.final_owner = final_record
    port.binding_owner = binding_record
    return corroborate_final_weight_component_evidence(
        principal=_principal(),
        final_weight=final_record,
        binding=binding_record,
        used_at=USED_AT,
        purpose_code="selection_validity_analysis",
        policy=policy,
        read_port=port,
    )


def test_base_only_resolution_does_not_request_adjustment_only_policy_fields() -> None:
    """Authorize owner provenance plus base projection fields when no adjustment owner is read."""
    port = _ReadPort()

    resolution = _corroborate_base_only(
        policy=_base_only_policy(permitted_fields=BASE_ONLY_READ_FIELDS),
        port=port,
    )

    assert resolution.adjustments == ()
    assert len(port.final_owner_calls) == 1
    assert len(port.binding_owner_calls) == 1
    assert len(port.base_calls) == 1
    assert port.adjustment_calls == []


def test_component_only_policy_cannot_authorize_owner_provenance_reads() -> None:
    """Deny before all owner access when final/binding provenance fields are not permitted."""
    port = _ReadPort()

    with pytest.raises(AuthorizationDeniedError):
        _corroborate_base_only(
            policy=_base_only_policy(permitted_fields=BASE_COMPONENT_READ_FIELDS),
            port=port,
        )

    assert port.final_owner_calls == []
    assert port.binding_owner_calls == []
    assert port.base_calls == []
    assert port.adjustment_calls == []


@pytest.mark.parametrize("omitted_scope_field", ["tenant_record_id", "validity_study_id"])
def test_base_only_resolution_authorizes_native_owner_scope_fields_before_read(
    omitted_scope_field: str,
) -> None:
    """Deny before owner access when policy omits a scope field consumed from the projection."""
    port = _ReadPort()
    permitted_fields = BASE_ONLY_READ_FIELDS - {omitted_scope_field}

    with pytest.raises(AuthorizationDeniedError):
        _corroborate_base_only(
            policy=_base_only_policy(permitted_fields=permitted_fields),
            port=port,
        )

    assert port.final_owner_calls == []
    assert port.binding_owner_calls == []
    assert port.base_calls == []
    assert port.adjustment_calls == []
