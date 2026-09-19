"""Field-minimized authorization for final-weight component evidence reads."""

from __future__ import annotations

from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api.final_weight_component_evidence_resolution import (
    BaseWeightComponentEvidence,
    corroborate_final_weight_component_evidence,
)
from test_final_weight_component_evidence_resolution import (
    BASE_ARTIFACT_DIGEST,
    TENANT,
    USED_AT,
    _ReadPort,
    _base_evidence,
    _binding,
    _final_weight,
    _principal,
)

BASE_ONLY_READ_FIELDS = frozenset(
    {
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


class _BaseOnlyReadPort:
    def __init__(self) -> None:
        self.base_calls: list[dict[str, object]] = []

    def read_base_weight_component_evidence(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        receipt_reference: str,
        receipt_digest: str,
        evidence_version: int,
    ) -> BaseWeightComponentEvidence | None:
        self.base_calls.append(
            {
                "tenant_record_id": tenant_record_id,
                "validity_study_id": validity_study_id,
                "receipt_reference": receipt_reference,
                "receipt_digest": receipt_digest,
                "evidence_version": evidence_version,
            }
        )
        return _base_evidence()


def _base_only_policy() -> PurposeBoundAccessPolicy:
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="final-weight-component-evidence-resolution-base-only-v1",
        resource_kind="final_weight_component_evidence_resolution",
        purpose_code="selection_validity_analysis",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=BASE_ONLY_READ_FIELDS,
    )


def _corroborate_base_only(*, read_port: object):
    return corroborate_final_weight_component_evidence(
        principal=_principal(),
        final_weight=_final_weight(
            adjustments=(),
            final_weight_artifact_digest=BASE_ARTIFACT_DIGEST,
        ),
        binding=_binding(adjustment_bindings=()),
        used_at=USED_AT,
        purpose_code="selection_validity_analysis",
        policy=_base_only_policy(),
        read_port=read_port,
    )


def test_base_only_resolution_does_not_request_adjustment_only_policy_fields() -> None:
    """Authorize exactly the fields read when no specialized adjustment owner is consulted."""
    port = _ReadPort()

    resolution = _corroborate_base_only(read_port=port)

    assert resolution.adjustments == ()
    assert len(port.base_calls) == 1
    assert port.adjustment_calls == []


def test_base_only_resolution_does_not_require_unused_adjustment_capability() -> None:
    """Accept a base-only port when the final-weight lineage cannot invoke an adjustment owner."""
    port = _BaseOnlyReadPort()

    resolution = _corroborate_base_only(read_port=port)

    assert resolution.adjustments == ()
    assert len(port.base_calls) == 1
