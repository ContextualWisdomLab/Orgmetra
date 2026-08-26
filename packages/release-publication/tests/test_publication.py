"""Regression tests for one-shot audited exact-revision release publication."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from orgmetra_release_readiness_review import build_release_readiness_review_packet
from orgmetra_release_authorization import (
    ReleaseAuditReceipt,
    ReleaseControlVerification,
    authorize_release_candidate,
)
from orgmetra_release_publication import (
    ReleasePlatformReceipt,
    ReleasePublicationError,
    ReleasePublicationIndeterminateError,
    publish_authorized_release,
)

_CANDIDATE = "a" * 40
_DIGEST = "1" * 64
_RULESET_DIGEST = "2" * 64
_GATE_DIGEST = "3" * 64
_AUTH_AUDIT_DIGEST = "4" * 64
_PLATFORM_DIGEST = "5" * 64
_PUBLICATION_AUDIT_DIGEST = "6" * 64
_REQUESTER = "actor:11111111-1111-4111-8111-111111111111"
_REVIEWER = "actor:22222222-2222-4222-8222-222222222222"
_RELEASER = "actor:33333333-3333-4333-8333-333333333333"
_PUBLICATION_REFERENCE = "release_publication:44444444-4444-4444-8444-444444444444"
_VERIFIED_AT = datetime(2026, 8, 26, 8, 0, tzinfo=timezone.utc)
_AUTHORIZED_AT = _VERIFIED_AT + timedelta(seconds=1)
_AUTH_AUDITED_AT = _VERIFIED_AT + timedelta(seconds=2)
_PUBLISH_STARTED_AT = _VERIFIED_AT + timedelta(seconds=3)
_PUBLISHED_AT = _VERIFIED_AT + timedelta(seconds=4)


def _readiness_packet():
    """Build one valid parent readiness packet."""
    kwargs = {
        "candidate_revision_sha": _CANDIDATE,
        "requester_actor_reference": _REQUESTER,
        "reviewer_actor_reference": _REVIEWER,
        "reviewed_at": datetime(2026, 8, 26, 7, 59, tzinfo=timezone.utc),
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


class _ControlAuthority:
    """Return acquisition-grade live controls for the parent authorization boundary."""

    def verify_release_controls(self, readiness_packet: object, tag_name: str) -> ReleaseControlVerification:
        """Return exact controls for the requested candidate and tag."""
        assert readiness_packet is not None
        assert tag_name == "v1.2.3"
        return ReleaseControlVerification(
            candidate_revision_sha=_CANDIDATE,
            integrated_default_head_sha=_CANDIDATE,
            ruleset_evidence_digest_sha256=_RULESET_DIGEST,
            required_gate_evidence_digest_sha256=_GATE_DIGEST,
            qualifying_independent_approval_count=2,
            last_push_approved=True,
            review_threads_resolved=True,
            all_required_gates_green=True,
            routine_admin_bypass_disabled=True,
            verified_at=_VERIFIED_AT,
        )


class _AuthorizationAudit:
    """Return one valid durable authorization-audit receipt."""

    def append_release_authorization(self, canonical_json: str, evidence_digest_sha256: str) -> ReleaseAuditReceipt:
        """Bind exact authorization evidence to an immutable audit envelope."""
        assert canonical_json
        return ReleaseAuditReceipt(
            authorization_evidence_digest_sha256=evidence_digest_sha256,
            audit_event_envelope_digest_sha256=_AUTH_AUDIT_DIGEST,
            recorded_at=_AUTH_AUDITED_AT,
        )


def _authorization_receipt():
    """Create one legitimate parent release-authorization receipt."""
    return authorize_release_candidate(
        readiness_packet=_readiness_packet(),
        tag_name="v1.2.3",
        release_actor_reference=_RELEASER,
        authority=_ControlAuthority(),
        audit_port=_AuthorizationAudit(),
        clock=lambda: _AUTHORIZED_AT,
    )


def _platform_receipt(
    *, authorization_evidence_digest_sha256: str | None = None, **overrides: object
) -> ReleasePlatformReceipt:
    """Build one valid host-owned publication receipt with optional overrides."""
    if authorization_evidence_digest_sha256 is None:
        authorization_evidence_digest_sha256 = _authorization_receipt().sha256_digest()
    values: dict[str, object] = {
        "authorization_evidence_digest_sha256": authorization_evidence_digest_sha256,
        "candidate_revision_sha": _CANDIDATE,
        "tag_name": "v1.2.3",
        "publication_reference": _PUBLICATION_REFERENCE,
        "platform_release_digest_sha256": _PLATFORM_DIGEST,
        "audit_event_envelope_digest_sha256": _PUBLICATION_AUDIT_DIGEST,
        "published_at": _PUBLISHED_AT,
    }
    values.update(overrides)
    return ReleasePlatformReceipt(**values)


class _Publisher:
    """Model an idempotent host release publisher plus reconciliation lookup."""

    def __init__(self, result: object, *, reconcile_result: object | None = None, raise_publish: bool = False) -> None:
        """Configure immediate and reconciliation evidence."""
        self.result = result
        self.reconcile_result = reconcile_result
        self.raise_publish = raise_publish
        self.publish_calls = 0
        self.reconcile_calls = 0

    def publish_release(
        self,
        *,
        candidate_revision_sha: str,
        tag_name: str,
        publication_reference: str,
        authorization_evidence_digest_sha256: str,
    ) -> object:
        """Publish at most once or simulate an ambiguous host failure."""
        self.publish_calls += 1
        assert candidate_revision_sha == _CANDIDATE
        assert tag_name == "v1.2.3"
        assert publication_reference == _PUBLICATION_REFERENCE
        assert len(authorization_evidence_digest_sha256) == 64
        if self.raise_publish:
            raise RuntimeError("publication response lost")
        return self.result

    def reconcile_release(
        self,
        *,
        candidate_revision_sha: str,
        tag_name: str,
        publication_reference: str,
        authorization_evidence_digest_sha256: str,
    ) -> object | None:
        """Look up prior publication without issuing a second publication."""
        self.reconcile_calls += 1
        assert candidate_revision_sha == _CANDIDATE
        assert tag_name == "v1.2.3"
        assert publication_reference == _PUBLICATION_REFERENCE
        assert len(authorization_evidence_digest_sha256) == 64
        return self.reconcile_result


def test_publication_consumes_exact_authorization_once() -> None:
    """Publish one exact candidate and return immutable publication evidence."""
    authorization = _authorization_receipt()
    publisher = _Publisher(
        _platform_receipt(authorization_evidence_digest_sha256=authorization.sha256_digest())
    )
    receipt = publish_authorized_release(
        authorization_receipt=authorization,
        publication_reference=_PUBLICATION_REFERENCE,
        publisher=publisher,
        clock=lambda: _PUBLISH_STARTED_AT,
    )
    assert publisher.publish_calls == 1
    assert publisher.reconcile_calls == 0
    assert receipt.candidate_revision_sha == _CANDIDATE
    assert receipt.tag_name == "v1.2.3"
    assert receipt.publication_state == "published"
    assert receipt.authorization_consumption_state == "consumed_once"
    assert receipt.canonical_document()["platform_release_digest_sha256"] == _PLATFORM_DIGEST
    assert receipt.sha256_digest()
    assert repr(receipt) == "ReleasePublicationReceipt(<redacted>)"


def test_publication_rejects_non_authorization_before_host_work() -> None:
    """Reject invented authorization evidence before any publication call."""
    publisher = _Publisher(_platform_receipt())
    with pytest.raises(ReleasePublicationError, match="ReleaseAuthorizationReceipt"):
        publish_authorized_release(
            authorization_receipt=object(),
            publication_reference=_PUBLICATION_REFERENCE,
            publisher=publisher,
            clock=lambda: _PUBLISH_STARTED_AT,
        )
    assert publisher.publish_calls == 0


def test_publication_rejects_stale_authorization_before_host_work() -> None:
    """Require publication to begin promptly after the durable authorization audit."""
    publisher = _Publisher(_platform_receipt())
    with pytest.raises(ReleasePublicationError, match="stale"):
        publish_authorized_release(
            authorization_receipt=_authorization_receipt(),
            publication_reference=_PUBLICATION_REFERENCE,
            publisher=publisher,
            clock=lambda: _AUTH_AUDITED_AT + timedelta(seconds=61),
        )
    assert publisher.publish_calls == 0


@pytest.mark.parametrize(
    "reference",
    ["release_publication:not-a-uuid", "publication:44444444-4444-4444-8444-444444444444"],
)
def test_publication_rejects_invalid_correlation_reference(reference: str) -> None:
    """Require one opaque UUIDv4 publication correlation before side effects."""
    publisher = _Publisher(_platform_receipt())
    with pytest.raises(ReleasePublicationError, match="publication_reference"):
        publish_authorized_release(
            authorization_receipt=_authorization_receipt(),
            publication_reference=reference,
            publisher=publisher,
            clock=lambda: _PUBLISH_STARTED_AT,
        )
    assert publisher.publish_calls == 0


def test_lost_publish_response_reconciles_without_republication() -> None:
    """Recover ambiguous success by lookup only and never publish twice."""
    authorization = _authorization_receipt()
    reconciled = _platform_receipt(
        authorization_evidence_digest_sha256=authorization.sha256_digest()
    )
    publisher = _Publisher(object(), reconcile_result=reconciled, raise_publish=True)
    receipt = publish_authorized_release(
        authorization_receipt=authorization,
        publication_reference=_PUBLICATION_REFERENCE,
        publisher=publisher,
        clock=lambda: _PUBLISH_STARTED_AT,
    )
    assert receipt.platform_release_digest_sha256 == _PLATFORM_DIGEST
    assert publisher.publish_calls == 1
    assert publisher.reconcile_calls == 1


def test_malformed_immediate_receipt_reconciles_without_republication() -> None:
    """Treat malformed immediate host evidence as ambiguous and reconcile by correlation."""
    authorization = _authorization_receipt()
    publisher = _Publisher(
        object(),
        reconcile_result=_platform_receipt(
            authorization_evidence_digest_sha256=authorization.sha256_digest()
        ),
    )
    receipt = publish_authorized_release(
        authorization_receipt=authorization,
        publication_reference=_PUBLICATION_REFERENCE,
        publisher=publisher,
        clock=lambda: _PUBLISH_STARTED_AT,
    )
    assert receipt.publication_state == "published"
    assert publisher.publish_calls == 1
    assert publisher.reconcile_calls == 1


def test_missing_reconciliation_is_indeterminate_and_non_retryable() -> None:
    """Fail closed without a second publish when the side effect may already exist."""
    publisher = _Publisher(object(), reconcile_result=None, raise_publish=True)
    with pytest.raises(ReleasePublicationIndeterminateError, match="do not republish"):
        publish_authorized_release(
            authorization_receipt=_authorization_receipt(),
            publication_reference=_PUBLICATION_REFERENCE,
            publisher=publisher,
            clock=lambda: _PUBLISH_STARTED_AT,
        )
    assert publisher.publish_calls == 1
    assert publisher.reconcile_calls == 1


def test_reconciliation_scope_mismatch_is_indeterminate() -> None:
    """Reject reconciliation evidence that does not bind the authorized exact candidate."""
    authorization = _authorization_receipt()
    bad = _platform_receipt(
        authorization_evidence_digest_sha256=authorization.sha256_digest(),
        candidate_revision_sha="b" * 40,
    )
    publisher = _Publisher(object(), reconcile_result=bad, raise_publish=True)
    with pytest.raises(ReleasePublicationIndeterminateError, match="do not republish"):
        publish_authorized_release(
            authorization_receipt=authorization,
            publication_reference=_PUBLICATION_REFERENCE,
            publisher=publisher,
            clock=lambda: _PUBLISH_STARTED_AT,
        )
    assert publisher.publish_calls == 1
    assert publisher.reconcile_calls == 1


def test_platform_receipt_bound_to_other_authorization_is_indeterminate() -> None:
    """Reject host evidence bound to a different exact parent authorization receipt."""
    authorization = _authorization_receipt()
    other_authorization = _authorization_receipt()
    assert authorization.sha256_digest() != other_authorization.sha256_digest()
    publisher = _Publisher(
        _platform_receipt(
            authorization_evidence_digest_sha256=other_authorization.sha256_digest()
        ),
        reconcile_result=None,
    )
    with pytest.raises(ReleasePublicationIndeterminateError, match="do not republish"):
        publish_authorized_release(
            authorization_receipt=authorization,
            publication_reference=_PUBLICATION_REFERENCE,
            publisher=publisher,
            clock=lambda: _PUBLISH_STARTED_AT,
        )
    assert publisher.publish_calls == 1
    assert publisher.reconcile_calls == 1


def test_publication_receipt_rejects_post_issuance_rewrite() -> None:
    """Prevent one published release receipt from emitting a second canonical truth."""
    authorization = _authorization_receipt()
    receipt = publish_authorized_release(
        authorization_receipt=authorization,
        publication_reference=_PUBLICATION_REFERENCE,
        publisher=_Publisher(
            _platform_receipt(
                authorization_evidence_digest_sha256=authorization.sha256_digest()
            )
        ),
        clock=lambda: _PUBLISH_STARTED_AT,
    )
    object.__setattr__(receipt, "publication_state", "not_published")
    with pytest.raises(ValueError, match="modified after issuance"):
        receipt.canonical_json()
