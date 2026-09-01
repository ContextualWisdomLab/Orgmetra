"""Regression tests for the audited exact-revision release authorization boundary."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import pytest

from orgmetra_release_readiness_review import build_release_readiness_review_packet
from orgmetra_release_authorization import (
    ReleaseAuditReceipt,
    ReleaseAuthorizationError,
    ReleaseAuthorizationReceipt,
    ReleaseControlVerification,
    authorize_release_candidate,
)

_CANDIDATE = "a" * 40
_OTHER_REVISION = "b" * 40
_DIGEST = "1" * 64
_RULESET_DIGEST = "2" * 64
_GATE_DIGEST = "3" * 64
_AUDIT_DIGEST = "4" * 64
_REQUESTER = "actor:11111111-1111-4111-8111-111111111111"
_REVIEWER = "actor:22222222-2222-4222-8222-222222222222"
_RELEASER = "actor:33333333-3333-4333-8333-333333333333"
_VERIFIED_AT = datetime(2026, 8, 26, 4, 0, tzinfo=timezone.utc)
_AUTHORIZED_AT = _VERIFIED_AT + timedelta(seconds=1)
_AUDITED_AT = _VERIFIED_AT + timedelta(seconds=2)


def _readiness_packet():
    """Build one valid non-authorizing parent readiness packet."""
    kwargs = {
        "candidate_revision_sha": _CANDIDATE,
        "requester_actor_reference": _REQUESTER,
        "reviewer_actor_reference": _REVIEWER,
        "reviewed_at": datetime(2026, 8, 26, 3, 59, tzinfo=timezone.utc),
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


def _verification(**overrides: object) -> ReleaseControlVerification:
    """Build one syntactically valid live-control verification result."""
    values: dict[str, object] = {
        "candidate_revision_sha": _CANDIDATE,
        "integrated_default_head_sha": _CANDIDATE,
        "ruleset_evidence_digest_sha256": _RULESET_DIGEST,
        "required_gate_evidence_digest_sha256": _GATE_DIGEST,
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
    values.update(overrides)
    return ReleaseControlVerification(**values)


class _Authority:
    """Return one controlled fresh repository verification to the operation."""

    def __init__(self, result: object) -> None:
        """Remember the result and expose call evidence."""
        self.result = result
        self.calls = 0

    def verify_release_controls(self, readiness_packet: object, tag_name: str) -> object:
        """Return the configured verification after recording the call."""
        self.calls += 1
        assert readiness_packet is not None
        assert tag_name == "v1.2.3"
        return self.result


class _Audit:
    """Bind the authorization evidence to one immutable audit envelope digest."""

    def __init__(self, *, mismatch: bool = False, recorded_at: datetime = _AUDITED_AT) -> None:
        """Configure whether the durable audit receipt is intentionally invalid."""
        self.mismatch = mismatch
        self.recorded_at = recorded_at
        self.calls = 0
        self.last_document: dict[str, object] | None = None

    def append_release_authorization(self, canonical_json: str, evidence_digest_sha256: str) -> ReleaseAuditReceipt:
        """Return an audit receipt over the exact supplied authorization evidence."""
        self.calls += 1
        self.last_document = json.loads(canonical_json)
        bound_digest = "f" * 64 if self.mismatch else evidence_digest_sha256
        return ReleaseAuditReceipt(
            authorization_evidence_digest_sha256=bound_digest,
            audit_event_envelope_digest_sha256=_AUDIT_DIGEST,
            recorded_at=self.recorded_at,
        )


def test_authorize_release_candidate_binds_readiness_controls_and_audit() -> None:
    """Authorize exactly one reviewed integrated revision without publishing it."""
    authority = _Authority(_verification())
    audit = _Audit()

    receipt = authorize_release_candidate(
        readiness_packet=_readiness_packet(),
        tag_name="v1.2.3",
        release_actor_reference=_RELEASER,
        authority=authority,
        audit_port=audit,
        clock=lambda: _AUTHORIZED_AT,
    )

    assert authority.calls == 1
    assert audit.calls == 1
    assert receipt.candidate_revision_sha == _CANDIDATE
    assert receipt.tag_name == "v1.2.3"
    assert receipt.release_authority == "authorized_for_exact_release_operation"
    assert receipt.publication_state == "not_published"
    assert receipt.audit_event_envelope_digest_sha256 == _AUDIT_DIGEST
    assert receipt.authorized_at == _AUTHORIZED_AT
    document = receipt.canonical_document()
    assert document == json.loads(receipt.canonical_json())
    assert receipt.sha256_digest()
    assert audit.last_document is not None
    assert audit.last_document["candidate_revision_sha"] == _CANDIDATE
    assert audit.last_document["purpose_code"] == "release_authorization"
    assert audit.last_document["reason_code"] == "approved_commercial_release"


def test_authorization_rejects_non_readiness_object_before_authority() -> None:
    """Reject invented readiness evidence before consulting repository controls."""
    authority = _Authority(_verification())
    with pytest.raises(ReleaseAuthorizationError, match="ReleaseReadinessReviewPacket"):
        authorize_release_candidate(
            readiness_packet=object(),
            tag_name="v1.2.3",
            release_actor_reference=_RELEASER,
            authority=authority,
            audit_port=_Audit(),
            clock=lambda: _AUTHORIZED_AT,
        )
    assert authority.calls == 0


@pytest.mark.parametrize("tag_name", ["1.2.3", "v01.2.3", "v1.2", "v1.2.3-rc1"])
def test_authorization_rejects_noncanonical_release_tags(tag_name: str) -> None:
    """Require one canonical full-release SemVer-style tag before authority work."""
    authority = _Authority(_verification())
    with pytest.raises(ReleaseAuthorizationError, match="tag_name"):
        authorize_release_candidate(
            readiness_packet=_readiness_packet(),
            tag_name=tag_name,
            release_actor_reference=_RELEASER,
            authority=authority,
            audit_port=_Audit(),
            clock=lambda: _AUTHORIZED_AT,
        )
    assert authority.calls == 0


def test_authorization_rejects_string_subclass_tag() -> None:
    """Reject caller-defined tag text before regex or authority operations."""

    class ForgedText(str):
        """Represent untrusted polymorphic text."""

    with pytest.raises(ReleaseAuthorizationError, match="tag_name"):
        authorize_release_candidate(
            readiness_packet=_readiness_packet(),
            tag_name=ForgedText("v1.2.3"),
            release_actor_reference=_RELEASER,
            authority=_Authority(_verification()),
            audit_port=_Audit(),
            clock=lambda: _AUTHORIZED_AT,
        )


@pytest.mark.parametrize("release_actor", [_REQUESTER, _REVIEWER])
def test_authorization_requires_separate_release_actor(release_actor: str) -> None:
    """Keep the release actor separate from readiness requester and reviewer."""
    with pytest.raises(ReleaseAuthorizationError, match="release actor"):
        authorize_release_candidate(
            readiness_packet=_readiness_packet(),
            tag_name="v1.2.3",
            release_actor_reference=release_actor,
            authority=_Authority(_verification()),
            audit_port=_Audit(),
            clock=lambda: _AUTHORIZED_AT,
        )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"integrated_default_head_sha": _OTHER_REVISION}, "integrated default-branch head"),
        ({"candidate_revision_sha": _OTHER_REVISION}, "candidate revision"),
        ({"required_approving_review_count": 1}, "required approving review count"),
        ({"require_last_push_approval": True}, "last-push approval requirement"),
        ({"synthetic_required_reviewers_absent": False}, "synthetic required reviewers"),
        ({"review_threads_resolved": False}, "review threads"),
        ({"all_required_gates_green": False}, "required gate"),
        ({"routine_admin_bypass_disabled": False}, "administrator bypass"),
    ],
)
def test_authorization_rejects_weak_or_mismatched_live_controls(overrides: dict[str, object], message: str) -> None:
    """Fail closed when fresh repository truth does not meet commercial policy."""
    authority = _Authority(_verification(**overrides))
    with pytest.raises(ReleaseAuthorizationError, match=message):
        authorize_release_candidate(
            readiness_packet=_readiness_packet(),
            tag_name="v1.2.3",
            release_actor_reference=_RELEASER,
            authority=authority,
            audit_port=_Audit(),
            clock=lambda: _AUTHORIZED_AT,
        )


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("required_approving_review_count", 1, "required approving review count"),
        ("qualifying_independent_approval_count", True, "qualifying independent approval count"),
        ("last_push_approved", 1, "last_push_approved"),
    ],
)
def test_authorization_revalidates_mutated_control_verification(
    field_name: str, value: object, message: str
) -> None:
    """Reject a verification object weakened after its own construction."""
    verification = _verification()
    object.__setattr__(verification, field_name, value)
    with pytest.raises(ReleaseAuthorizationError, match=message):
        authorize_release_candidate(
            readiness_packet=_readiness_packet(),
            tag_name="v1.2.3",
            release_actor_reference=_RELEASER,
            authority=_Authority(verification),
            audit_port=_Audit(),
            clock=lambda: _AUTHORIZED_AT,
        )


def test_authorization_rejects_untyped_authority_result() -> None:
    """Reject duck-typed live-control evidence at the trust boundary."""
    with pytest.raises(ReleaseAuthorizationError, match="ReleaseControlVerification"):
        authorize_release_candidate(
            readiness_packet=_readiness_packet(),
            tag_name="v1.2.3",
            release_actor_reference=_RELEASER,
            authority=_Authority(object()),
            audit_port=_Audit(),
            clock=lambda: _AUTHORIZED_AT,
        )


def test_authorization_rejects_preverification_clock() -> None:
    """Do not issue release authority before the fresh control verification instant."""
    with pytest.raises(ReleaseAuthorizationError, match="authorized_at"):
        authorize_release_candidate(
            readiness_packet=_readiness_packet(),
            tag_name="v1.2.3",
            release_actor_reference=_RELEASER,
            authority=_Authority(_verification()),
            audit_port=_Audit(),
            clock=lambda: _VERIFIED_AT - timedelta(microseconds=1),
        )


def test_authorization_rejects_mismatched_or_preissuance_audit_receipt() -> None:
    """Require immutable audit evidence to bind the exact authorization before return."""
    with pytest.raises(ReleaseAuthorizationError, match="audit receipt digest"):
        authorize_release_candidate(
            readiness_packet=_readiness_packet(),
            tag_name="v1.2.3",
            release_actor_reference=_RELEASER,
            authority=_Authority(_verification()),
            audit_port=_Audit(mismatch=True),
            clock=lambda: _AUTHORIZED_AT,
        )
    with pytest.raises(ReleaseAuthorizationError, match="audit recorded_at"):
        authorize_release_candidate(
            readiness_packet=_readiness_packet(),
            tag_name="v1.2.3",
            release_actor_reference=_RELEASER,
            authority=_Authority(_verification()),
            audit_port=_Audit(recorded_at=_VERIFIED_AT),
            clock=lambda: _AUTHORIZED_AT,
        )


def test_weak_control_runtime_types_fail_closed() -> None:
    """Require exact primitive evidence for live repository controls."""
    with pytest.raises(ValueError, match="approval count"):
        _verification(qualifying_independent_approval_count=True)
    with pytest.raises(ValueError, match="approval count"):
        _verification(qualifying_independent_approval_count=-1)
    with pytest.raises(ValueError, match="required_approving_review_count"):
        _verification(required_approving_review_count=True)
    with pytest.raises(ValueError, match="required_approving_review_count"):
        _verification(required_approving_review_count=-1)
    with pytest.raises(ValueError, match="last_push_approved"):
        _verification(last_push_approved=1)
    with pytest.raises(ValueError, match="verified_at"):
        _verification(verified_at=datetime(2026, 8, 26, 4, 0))


def test_release_actor_runtime_type_and_shape_fail_closed() -> None:
    """Reject non-opaque release actor evidence before authority resolution."""

    class ForgedText(str):
        """Represent caller-defined actor text."""

    for actor in (ForgedText(_RELEASER), "actor:not-a-uuid"):
        with pytest.raises(ReleaseAuthorizationError, match="release_actor_reference"):
            authorize_release_candidate(
                readiness_packet=_readiness_packet(),
                tag_name="v1.2.3",
                release_actor_reference=actor,
                authority=_Authority(_verification()),
                audit_port=_Audit(),
                clock=lambda: _AUTHORIZED_AT,
            )


def test_receipt_cannot_be_directly_constructed_or_tampered() -> None:
    """Keep high-impact release authority factory-issued and mutation-detecting."""
    with pytest.raises(TypeError, match="factory-issued"):
        ReleaseAuthorizationReceipt()

    receipt = authorize_release_candidate(
        readiness_packet=_readiness_packet(),
        tag_name="v1.2.3",
        release_actor_reference=_RELEASER,
        authority=_Authority(_verification()),
        audit_port=_Audit(),
        clock=lambda: _AUTHORIZED_AT,
    )
    assert "<redacted>" in repr(receipt)
    object.__setattr__(receipt, "tag_name", "v9.9.9")
    with pytest.raises(ValueError, match="modified after issuance"):
        receipt.canonical_json()
