"""Purpose-bound authorization for final-weight component owner reads."""

from __future__ import annotations

from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.final_weight_component_evidence_resolution import (
    corroborate_final_weight_component_evidence,
)
from test_final_weight_component_evidence_resolution import (
    STUDY,
    TENANT,
    USED_AT,
    _ReadPort,
    _binding,
    _final_weight,
)

READ_FIELDS = frozenset(
    {
        "receipt_reference",
        "receipt_digest",
        "evidence_version",
        "method_code",
        "method_reference",
        "method_version",
        "input_weight_artifact_digest",
        "output_weight_artifact_digest",
        "configuration_digest",
        "evidence_kind",
        "released_at",
        "superseded_at",
    }
)


def _principal(*, tenant_record_id: UUID = TENANT) -> ValidationPrincipal:
    return ValidationPrincipal(
        tenant_record_id=tenant_record_id,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )


def _policy(*, purpose_code: str = "selection_validity_analysis") -> PurposeBoundAccessPolicy:
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="final-weight-component-evidence-resolution-read-v1",
        resource_kind="final_weight_component_evidence_resolution",
        purpose_code=purpose_code,
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def test_denied_purpose_stops_before_any_component_owner_read() -> None:
    """Reject a purpose mismatch before the base or adjustment port is invoked."""
    port = _ReadPort()

    with pytest.raises(AuthorizationDeniedError):
        corroborate_final_weight_component_evidence(
            principal=_principal(),
            final_weight=_final_weight(),
            binding=_binding(),
            used_at=USED_AT,
            purpose_code="compensation_administration",
            policy=_policy(),
            read_port=port,
        )

    assert port.base_calls == []
    assert port.adjustment_calls == []


def test_cross_tenant_principal_stops_before_any_component_owner_read() -> None:
    """Reject an actor from another tenant before component evidence is exposed."""
    port = _ReadPort()

    with pytest.raises(AuthorizationDeniedError):
        corroborate_final_weight_component_evidence(
            principal=_principal(
                tenant_record_id=UUID("10000000-0000-7000-8000-000000000002")
            ),
            final_weight=_final_weight(),
            binding=_binding(),
            used_at=USED_AT,
            purpose_code="selection_validity_analysis",
            policy=_policy(),
            read_port=port,
        )

    assert port.base_calls == []
    assert port.adjustment_calls == []
