"""Regression for publication evidence that occurs after authorization expiry."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from orgmetra_release_readiness_review import build_release_readiness_review_packet
from orgmetra_release_authorization import ReleaseAuditReceipt, ReleaseControlVerification, authorize_release_candidate
from orgmetra_release_publication import (
    ReleasePlatformReceipt,
    ReleasePublicationIndeterminateError,
    publish_authorized_release,
)

_CANDIDATE = "a" * 40
_DIGEST = "1" * 64
_REQUESTER = "actor:11111111-1111-4111-8111-111111111111"
_REVIEWER = "actor:22222222-2222-4222-8222-222222222222"
_RELEASER = "actor:33333333-3333-4333-8333-333333333333"
_REFERENCE = "release_publication:44444444-4444-4444-8444-444444444444"
_VERIFIED = datetime(2026, 8, 26, 8, 0, tzinfo=timezone.utc)
_AUDITED = _VERIFIED + timedelta(seconds=2)


class _Authority:
    """Return exact acquisition-grade repository controls."""

    def verify_release_controls(self, readiness_packet: object, tag_name: str) -> ReleaseControlVerification:
        """Return one fresh exact control snapshot."""
        assert readiness_packet is not None and tag_name == "v1.2.3"
        return ReleaseControlVerification(
            candidate_revision_sha=_CANDIDATE,
            integrated_default_head_sha=_CANDIDATE,
            ruleset_evidence_digest_sha256="2" * 64,
            required_gate_evidence_digest_sha256="3" * 64,
            qualifying_independent_approval_count=2,
            last_push_approved=True,
            review_threads_resolved=True,
            all_required_gates_green=True,
            routine_admin_bypass_disabled=True,
            verified_at=_VERIFIED,
        )


class _Audit:
    """Bind the parent authorization to immutable audit evidence."""

    def append_release_authorization(self, canonical_json: str, evidence_digest_sha256: str) -> ReleaseAuditReceipt:
        """Return one exact durable authorization audit receipt."""
        assert canonical_json
        return ReleaseAuditReceipt(
            authorization_evidence_digest_sha256=evidence_digest_sha256,
            audit_event_envelope_digest_sha256="4" * 64,
            recorded_at=_AUDITED,
        )


def _authorization():
    """Build one legitimate exact parent authorization."""
    kwargs = {
        "candidate_revision_sha": _CANDIDATE,
        "requester_actor_reference": _REQUESTER,
        "reviewer_actor_reference": _REVIEWER,
        "reviewed_at": _VERIFIED - timedelta(minutes=1),
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
        kwargs[field_name] = _DIGEST
    readiness = build_release_readiness_review_packet(**kwargs)
    return authorize_release_candidate(
        readiness_packet=readiness,
        tag_name="v1.2.3",
        release_actor_reference=_RELEASER,
        authority=_Authority(),
        audit_port=_Audit(),
        clock=lambda: _VERIFIED + timedelta(seconds=1),
    )


class _LatePublisher:
    """Simulate a host that wrongly publishes after the authorization freshness window."""

    def __init__(self, authorization_digest: str) -> None:
        """Remember the exact parent authorization digest."""
        self.authorization_digest = authorization_digest
        self.publish_calls = 0
        self.reconcile_calls = 0

    def _late_receipt(self) -> ReleasePlatformReceipt:
        """Return evidence for a publication after authorization expiry."""
        return ReleasePlatformReceipt(
            authorization_evidence_digest_sha256=self.authorization_digest,
            candidate_revision_sha=_CANDIDATE,
            tag_name="v1.2.3",
            publication_reference=_REFERENCE,
            platform_release_digest_sha256="5" * 64,
            audit_event_envelope_digest_sha256="6" * 64,
            published_at=_AUDITED + timedelta(seconds=61),
        )

    def publish_release(self, **kwargs: object) -> object:
        """Return a stale publication result once."""
        self.publish_calls += 1
        assert kwargs["authorization_evidence_digest_sha256"] == self.authorization_digest
        return self._late_receipt()

    def reconcile_release(self, **kwargs: object) -> object:
        """Expose read-only lookup evidence if an operator later reconciles this correlation."""
        self.reconcile_calls += 1
        assert kwargs["authorization_evidence_digest_sha256"] == self.authorization_digest
        return self._late_receipt()


def test_publication_after_authorization_expiry_is_indeterminate_and_never_republished() -> None:
    """Do not bless or retry a host release published after authorization expiry."""
    authorization = _authorization()
    publisher = _LatePublisher(authorization.sha256_digest())
    with pytest.raises(ReleasePublicationIndeterminateError, match="do not republish"):
        publish_authorized_release(
            authorization_receipt=authorization,
            publication_reference=_REFERENCE,
            publisher=publisher,
            clock=lambda: _AUDITED + timedelta(seconds=1),
        )
    assert publisher.publish_calls == 1
    assert publisher.reconcile_calls == 0
