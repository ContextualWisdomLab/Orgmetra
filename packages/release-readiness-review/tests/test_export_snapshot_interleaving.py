"""Adversarial checked-versus-emitted regressions for readiness export."""

from datetime import datetime, timezone

import pytest

from orgmetra_release_readiness_review import (
    ReleaseReadinessReviewPacket,
    build_release_readiness_review_packet,
)

_DIGEST = "a" * 64
_REQUESTER = "actor:123e4567-e89b-42d3-a456-426614174000"
_REVIEWER = "actor:123e4567-e89b-42d3-b456-426614174001"


class _ForgedText(str):
    """Model equality-compatible trust text introduced during export."""


def _packet() -> ReleaseReadinessReviewPacket:
    """Build one valid packet before installing an adversarial export interleaving."""
    values: dict[str, object] = {
        "candidate_revision_sha": "a" * 40,
        "requester_actor_reference": _REQUESTER,
        "reviewer_actor_reference": _REVIEWER,
        "reviewed_at": datetime(2020, 1, 1, tzinfo=timezone.utc),
    }
    for field_name in (
        "source_artifact_digest_sha256",
        "sbom_digest_sha256",
        "provenance_digest_sha256",
        "test_evidence_digest_sha256",
        "coverage_evidence_digest_sha256",
        "security_evidence_digest_sha256",
        "sast_evidence_digest_sha256",
        "recovery_evidence_digest_sha256",
        "operability_evidence_digest_sha256",
        "accessibility_evidence_digest_sha256",
        "migration_rollback_evidence_digest_sha256",
        "package_reproducibility_evidence_digest_sha256",
    ):
        values[field_name] = _DIGEST
    return build_release_readiness_review_packet(**values)


def test_export_validates_the_same_digest_snapshot_it_emits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject same-value forged text introduced after pre-export field validation."""
    packet = _packet()
    original_payload = ReleaseReadinessReviewPacket._payload

    def interleaving_payload(self: ReleaseReadinessReviewPacket) -> dict[str, object]:
        """Model a same-process mutation between validation and payload capture."""
        object.__setattr__(self, "security_evidence_digest_sha256", _ForgedText(_DIGEST))
        return original_payload(self)

    monkeypatch.setattr(ReleaseReadinessReviewPacket, "_payload", interleaving_payload)
    with pytest.raises(ValueError, match=r"security_evidence_digest_sha256.*exact string"):
        packet.canonical_document()
