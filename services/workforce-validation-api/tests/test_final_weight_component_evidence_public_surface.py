"""Public package contract for deterministic final-weight component corroboration."""

from __future__ import annotations

import orgmetra_workforce_validation_api as api


def test_component_evidence_resolution_is_public_package_surface() -> None:
    expected = {
        "AdjustmentComponentEvidence",
        "BaseWeightComponentEvidence",
        "FinalWeightComponentEvidenceIntegrityError",
        "FinalWeightComponentEvidenceNotFound",
        "FinalWeightComponentEvidenceReadPort",
        "FinalWeightComponentEvidenceResolution",
        "corroborate_final_weight_component_evidence",
    }

    assert expected <= set(api.__all__)
    for name in expected:
        assert getattr(api, name).__module__ == (
            "orgmetra_workforce_validation_api.final_weight_component_evidence_resolution"
        )
