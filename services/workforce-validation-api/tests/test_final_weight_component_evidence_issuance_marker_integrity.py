"""Hostile issuance-marker and private-issuer edge cases for component evidence."""

from __future__ import annotations

import pytest

import orgmetra_workforce_validation_api.final_weight_component_evidence_resolution as resolution_module
from orgmetra_workforce_validation_api.final_weight_component_evidence_resolution import (
    FinalWeightComponentEvidenceIntegrityError,
    FinalWeightComponentEvidenceResolution,
)
from test_final_weight_component_evidence_resolution_low_level_issuance import _base_evidence


def test_resolution_module_exposes_no_issuance_marker_capability() -> None:
    """Keep proof-result sealing authority out of ordinary module state."""
    assert not hasattr(resolution_module, "_RESOLUTION_ISSUANCE_MARKER")


def test_importable_marker_cannot_mint_proof_bearing_resolution() -> None:
    """Reject caller-populated proof slots even when a module marker is obtainable."""
    forged = object.__new__(FinalWeightComponentEvidenceResolution)
    object.__setattr__(
        forged,
        "_FinalWeightComponentEvidenceResolution__base_weight",
        _base_evidence(),
    )
    object.__setattr__(
        forged,
        "_FinalWeightComponentEvidenceResolution__adjustments",
        (),
    )
    caller_marker = getattr(resolution_module, "_RESOLUTION_ISSUANCE_MARKER", object())
    object.__setattr__(
        forged,
        "_FinalWeightComponentEvidenceResolution__issuance_marker",
        caller_marker,
    )

    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="not issued"):
        _ = forged.base_weight
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="not issued"):
        _ = forged.adjustments


def test_wrong_private_issuance_marker_cannot_expose_proof_properties() -> None:
    """Fail closed when hostile allocation populates a marker that is not the canonical seal."""
    forged = object.__new__(FinalWeightComponentEvidenceResolution)
    object.__setattr__(
        forged,
        "_FinalWeightComponentEvidenceResolution__issuance_marker",
        object(),
    )

    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="not issued"):
        _ = forged.base_weight
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="not issued"):
        _ = forged.adjustments


def test_resolution_module_exposes_no_generic_private_issuer() -> None:
    """Keep generic proof-result minting outside ordinary module state."""
    assert not hasattr(resolution_module, "_issue_component_evidence_resolution")
