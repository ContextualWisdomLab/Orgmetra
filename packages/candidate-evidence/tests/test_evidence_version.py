"""Regression coverage for explicit high-impact candidate-evidence versioning."""

from dataclasses import replace
import json

import pytest

from orgmetra_candidate_evidence import CandidateEvidenceIntakePacket

from test_packet import values


def _packet(evidence_version: int = 1) -> CandidateEvidenceIntakePacket:
    """Build one valid packet while varying only its immutable evidence version."""
    data = values()
    data["evidence_version"] = evidence_version
    return CandidateEvidenceIntakePacket(**data)


def test_evidence_version_is_canonical_evidence() -> None:
    """Bind the explicit evidence version into canonical JSON and its SHA-256 digest."""
    first = _packet(1)
    second = _packet(2)
    assert json.loads(first.canonical_json())["evidence_version"] == 1
    assert first.canonical_json() != second.canonical_json()
    assert first.sha256_digest() != second.sha256_digest()


@pytest.mark.parametrize("evidence_version", [True, False, 0, -1, 2_147_483_648, "1", 1.0])
def test_rejects_noncanonical_evidence_versions(evidence_version: object) -> None:
    """Reject booleans, non-integers, non-positive values, and signed-int32 overflow."""
    with pytest.raises(ValueError, match="evidence_version"):
        _packet(evidence_version)  # type: ignore[arg-type]


def test_replace_cannot_bypass_evidence_version_validation() -> None:
    """Revalidate explicit evidence-version bounds when immutable packets are copied."""
    with pytest.raises(ValueError, match="evidence_version"):
        replace(_packet(), evidence_version=0)
