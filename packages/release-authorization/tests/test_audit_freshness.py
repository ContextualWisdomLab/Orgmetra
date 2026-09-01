"""Regression for release-control freshness across immutable-audit latency."""

from datetime import datetime, timedelta, timezone

import pytest

from orgmetra_release_readiness_review import build_release_readiness_review_packet
from orgmetra_release_authorization import (
    ReleaseAuditReceipt,
    ReleaseAuthorizationError,
    ReleaseControlVerification,
    authorize_release_candidate,
)

_CANDIDATE = "a" * 40
_DIGEST = "1" * 64
_REQUESTER = "actor:11111111-1111-4111-8111-111111111111"
_REVIEWER = "actor:22222222-2222-4222-8222-222222222222"
_RELEASER = "actor:33333333-3333-4333-8333-333333333333"
_VERIFIED_AT = datetime(2026, 8, 26, 8, 0, tzinfo=timezone.utc)
_AUTHORIZED_AT = _VERIFIED_AT + timedelta(seconds=1)


def _readiness_packet():
    """Build one valid non-authorizing release-readiness packet."""
    kwargs = {
        "candidate_revision_sha": _CANDIDATE,
        "requester_actor_reference": _REQUESTER,
        "reviewer_actor_reference": _REVIEWER,
        "reviewed_at": _VERIFIED_AT - timedelta(seconds=1),
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
    return build_release_readiness_review_packet(**kwargs)


class _Authority:
    """Return fresh solo-maintainer control evidence for the exact candidate."""

    def verify_release_controls(self, readiness_packet: object, tag_name: str) -> ReleaseControlVerification:
        """Return controls fresh at the beginning of authorization."""
        assert readiness_packet is not None
        assert tag_name == "v1.2.3"
        return ReleaseControlVerification(
            candidate_revision_sha=_CANDIDATE,
            integrated_default_head_sha=_CANDIDATE,
            ruleset_evidence_digest_sha256="2" * 64,
            required_gate_evidence_digest_sha256="3" * 64,
            qualifying_independent_approval_count=0,
            last_push_approved=False,
            required_approving_review_count=0,
            require_last_push_approval=False,
            synthetic_required_reviewers_absent=True,
            review_threads_resolved=True,
            all_required_gates_green=True,
            routine_admin_bypass_disabled=True,
            verified_at=_VERIFIED_AT,
        )


class _SlowAudit:
    """Model durable audit completion after the control-freshness window expires."""

    def append_release_authorization(
        self, canonical_json: str, evidence_digest_sha256: str
    ) -> ReleaseAuditReceipt:
        """Return a valid binding whose durable record is too late for fresh authority."""
        assert canonical_json
        return ReleaseAuditReceipt(
            authorization_evidence_digest_sha256=evidence_digest_sha256,
            audit_event_envelope_digest_sha256="4" * 64,
            recorded_at=_VERIFIED_AT + timedelta(seconds=61),
        )


def test_authorization_rejects_controls_that_expire_during_immutable_audit() -> None:
    """Do not return release authority after durable audit outlives fresh controls."""
    with pytest.raises(ReleaseAuthorizationError, match="stale"):
        authorize_release_candidate(
            readiness_packet=_readiness_packet(),
            tag_name="v1.2.3",
            release_actor_reference=_RELEASER,
            authority=_Authority(),
            audit_port=_SlowAudit(),
            clock=lambda: _AUTHORIZED_AT,
        )
