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

BASE_ONLY_READ_FIELDS = frozenset(
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
    return corroborate_final_weight_component_evidence(
        principal=_principal(),
        final_weight=_final_weight(
            adjustments=(),
            final_weight_artifact_digest=BASE_ARTIFACT_DIGEST,
        ),
        binding=_binding(adjustment_bindings=()),
        used_at=USED_AT,
        purpose_code="selection_validity_analysis",
        policy=policy,
        read_port=port,
    )


def test_base_only_resolution_does_not_request_adjustment_only_policy_fields() -> None:
    """Authorize exactly the base projection fields when no adjustment owner is consulted."""
    port = _ReadPort()

    resolution = _corroborate_base_only(
        policy=_base_only_policy(permitted_fields=BASE_ONLY_READ_FIELDS),
        port=port,
    )

    assert resolution.adjustments == ()
    assert len(port.base_calls) == 1
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

    assert port.base_calls == []
    assert port.adjustment_calls == []
