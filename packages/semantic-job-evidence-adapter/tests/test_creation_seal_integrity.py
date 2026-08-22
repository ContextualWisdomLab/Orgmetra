"""Regression for authoritative creation evidence living outside packet-writable slots."""

import pytest

import orgmetra_semantic_job_evidence_adapter.envelope as envelope_module
from orgmetra_semantic_job_evidence_adapter import SemanticJobEvidenceEnvelope


def test_recomputed_packet_owned_seal_cannot_authorize_rewritten_evidence(
    semantic_values: dict[str, object],
) -> None:
    """Rewriting payload plus its packet-owned seal must still fail closed."""
    packet = SemanticJobEvidenceEnvelope(**semantic_values)
    object.__setattr__(packet, "response_evidence_digest", "d" * 64)
    forged_seal = envelope_module._seal(packet._canonical_payload_json())
    object.__setattr__(packet, "_creation_seal", forged_seal)

    with pytest.raises(ValueError, match="changed after construction"):
        packet.canonical_json()
