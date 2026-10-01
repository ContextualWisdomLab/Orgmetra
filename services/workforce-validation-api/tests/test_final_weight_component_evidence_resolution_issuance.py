"""Issuance integrity for corroborated final-weight component evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.final_weight_component_evidence_resolution import (
    BaseWeightComponentEvidence,
    FinalWeightComponentEvidenceResolution,
)


def test_corroborated_resolution_cannot_be_publicly_forged() -> None:
    """Require the proof-bearing resolution to be issued only by corroboration."""
    base = BaseWeightComponentEvidence(
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

    with pytest.raises(TypeError, match="issued only"):
        FinalWeightComponentEvidenceResolution(base_weight=base, adjustments=())
