"""Governed, non-authorizing release-readiness review evidence for Orgmetra."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from threading import RLock
from typing import ClassVar
from weakref import WeakKeyDictionary

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_NULL_REVISION = "0" * 40
_ACTOR_PATTERN = re.compile(
    r"^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_PURPOSE_CODE = "release_readiness_review"
_REVIEW_STATE = "requires_human_review"
_INTEGRATION_STATE = "requires_protected_head_verification"
_RELEASE_AUTHORITY = "not_authorized_to_release"
_EVIDENCE_VERSION = 1
_NEXT_ACTION = (
    "Freshly verify that candidate_revision_sha is the integrated default-branch head, "
    "re-resolve every referenced CI/security/coverage/recovery/accessibility/operability/"
    "migration/package/SBOM/provenance artifact to that same revision, verify the effective "
    "repository ruleset and its required review policy, require fresh qualifying independent review "
    "evidence without manufacturing approval, then perform release authorization separately. "
    "This packet never tags, publishes, signs, deploys, or releases."
)
_DIGEST_FIELDS = (
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
)


def _require_exact_text(value: object, field_name: str) -> str:
    """Return trust-bearing text only when it is an exact built-in string."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be an exact string")
    return value


def _validate_revision(value: object) -> str:
    """Require one exact lower-case forty-hex Git revision."""
    text = _require_exact_text(value, "candidate_revision_sha")
    if not _REVISION_PATTERN.fullmatch(text):
        raise ValueError("candidate_revision_sha must be 40 lower-case hexadecimal characters")
    if text == _NULL_REVISION:
        raise ValueError("candidate_revision_sha must not use the null Git revision")
    return text


def _validate_digest(value: object, field_name: str) -> str:
    """Require exact lower-case SHA-256 evidence."""
    text = _require_exact_text(value, field_name)
    if not _SHA256_PATTERN.fullmatch(text):
        raise ValueError(f"{field_name} must be lower-case SHA-256 hex")
    return text


def _validate_actor_reference(value: object, field_name: str) -> str:
    """Require one pseudonymous packet-local actor UUIDv4 correlation."""
    text = _require_exact_text(value, field_name)
    if not _ACTOR_PATTERN.fullmatch(text):
        raise ValueError(f"{field_name} must be an opaque actor:<canonical-uuidv4> reference")
    return text


def _validate_timestamp(value: object, field_name: str) -> datetime:
    """Require an exact built-in UTC datetime."""
    if type(value) is not datetime:
        raise ValueError(f"{field_name} must be an exact built-in datetime")
    if value.tzinfo is not timezone.utc:
        raise ValueError(f"{field_name} must use timezone.utc")
    return value


def _validate_evidence_version(value: object) -> int:
    """Require the one currently supported evidence schema version."""
    if type(value) is not int:
        raise ValueError("evidence_version must be exact integer 1")
    if value != _EVIDENCE_VERSION:
        raise ValueError("evidence_version must be exact integer 1")
    return value


def _system_recorded_utc() -> datetime:
    """Return Orgmetra-owned system-recorded issuance time."""
    return datetime.now(timezone.utc)


def _canonical_timestamp(value: datetime) -> str:
    """Render one trusted UTC timestamp as RFC 3339 text."""
    return value.isoformat().replace("+00:00", "Z")


def _canonical_json(payload: dict[str, object]) -> str:
    """Serialize canonical release-readiness evidence deterministically."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True, slots=True, weakref_slot=True, eq=False, repr=False)
class ReleaseReadinessReviewPacket:
    """Human review evidence for one candidate revision without release authority."""

    candidate_revision_sha: str
    source_artifact_digest_sha256: str
    sbom_digest_sha256: str
    provenance_digest_sha256: str
    test_evidence_digest_sha256: str
    coverage_evidence_digest_sha256: str
    security_evidence_digest_sha256: str
    sast_evidence_digest_sha256: str
    recovery_evidence_digest_sha256: str
    operability_evidence_digest_sha256: str
    accessibility_evidence_digest_sha256: str
    migration_rollback_evidence_digest_sha256: str
    package_reproducibility_evidence_digest_sha256: str
    requester_actor_reference: str
    reviewer_actor_reference: str
    reviewed_at: datetime
    evidence_version: int = _EVIDENCE_VERSION
    recorded_at: datetime = field(init=False, default_factory=_system_recorded_utc)
    purpose_code: str = _PURPOSE_CODE
    review_state: str = _REVIEW_STATE
    integration_state: str = _INTEGRATION_STATE
    release_authority: str = _RELEASE_AUTHORITY
    human_review_required: bool = True
    next_action: str = _NEXT_ACTION

    _issuance_digests: ClassVar[WeakKeyDictionary["ReleaseReadinessReviewPacket", str]] = WeakKeyDictionary()
    _issuance_lock: ClassVar[RLock] = RLock()

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Reject subtype-based overrides of the trust-bearing packet contract."""
        raise TypeError("ReleaseReadinessReviewPacket is a final trust-bearing runtime type")

    def __post_init__(self) -> None:
        """Validate all reviewed evidence and seal its exact creation snapshot."""
        _validate_revision(self.candidate_revision_sha)
        for field_name in _DIGEST_FIELDS:
            _validate_digest(getattr(self, field_name), field_name)
        _validate_actor_reference(self.requester_actor_reference, "requester_actor_reference")
        _validate_actor_reference(self.reviewer_actor_reference, "reviewer_actor_reference")
        if self.requester_actor_reference == self.reviewer_actor_reference:
            raise ValueError("requester and reviewer must be different actor references")
        reviewed_at = _validate_timestamp(self.reviewed_at, "reviewed_at")
        recorded_at = _validate_timestamp(self.recorded_at, "recorded_at")
        if recorded_at < reviewed_at:
            raise ValueError("recorded_at cannot precede reviewed_at")
        _validate_evidence_version(self.evidence_version)
        self._require_fixed_governance()
        payload = self._payload()
        digest = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
        with self._issuance_lock:
            self._issuance_digests[self] = digest

    def _require_fixed_governance(self) -> None:
        """Fail closed if any derived non-authorizing governance state changes."""
        if type(self.purpose_code) is not str or self.purpose_code != _PURPOSE_CODE:
            raise ValueError("purpose_code must remain release_readiness_review")
        if type(self.review_state) is not str or self.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain requires_human_review")
        if type(self.integration_state) is not str or self.integration_state != _INTEGRATION_STATE:
            raise ValueError("integration_state must remain requires_protected_head_verification")
        if type(self.release_authority) is not str or self.release_authority != _RELEASE_AUTHORITY:
            raise ValueError("release_authority must remain not_authorized_to_release")
        if self.human_review_required is not True:
            raise ValueError("human review is mandatory for release readiness")
        if type(self.next_action) is not str or self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed release-readiness instruction")

    def __repr__(self) -> str:
        """Return a correlation-safe routine representation."""
        return "ReleaseReadinessReviewPacket(<redacted>)"

    def _payload(self) -> dict[str, object]:
        """Snapshot every canonical evidence field exactly once."""
        return {
            "accessibility_evidence_digest_sha256": self.accessibility_evidence_digest_sha256,
            "candidate_revision_sha": self.candidate_revision_sha,
            "coverage_evidence_digest_sha256": self.coverage_evidence_digest_sha256,
            "evidence_version": self.evidence_version,
            "human_review_required": self.human_review_required,
            "integration_state": self.integration_state,
            "migration_rollback_evidence_digest_sha256": self.migration_rollback_evidence_digest_sha256,
            "next_action": self.next_action,
            "operability_evidence_digest_sha256": self.operability_evidence_digest_sha256,
            "package_reproducibility_evidence_digest_sha256": self.package_reproducibility_evidence_digest_sha256,
            "provenance_digest_sha256": self.provenance_digest_sha256,
            "purpose_code": self.purpose_code,
            "recorded_at": _canonical_timestamp(self.recorded_at),
            "recovery_evidence_digest_sha256": self.recovery_evidence_digest_sha256,
            "release_authority": self.release_authority,
            "requester_actor_reference": self.requester_actor_reference,
            "review_state": self.review_state,
            "reviewed_at": _canonical_timestamp(self.reviewed_at),
            "reviewer_actor_reference": self.reviewer_actor_reference,
            "sast_evidence_digest_sha256": self.sast_evidence_digest_sha256,
            "sbom_digest_sha256": self.sbom_digest_sha256,
            "security_evidence_digest_sha256": self.security_evidence_digest_sha256,
            "source_artifact_digest_sha256": self.source_artifact_digest_sha256,
            "test_evidence_digest_sha256": self.test_evidence_digest_sha256,
        }

    def _verified_payload(self) -> dict[str, object]:
        """Return the exact validated payload snapshot or fail closed on mutation."""
        self._require_fixed_governance()
        _validate_revision(self.candidate_revision_sha)
        for field_name in _DIGEST_FIELDS:
            _validate_digest(getattr(self, field_name), field_name)
        _validate_actor_reference(self.requester_actor_reference, "requester_actor_reference")
        _validate_actor_reference(self.reviewer_actor_reference, "reviewer_actor_reference")
        _validate_timestamp(self.reviewed_at, "reviewed_at")
        _validate_timestamp(self.recorded_at, "recorded_at")
        _validate_evidence_version(self.evidence_version)

        payload = self._payload()
        _validate_revision(payload["candidate_revision_sha"])
        for field_name in _DIGEST_FIELDS:
            _validate_digest(payload[field_name], field_name)
        _validate_actor_reference(payload["requester_actor_reference"], "requester_actor_reference")
        _validate_actor_reference(payload["reviewer_actor_reference"], "reviewer_actor_reference")
        _validate_evidence_version(payload["evidence_version"])
        for field_name in (
            "purpose_code",
            "review_state",
            "integration_state",
            "release_authority",
            "next_action",
            "reviewed_at",
            "recorded_at",
        ):
            _require_exact_text(payload[field_name], field_name)

        digest = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
        with self._issuance_lock:
            issued_digest = self._issuance_digests.get(self)
        if issued_digest != digest:
            raise ValueError("release-readiness evidence was modified after issuance")
        return payload

    def canonical_document(self) -> dict[str, object]:
        """Return detached canonical release-readiness evidence."""
        return dict(self._verified_payload())

    def canonical_json(self) -> str:
        """Return deterministic JSON for the exact verified snapshot."""
        return _canonical_json(self._verified_payload())

    def sha256_digest(self) -> str:
        """Return SHA-256 over exact verified canonical JSON bytes."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_release_readiness_review_packet(**kwargs: object) -> ReleaseReadinessReviewPacket:
    """Build one non-authorizing release-readiness review packet."""
    return ReleaseReadinessReviewPacket(**kwargs)
