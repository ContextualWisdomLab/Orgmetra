"""Authoritative owner provenance for final-weight component corroboration."""

from __future__ import annotations

import pytest

from orgmetra_workforce_validation_api.final_weight_component_evidence_resolution import (
    FinalWeightComponentEvidenceIntegrityError,
    FinalWeightComponentEvidenceNotFound,
    corroborate_final_weight_component_evidence,
)
from test_final_weight_component_evidence_resolution import (
    USED_AT,
    _ReadPort,
    _binding,
    _final_weight,
    _policy,
    _principal,
)


class _OwnerProvenanceReadPort(_ReadPort):
    """Expose independent final-weight and binding owner reads before component reads."""

    def __init__(self, *, final_owner: object, binding_owner: object) -> None:
        super().__init__()
        self.final_owner = final_owner
        self.binding_owner = binding_owner
        self.final_owner_calls: list[dict[str, object]] = []
        self.binding_owner_calls: list[dict[str, object]] = []

    def read_final_analysis_weight_authority(self, **kwargs: object):
        """Return owner-confirmed final-weight authority or an explicit miss."""
        self.final_owner_calls.append(dict(kwargs))
        return self.final_owner

    def read_final_weight_component_binding_authority(self, **kwargs: object):
        """Return owner-confirmed component-binding authority or an explicit miss."""
        self.binding_owner_calls.append(dict(kwargs))
        return self.binding_owner


def _corroborate_with(port: _OwnerProvenanceReadPort) -> None:
    corroborate_final_weight_component_evidence(
        principal=_principal(),
        final_weight=_final_weight(),
        binding=_binding(),
        used_at=USED_AT,
        purpose_code="selection_validity_analysis",
        policy=_policy(),
        read_port=port,
    )


def test_missing_final_weight_owner_authority_stops_before_component_reads() -> None:
    """Canonical caller records cannot substitute for released final-weight owner truth."""
    port = _OwnerProvenanceReadPort(final_owner=None, binding_owner=_binding())

    with pytest.raises(FinalWeightComponentEvidenceNotFound, match="final-weight"):
        _corroborate_with(port)

    assert len(port.final_owner_calls) == 1
    assert port.binding_owner_calls == []
    assert port.base_calls == []
    assert port.adjustment_calls == []


def test_conflicting_binding_owner_authority_stops_before_component_reads() -> None:
    """A locally canonical binding must exactly match the native owner record."""
    conflicting_binding = _binding(binding_digest="b" * 64)
    port = _OwnerProvenanceReadPort(
        final_owner=_final_weight(),
        binding_owner=conflicting_binding,
    )

    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="binding owner"):
        _corroborate_with(port)

    assert len(port.final_owner_calls) == 1
    assert len(port.binding_owner_calls) == 1
    assert port.base_calls == []
    assert port.adjustment_calls == []
