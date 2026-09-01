"""Governance regression for release-readiness next-action guidance."""

from datetime import datetime, timezone

from orgmetra_release_readiness_review import build_release_readiness_review_packet

_DIGEST = "a" * 64


def test_next_action_requires_fresh_independent_review_without_hardcoding_approval_count() -> None:
    """Preserve AGENTS.md independent review while leaving approval counts to live policy."""
    values: dict[str, object] = {
        "candidate_revision_sha": "a" * 40,
        "requester_actor_reference": "actor:123e4567-e89b-42d3-a456-426614174000",
        "reviewer_actor_reference": "actor:123e4567-e89b-42d3-b456-426614174001",
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

    next_action = build_release_readiness_review_packet(**values).canonical_document()["next_action"]
    assert type(next_action) is str
    assert (
        "require fresh qualifying independent review evidence without manufacturing approval"
        in next_action
    )
    assert "not require fresh qualifying independent review" not in next_action.lower()
    assert "do not require fresh qualifying independent review" not in next_action.lower()
    assert "two approvals" not in next_action
    assert "approval after the last push" not in next_action
