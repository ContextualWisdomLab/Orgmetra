"""Hostile edge coverage for final-weight component evidence resolution."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

import pytest

import orgmetra_workforce_validation_api.final_weight_component_evidence_resolution as resolution_module
from orgmetra_workforce_validation_api.final_weight_authority import (
    FinalAnalysisWeightAuthorityRecord,
)
from orgmetra_workforce_validation_api.final_weight_component_binding_authority import (
    FinalWeightAdjustmentEvidenceBinding,
    FinalWeightComponentBindingAuthorityRecord,
)
from orgmetra_workforce_validation_api.final_weight_component_evidence_resolution import (
    AdjustmentComponentEvidence,
    BaseWeightComponentEvidence,
    FinalWeightComponentEvidenceIntegrityError,
    FinalWeightComponentEvidenceNotFound,
    corroborate_final_weight_component_evidence,
)
from test_final_weight_component_evidence_resolution import (
    ADJUSTMENT_RECEIPT_REFERENCE,
    BASE_ARTIFACT_DIGEST,
    BINDING_RELEASED_AT,
    CONSTRUCTED_AT,
    FINAL_RELEASED_AT,
    OTHER_TENANT,
    TENANT,
    USED_AT,
    _ReadPort,
    _adjustment_evidence,
    _base_evidence,
    _binding,
    _corroborate,
    _final_weight,
    _policy,
    _principal,
)


def _call_without_owner_rebinding(port: _ReadPort) -> object:
    """Invoke corroboration while preserving independently configured owner results."""
    return corroborate_final_weight_component_evidence(
        principal=_principal(),
        final_weight=_final_weight(),
        binding=_binding(),
        used_at=USED_AT,
        purpose_code="selection_validity_analysis",
        policy=_policy(),
        read_port=port,
    )


def test_component_value_objects_reject_invalid_versions_transforms_and_cutovers() -> None:
    """Keep component schema, transform, and half-open chronology fail-closed."""
    with pytest.raises(ValueError, match="evidence_version"):
        _base_evidence(evidence_version=2)
    with pytest.raises(ValueError, match="superseded_at"):
        _base_evidence(superseded_at=CONSTRUCTED_AT - timedelta(minutes=15))
    with pytest.raises(ValueError, match="governed specialized"):
        _adjustment_evidence(evidence_kind="unknown_receipt")
    with pytest.raises(ValueError, match="evidence_version"):
        _adjustment_evidence(evidence_version=2)
    with pytest.raises(ValueError, match="transformed"):
        _adjustment_evidence(output_weight_artifact_digest=BASE_ARTIFACT_DIGEST)
    with pytest.raises(ValueError, match="superseded_at"):
        _adjustment_evidence(superseded_at=CONSTRUCTED_AT - timedelta(minutes=1))


def test_canonicalizers_reject_wrong_malformed_and_hidden_record_shapes() -> None:
    """Require exact reconstructible runtime types for every cross-owner record."""
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="base-weight"):
        resolution_module._canonical_base_evidence(object())
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="final_weight must"):
        resolution_module._canonical_final_weight(object())
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="binding must"):
        resolution_module._canonical_binding(object())

    final_weight = _final_weight()
    malformed_final = tuple.__new__(
        FinalAnalysisWeightAuthorityRecord,
        tuple(final_weight)[:-1],
    )
    hidden_final = tuple.__new__(
        FinalAnalysisWeightAuthorityRecord,
        tuple(final_weight) + ("hidden-final-coordinate",),
    )
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="malformed"):
        resolution_module._canonical_final_weight(malformed_final)
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="hidden"):
        resolution_module._canonical_final_weight(hidden_final)

    binding = _binding()
    malformed_binding = tuple.__new__(
        FinalWeightComponentBindingAuthorityRecord,
        tuple(binding)[:-1],
    )
    hidden_binding = tuple.__new__(
        FinalWeightComponentBindingAuthorityRecord,
        tuple(binding) + ("hidden-binding-coordinate",),
    )
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="malformed"):
        resolution_module._canonical_binding(malformed_binding)
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="hidden"):
        resolution_module._canonical_binding(hidden_binding)


def _unused_read(*_args: object, **_kwargs: object) -> None:
    """Fail if an incomplete port reaches any owner read."""
    raise AssertionError("incomplete port must fail before owner access")


@pytest.mark.parametrize(
    "missing_method",
    [
        "read_final_analysis_weight_authority",
        "read_final_weight_component_binding_authority",
        "read_base_weight_component_evidence",
        "read_adjustment_component_evidence",
    ],
)
def test_every_owner_read_capability_is_required_before_resolution(
    missing_method: str,
) -> None:
    """Reject a port missing any one of the four static owner capabilities."""
    methods = {
        "read_final_analysis_weight_authority": _unused_read,
        "read_final_weight_component_binding_authority": _unused_read,
        "read_base_weight_component_evidence": _unused_read,
        "read_adjustment_component_evidence": _unused_read,
    }
    del methods[missing_method]
    incomplete_port = type("IncompleteComponentReadPort", (), methods)()

    with pytest.raises(TypeError, match=missing_method):
        _corroborate(read_port=incomplete_port)


def test_final_binding_scope_chronology_and_currentness_fail_closed() -> None:
    """Reject cross-receipt, unreleased, or superseded final/binding evidence."""
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="different"):
        _corroborate(
            read_port=_ReadPort(),
            binding=_binding(analysis_weight_receipt_digest="9" * 64),
        )
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="released before use"):
        _corroborate(
            read_port=_ReadPort(),
            used_at=FINAL_RELEASED_AT - timedelta(microseconds=1),
        )
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="final-weight evidence"):
        _corroborate(
            read_port=_ReadPort(),
            final_weight=_final_weight(superseded_at=USED_AT),
        )
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="binding is not current"):
        _corroborate(
            read_port=_ReadPort(),
            binding=_binding(superseded_at=USED_AT),
        )


def test_owner_final_binding_and_base_failures_stop_resolution() -> None:
    """Require owner-confirmed final, binding, and base evidence before resolution."""
    port = _ReadPort()
    port.final_owner = _final_weight(analytic_case_count=11)
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="final-weight owner"):
        _call_without_owner_rebinding(port)

    port = _ReadPort()
    port.binding_owner = None
    with pytest.raises(FinalWeightComponentEvidenceNotFound, match="binding"):
        _call_without_owner_rebinding(port)

    port = _ReadPort()
    port.base = None
    with pytest.raises(FinalWeightComponentEvidenceNotFound):
        _call_without_owner_rebinding(port)

    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="base-weight component"):
        _corroborate(
            read_port=_ReadPort(base=_base_evidence(method_version=2)),
        )


def test_component_superseded_by_construction_fails_closed() -> None:
    """Reject a component whose authority ended at final-weight construction."""
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="construction"):
        _corroborate(
            read_port=_ReadPort(
                base=_base_evidence(superseded_at=CONSTRUCTED_AT),
            )
        )


def test_adjustment_locator_and_component_identity_must_match() -> None:
    """Bind each specialized coordinate to its exact locator and owner projection."""
    mismatched_binding = _binding(
        adjustment_bindings=(
            FinalWeightAdjustmentEvidenceBinding(
                sequence_number=1,
                evidence_kind="trimming_bounding_adjustment_receipt",
                evidence_receipt_reference=ADJUSTMENT_RECEIPT_REFERENCE.replace(
                    "nonresponse_adjustment_receipt",
                    "trimming_bounding_adjustment_receipt",
                ),
                evidence_version=1,
                evidence_receipt_digest="4" * 64,
            ),
        )
    )
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="digest or evidence kind"):
        _corroborate(read_port=_ReadPort(), binding=mismatched_binding)

    port = _ReadPort(
        adjustment=_adjustment_evidence(
            receipt_reference=(
                "nonresponse_adjustment_receipt:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
            )
        )
    )
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="exact binding locator"):
        _corroborate(read_port=port)


def test_adjustment_and_base_wrong_runtime_types_fail_closed() -> None:
    """Reject non-canonical component objects before reading their structure."""
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="specialized"):
        resolution_module._canonical_adjustment_evidence(object())
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="base-weight"):
        resolution_module._canonical_base_evidence(object())


def test_owner_provenance_rejects_cross_tenant_component() -> None:
    """Retain tenant provenance before any component semantics are trusted."""
    port = _ReadPort(base=_base_evidence(tenant_record_id=OTHER_TENANT))
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="tenant"):
        _corroborate(read_port=port)


def _authority_view(record: object, **field_overrides: object) -> SimpleNamespace:
    """Expose a detached authority view for post-canonicalization defense tests."""
    fields = dict(record.fields)
    fields.update(field_overrides)
    return SimpleNamespace(
        tenant_record_id=record.tenant_record_id,
        validity_study_id=record.validity_study_id,
        owner_contract_released_at=record.owner_contract_released_at,
        released_at=record.released_at,
        superseded_at=record.superseded_at,
        fields=fields,
    )


@pytest.mark.parametrize(
    ("target", "message"),
    [
        ("final", "final-weight adjustments"),
        ("binding", "component adjustment bindings"),
    ],
)
def test_post_canonicalization_collections_remain_immutable(
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    message: str,
) -> None:
    """Retain fail-closed collection checks even if a canonicalizer regresses."""
    final_weight = _final_weight()
    binding = _binding()
    if target == "final":
        final_view = _authority_view(
            final_weight,
            adjustments=list(dict(final_weight.fields)["adjustments"]),
        )
        monkeypatch.setattr(resolution_module, "_canonical_final_weight", lambda _value: final_view)
    else:
        binding_view = _authority_view(
            binding,
            adjustment_bindings=list(dict(binding.fields)["adjustment_bindings"]),
        )
        monkeypatch.setattr(resolution_module, "_canonical_binding", lambda _value: binding_view)

    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match=message):
        _corroborate(
            read_port=_ReadPort(),
            final_weight=final_weight,
            binding=binding,
        )


def test_post_canonicalization_adjustment_coordinate_type_remains_exact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject a structurally similar adjustment if canonical reconstruction regresses."""
    final_weight = _final_weight()
    forged_adjustment = SimpleNamespace(
        sequence_number=1,
        evidence_kind="nonresponse_adjustment_receipt",
    )
    final_view = _authority_view(final_weight, adjustments=(forged_adjustment,))
    monkeypatch.setattr(resolution_module, "_canonical_final_weight", lambda _value: final_view)

    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="coordinates"):
        _corroborate(read_port=_ReadPort(), final_weight=final_weight)
