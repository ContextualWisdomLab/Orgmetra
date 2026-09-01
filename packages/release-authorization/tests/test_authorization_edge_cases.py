"""Adversarial edge regressions for release authorization evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from orgmetra_release_authorization import (
    ReleaseAuditReceipt,
    ReleaseAuthorizationError,
    ReleaseAuthorizationReceipt,
    ReleaseControlVerification,
    authorize_release_candidate,
)
from orgmetra_release_authorization.authorization import _validate_evidence_version
from orgmetra_release_readiness_review import build_release_readiness_review_packet

_CANDIDATE = "a" * 40
_DIGEST = "1" * 64
_REQUESTER = "actor:11111111-1111-4111-8111-111111111111"
_REVIEWER = "actor:22222222-2222-4222-8222-222222222222"
_RELEASER = "actor:33333333-3333-4333-8333-333333333333"
_VERIFIED_AT = datetime(2026, 8, 26, 4, 0, tzinfo=timezone.utc)


def _readiness_packet():
    """Build valid parent readiness evidence for edge tests."""
    kwargs = {
        "candidate_revision_sha": _CANDIDATE,
        "requester_actor_reference": _REQUESTER,
        "reviewer_actor_reference": _REVIEWER,
        "reviewed_at": _VERIFIED_AT - timedelta(minutes=1),
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


def _verification() -> ReleaseControlVerification:
    """Build one strong live-control result."""
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


class _Authority:
    """Return one configured control result."""

    def __init__(self, result: object) -> None:
        """Store the result."""
        self.result = result

    def verify_release_controls(self, readiness_packet: object, tag_name: str) -> object:
        """Return the configured result."""
        assert readiness_packet is not None
        assert tag_name == "v1.2.3"
        return self.result


class _Audit:
    """Return a matching durable audit receipt."""

    def append_release_authorization(self, canonical_json: str, evidence_digest_sha256: str) -> ReleaseAuditReceipt:
        """Bind the supplied exact evidence digest."""
        assert canonical_json
        return ReleaseAuditReceipt(
            authorization_evidence_digest_sha256=evidence_digest_sha256,
            audit_event_envelope_digest_sha256="4" * 64,
            recorded_at=_VERIFIED_AT + timedelta(seconds=3),
        )


class _UntypedAudit:
    """Return a non-governed audit result."""

    def append_release_authorization(self, canonical_json: str, evidence_digest_sha256: str) -> object:
        """Return an invented result despite receiving valid evidence."""
        assert canonical_json and evidence_digest_sha256
        return object()


class _MalformedAudit:
    """Return an audit receipt mutated after construction."""

    def append_release_authorization(self, canonical_json: str, evidence_digest_sha256: str) -> ReleaseAuditReceipt:
        """Forge the digest runtime type after initial validation."""
        assert canonical_json
        receipt = ReleaseAuditReceipt(
            authorization_evidence_digest_sha256=evidence_digest_sha256,
            audit_event_envelope_digest_sha256="4" * 64,
            recorded_at=_VERIFIED_AT + timedelta(seconds=3),
        )
        object.__setattr__(receipt, "authorization_evidence_digest_sha256", object())
        return receipt


def test_stale_control_verification_cannot_authorize_release() -> None:
    """Require a bounded fresh-control window before issuing release authority."""
    with pytest.raises(ReleaseAuthorizationError, match="stale"):
        authorize_release_candidate(
            readiness_packet=_readiness_packet(),
            tag_name="v1.2.3",
            release_actor_reference=_RELEASER,
            authority=_Authority(_verification()),
            audit_port=_Audit(),
            clock=lambda: _VERIFIED_AT + timedelta(seconds=61),
        )


def test_invalid_authorization_clock_fails_closed() -> None:
    """Reject a naive host clock after repository verification."""
    with pytest.raises(ReleaseAuthorizationError, match="authorized_at"):
        authorize_release_candidate(
            readiness_packet=_readiness_packet(),
            tag_name="v1.2.3",
            release_actor_reference=_RELEASER,
            authority=_Authority(_verification()),
            audit_port=_Audit(),
            clock=lambda: datetime(2026, 8, 26, 4, 0),
        )


def test_mutated_control_trust_evidence_fails_closed() -> None:
    """Revalidate the exact snapshot rather than trusting a constructed container."""
    verification = _verification()
    object.__setattr__(verification, "candidate_revision_sha", object())
    with pytest.raises(ReleaseAuthorizationError, match="invalid trust evidence"):
        authorize_release_candidate(
            readiness_packet=_readiness_packet(),
            tag_name="v1.2.3",
            release_actor_reference=_RELEASER,
            authority=_Authority(verification),
            audit_port=_Audit(),
            clock=lambda: _VERIFIED_AT + timedelta(seconds=1),
        )


@pytest.mark.parametrize("audit_port", [_UntypedAudit(), _MalformedAudit()])
def test_untyped_or_mutated_audit_evidence_fails_closed(audit_port: object) -> None:
    """Reject invented or post-construction-mutated durable audit receipts."""
    with pytest.raises(ReleaseAuthorizationError, match="audit"):
        authorize_release_candidate(
            readiness_packet=_readiness_packet(),
            tag_name="v1.2.3",
            release_actor_reference=_RELEASER,
            authority=_Authority(_verification()),
            audit_port=audit_port,
            clock=lambda: _VERIFIED_AT + timedelta(seconds=1),
        )


def test_control_and_audit_runtime_constructors_reject_malformed_evidence() -> None:
    """Exercise exact primitive guards on host-owned trust evidence."""
    with pytest.raises(ValueError, match="candidate_revision_sha"):
        ReleaseControlVerification(
            candidate_revision_sha="not-a-revision",
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
    with pytest.raises(ValueError, match="ruleset_evidence"):
        ReleaseControlVerification(
            candidate_revision_sha=_CANDIDATE,
            integrated_default_head_sha=_CANDIDATE,
            ruleset_evidence_digest_sha256="bad",
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
    with pytest.raises(ValueError, match="audit_event_envelope"):
        ReleaseAuditReceipt(
            authorization_evidence_digest_sha256="1" * 64,
            audit_event_envelope_digest_sha256="bad",
            recorded_at=_VERIFIED_AT,
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "last_push_approved",
        "require_last_push_approval",
        "synthetic_required_reviewers_absent",
        "review_threads_resolved",
        "all_required_gates_green",
        "routine_admin_bypass_disabled",
    ],
)
def test_control_boolean_fields_require_exact_bool(field_name: str) -> None:
    """Reject integer-like or polymorphic control truth values."""
    values = {
        "candidate_revision_sha": _CANDIDATE,
        "integrated_default_head_sha": _CANDIDATE,
        "ruleset_evidence_digest_sha256": "2" * 64,
        "required_gate_evidence_digest_sha256": "3" * 64,
        "qualifying_independent_approval_count": 0,
        "last_push_approved": False,
        "required_approving_review_count": 0,
        "require_last_push_approval": False,
        "synthetic_required_reviewers_absent": True,
        "review_threads_resolved": True,
        "all_required_gates_green": True,
        "routine_admin_bypass_disabled": True,
        "verified_at": _VERIFIED_AT,
    }
    values[field_name] = 1
    with pytest.raises(ValueError, match=field_name):
        ReleaseControlVerification(**values)


def test_final_trust_types_reject_subclass_overrides() -> None:
    """Keep trust-bearing container semantics final."""
    with pytest.raises(TypeError, match="ReleaseControlVerification"):

        class ForgedControl(ReleaseControlVerification):
            """Attempt to override live-control semantics."""

    with pytest.raises(TypeError, match="ReleaseAuditReceipt"):

        class ForgedAudit(ReleaseAuditReceipt):
            """Attempt to override audit semantics."""

    with pytest.raises(TypeError, match="ReleaseAuthorizationReceipt"):

        class ForgedReceipt(ReleaseAuthorizationReceipt):
            """Attempt to override issued release authority."""


def test_evidence_version_helper_accepts_only_exact_version_one() -> None:
    """Keep the release-authorization evidence schema version exact and non-coercible."""
    assert _validate_evidence_version(1) == 1
    for value in (True, 2):
        with pytest.raises(ValueError, match="evidence_version"):
            _validate_evidence_version(value)
