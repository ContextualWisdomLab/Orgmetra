"""Hostile issuance-marker and private-issuer edge cases for component evidence."""

from __future__ import annotations

import pytest

import orgmetra_workforce_validation_api.final_weight_component_evidence_resolution as resolution_module
from orgmetra_workforce_validation_api.final_weight_component_evidence_resolution import (
    FinalWeightComponentEvidenceIntegrityError,
    FinalWeightComponentEvidenceResolution,
)
from test_final_weight_component_evidence_resolution_low_level_issuance import _base_evidence


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


def test_private_issuer_rejects_mutable_adjustment_collection() -> None:
    """Keep the internal proof issuer fail-closed if a future caller passes mutable state."""
    with pytest.raises(
        FinalWeightComponentEvidenceIntegrityError,
        match="immutable tuple",
    ):
        resolution_module._issue_component_evidence_resolution(
            base_weight=_base_evidence(),
            adjustments=[],  # type: ignore[arg-type]
        )


def test_private_issuer_rejects_noncanonical_adjustment_member() -> None:
    """Reject an immutable container whose member is not canonical adjustment evidence."""
    with pytest.raises(
        FinalWeightComponentEvidenceIntegrityError,
        match="non-canonical specialized evidence",
    ):
        resolution_module._issue_component_evidence_resolution(
            base_weight=_base_evidence(),
            adjustments=(object(),),  # type: ignore[arg-type]
        )
