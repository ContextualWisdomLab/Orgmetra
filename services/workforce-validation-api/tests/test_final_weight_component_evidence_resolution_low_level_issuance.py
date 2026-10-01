"""Low-level issuance integrity for corroborated final-weight component evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.final_weight_component_evidence_resolution import (
    BaseWeightComponentEvidence,
    FinalWeightComponentEvidenceIntegrityError,
    FinalWeightComponentEvidenceResolution,
)
from test_final_weight_component_evidence_resolution import _ReadPort, _corroborate


def _base_evidence() -> BaseWeightComponentEvidence:
    """Return canonical base evidence for hostile result-allocation tests."""
    return BaseWeightComponentEvidence(
        tenant_record_id=UUID("10000000-0000-7000-8000-000000000001"),
        validity_study_id=UUID("00000000-0000-7000-8000-0000000000f1"),
        receipt_reference=(
            "base_weight_evidence_receipt:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        ),
        receipt_digest="2" * 64,
        evidence_version=1,
        method_code="inverse_probability",
        method_version=1,
        output_weight_artifact_digest="3" * 64,
        released_at=datetime(2026, 9, 19, 4, 0, tzinfo=timezone.utc),
    )


def test_tuple_new_cannot_bypass_corroborated_resolution_issuance() -> None:
    """Reject the built-in tuple constructor as an alternate proof issuer."""
    base = _base_evidence()

    with pytest.raises(TypeError):
        tuple.__new__(FinalWeightComponentEvidenceResolution, (base, ()))


def test_generic_object_allocation_cannot_expose_unsealed_proof() -> None:
    """Fail closed if generic allocation produces an exact but unissued result object."""
    forged = object.__new__(FinalWeightComponentEvidenceResolution)

    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="not issued"):
        _ = forged.base_weight
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="not issued"):
        _ = forged.adjustments


def test_canonical_issued_resolution_rejects_public_mutation() -> None:
    """Keep corroborated result state immutable after the canonical issuer seals it."""
    resolution = _corroborate(read_port=_ReadPort())

    with pytest.raises(AttributeError, match="immutable"):
        resolution.extra = _base_evidence()  # type: ignore[attr-defined]
    with pytest.raises(AttributeError, match="immutable"):
        del resolution.base_weight
