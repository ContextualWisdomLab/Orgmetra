"""Audited exact-revision release authorization without publication side effects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import re
from threading import RLock
from typing import Callable, ClassVar, Protocol, cast
from weakref import WeakKeyDictionary

from orgmetra_release_readiness_review import ReleaseReadinessReviewPacket

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ACTOR_PATTERN = re.compile(
    r"^actor:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_TAG_PATTERN = re.compile(r"^v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$")
_PURPOSE_CODE = "release_authorization"
_REASON_CODE = "approved_commercial_release"
_RELEASE_AUTHORITY = "authorized_for_exact_release_operation"
_PUBLICATION_STATE = "not_published"
_EVIDENCE_VERSION = 1
_MINIMUM_APPROVALS = 2
_MAX_CONTROL_AGE = timedelta(seconds=60)
_RECEIPT_CAPABILITY = object()


class ReleaseAuthorizationError(ValueError):
    """Report a fail-closed release-authorization contract violation."""


class ReleaseControlAuthority(Protocol):
    """Resolve fresh repository controls for one reviewed candidate and release tag."""

    def verify_release_controls(
        self, readiness_packet: ReleaseReadinessReviewPacket, tag_name: str
    ) -> object:
        """Return fresh control evidence for the exact candidate."""
        ...


class ReleaseAuditPort(Protocol):
    """Append immutable authorization evidence before release authority is returned."""

    def append_release_authorization(
        self, canonical_json: str, evidence_digest_sha256: str
    ) -> "ReleaseAuditReceipt":
        """Persist exact authorization evidence and return its audit envelope binding."""
        ...


def _canonical_json(payload: dict[str, object]) -> str:
    """Serialize one canonical evidence object deterministically."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _canonical_timestamp(value: datetime) -> str:
    """Render one trusted UTC timestamp as RFC 3339 text."""
    return value.isoformat().replace("+00:00", "Z")


def _require_exact_text(value: object, field_name: str) -> str:
    """Return trust-bearing text only when it is an exact built-in string."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be an exact string")
    return value


def _validate_revision(value: object, field_name: str) -> str:
    """Require one exact lower-case forty-hex Git revision."""
    text = _require_exact_text(value, field_name)
    if not _REVISION_PATTERN.fullmatch(text):
        raise ValueError(f"{field_name} must be 40 lower-case hexadecimal characters")
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
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError(f"{field_name} must be an exact built-in timezone.utc datetime")
    return value


def _validate_tag(value: object) -> str:
    """Require one canonical full-release vMAJOR.MINOR.PATCH tag."""
    text = _require_exact_text(value, "tag_name")
    if not _TAG_PATTERN.fullmatch(text):
        raise ValueError("tag_name must be canonical vMAJOR.MINOR.PATCH without prerelease metadata")
    return text


def _validate_evidence_version(value: object) -> int:
    """Require the one supported release-authorization evidence schema version."""
    if type(value) is not int or value != _EVIDENCE_VERSION:
        raise ValueError("evidence_version must be exact integer 1")
    return value


@dataclass(frozen=True, slots=True)
class ReleaseControlVerification:
    """Fresh repository-control evidence returned by the authoritative host."""

    candidate_revision_sha: str
    integrated_default_head_sha: str
    ruleset_evidence_digest_sha256: str
    required_gate_evidence_digest_sha256: str
    qualifying_independent_approval_count: int
    last_push_approved: bool
    review_threads_resolved: bool
    all_required_gates_green: bool
    routine_admin_bypass_disabled: bool
    verified_at: datetime

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Reject subtype overrides of live-control evidence semantics."""
        raise TypeError("ReleaseControlVerification is a final trust-bearing runtime type")

    def __post_init__(self) -> None:
        """Reject malformed host evidence before it reaches authorization policy."""
        _validate_revision(self.candidate_revision_sha, "candidate_revision_sha")
        _validate_revision(self.integrated_default_head_sha, "integrated_default_head_sha")
        _validate_digest(self.ruleset_evidence_digest_sha256, "ruleset_evidence_digest_sha256")
        _validate_digest(self.required_gate_evidence_digest_sha256, "required_gate_evidence_digest_sha256")
        if type(self.qualifying_independent_approval_count) is not int or self.qualifying_independent_approval_count < 0:
            raise ValueError("approval count must be an exact non-negative integer")
        for field_name in (
            "last_push_approved",
            "review_threads_resolved",
            "all_required_gates_green",
            "routine_admin_bypass_disabled",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ValueError(f"{field_name} must be an exact boolean")
        _validate_timestamp(self.verified_at, "verified_at")

    def snapshot(self) -> dict[str, object]:
        """Read every control field once for subsequent validation and hashing."""
        return {
            "all_required_gates_green": self.all_required_gates_green,
            "candidate_revision_sha": self.candidate_revision_sha,
            "integrated_default_head_sha": self.integrated_default_head_sha,
            "last_push_approved": self.last_push_approved,
            "qualifying_independent_approval_count": self.qualifying_independent_approval_count,
            "required_gate_evidence_digest_sha256": self.required_gate_evidence_digest_sha256,
            "review_threads_resolved": self.review_threads_resolved,
            "routine_admin_bypass_disabled": self.routine_admin_bypass_disabled,
            "ruleset_evidence_digest_sha256": self.ruleset_evidence_digest_sha256,
            "verified_at": self.verified_at,
        }


@dataclass(frozen=True, slots=True)
class ReleaseAuditReceipt:
    """Host-owned immutable-audit binding for one authorization evidence object."""

    authorization_evidence_digest_sha256: str
    audit_event_envelope_digest_sha256: str
    recorded_at: datetime

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Reject subtype overrides of audit-receipt semantics."""
        raise TypeError("ReleaseAuditReceipt is a final trust-bearing runtime type")

    def __post_init__(self) -> None:
        """Reject malformed durable-audit evidence."""
        _validate_digest(self.authorization_evidence_digest_sha256, "authorization_evidence_digest_sha256")
        _validate_digest(self.audit_event_envelope_digest_sha256, "audit_event_envelope_digest_sha256")
        _validate_timestamp(self.recorded_at, "recorded_at")

    def snapshot(self) -> dict[str, object]:
        """Read every audit field once before matching it to authorization evidence."""
        return {
            "authorization_evidence_digest_sha256": self.authorization_evidence_digest_sha256,
            "audit_event_envelope_digest_sha256": self.audit_event_envelope_digest_sha256,
            "recorded_at": self.recorded_at,
        }


@dataclass(frozen=True, slots=True, weakref_slot=True, eq=False, repr=False, init=False)
class ReleaseAuthorizationReceipt:
    """Factory-issued authority for one exact future release operation, not publication."""

    candidate_revision_sha: str
    readiness_evidence_digest_sha256: str
    control_verification_digest_sha256: str
    audit_event_envelope_digest_sha256: str
    tag_name: str
    release_actor_reference: str
    authorized_at: datetime
    audit_recorded_at: datetime
    purpose_code: str
    reason_code: str
    evidence_version: int
    release_authority: str
    publication_state: str

    _issuance_digests: ClassVar[WeakKeyDictionary["ReleaseAuthorizationReceipt", str]] = WeakKeyDictionary()
    _issuance_lock: ClassVar[RLock] = RLock()

    def __init__(
        self,
        *,
        candidate_revision_sha: str | None = None,
        readiness_evidence_digest_sha256: str | None = None,
        control_verification_digest_sha256: str | None = None,
        audit_event_envelope_digest_sha256: str | None = None,
        tag_name: str | None = None,
        release_actor_reference: str | None = None,
        authorized_at: datetime | None = None,
        audit_recorded_at: datetime | None = None,
        _capability: object | None = None,
    ) -> None:
        """Allow construction only to the audited authorization factory."""
        if _capability is not _RECEIPT_CAPABILITY:
            raise TypeError("ReleaseAuthorizationReceipt must be factory-issued")
        values = {
            "candidate_revision_sha": candidate_revision_sha,
            "readiness_evidence_digest_sha256": readiness_evidence_digest_sha256,
            "control_verification_digest_sha256": control_verification_digest_sha256,
            "audit_event_envelope_digest_sha256": audit_event_envelope_digest_sha256,
            "tag_name": tag_name,
            "release_actor_reference": release_actor_reference,
            "authorized_at": authorized_at,
            "audit_recorded_at": audit_recorded_at,
            "purpose_code": _PURPOSE_CODE,
            "reason_code": _REASON_CODE,
            "evidence_version": _EVIDENCE_VERSION,
            "release_authority": _RELEASE_AUTHORITY,
            "publication_state": _PUBLICATION_STATE,
        }
        for field_name, value in values.items():
            object.__setattr__(self, field_name, value)
        payload = self._payload()
        digest = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
        with self._issuance_lock:
            self._issuance_digests[self] = digest

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Reject subtype-based overrides of the release-authority receipt."""
        raise TypeError("ReleaseAuthorizationReceipt is a final trust-bearing runtime type")

    def __repr__(self) -> str:
        """Return a correlation-safe routine representation."""
        return "ReleaseAuthorizationReceipt(<redacted>)"

    def _payload(self) -> dict[str, object]:
        """Snapshot every canonical receipt field exactly once."""
        return {
            "audit_event_envelope_digest_sha256": self.audit_event_envelope_digest_sha256,
            "audit_recorded_at": _canonical_timestamp(self.audit_recorded_at),
            "authorized_at": _canonical_timestamp(self.authorized_at),
            "candidate_revision_sha": self.candidate_revision_sha,
            "control_verification_digest_sha256": self.control_verification_digest_sha256,
            "evidence_version": self.evidence_version,
            "publication_state": self.publication_state,
            "purpose_code": self.purpose_code,
            "readiness_evidence_digest_sha256": self.readiness_evidence_digest_sha256,
            "reason_code": self.reason_code,
            "release_actor_reference": self.release_actor_reference,
            "release_authority": self.release_authority,
            "tag_name": self.tag_name,
        }

    def _verified_payload(self) -> dict[str, object]:
        """Return the exact issued payload or fail closed after receipt mutation."""
        payload = self._payload()
        digest = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
        with self._issuance_lock:
            issued_digest = self._issuance_digests.get(self)
        if issued_digest != digest:
            raise ValueError("release-authorization receipt was modified after issuance")
        return payload

    def canonical_document(self) -> dict[str, object]:
        """Return detached canonical release-authorization evidence."""
        return dict(self._verified_payload())

    def canonical_json(self) -> str:
        """Return deterministic JSON for the exact issued receipt."""
        return _canonical_json(self._verified_payload())

    def sha256_digest(self) -> str:
        """Return SHA-256 over exact issued canonical JSON bytes."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _validate_control_snapshot(payload: dict[str, object], candidate_revision_sha: str) -> None:
    """Apply Orgmetra's acquisition-grade release policy to one fresh snapshot."""
    try:
        candidate = _validate_revision(payload["candidate_revision_sha"], "candidate_revision_sha")
        integrated = _validate_revision(payload["integrated_default_head_sha"], "integrated_default_head_sha")
        _validate_digest(payload["ruleset_evidence_digest_sha256"], "ruleset_evidence_digest_sha256")
        _validate_digest(payload["required_gate_evidence_digest_sha256"], "required_gate_evidence_digest_sha256")
        _validate_timestamp(payload["verified_at"], "verified_at")
    except (KeyError, ValueError) as exc:
        raise ReleaseAuthorizationError("ReleaseControlVerification contains invalid trust evidence") from exc
    approvals = payload.get("qualifying_independent_approval_count")
    if type(approvals) is not int or approvals < _MINIMUM_APPROVALS:
        raise ReleaseAuthorizationError("release authorization requires at least two qualifying independent approvals")
    if candidate != candidate_revision_sha:
        raise ReleaseAuthorizationError("verified candidate revision does not match readiness evidence")
    if integrated != candidate_revision_sha:
        raise ReleaseAuthorizationError("candidate is not the freshly integrated default-branch head")
    if payload.get("last_push_approved") is not True:
        raise ReleaseAuthorizationError("release authorization requires approval after the last push")
    if payload.get("review_threads_resolved") is not True:
        raise ReleaseAuthorizationError("release authorization requires all review threads to be resolved")
    if payload.get("all_required_gates_green") is not True:
        raise ReleaseAuthorizationError("release authorization requires every applicable required gate to be GREEN")
    if payload.get("routine_admin_bypass_disabled") is not True:
        raise ReleaseAuthorizationError("release authorization requires routine administrator bypass to be disabled")


def authorize_release_candidate(
    *,
    readiness_packet: object,
    tag_name: object,
    release_actor_reference: object,
    authority: ReleaseControlAuthority,
    audit_port: ReleaseAuditPort,
    clock: Callable[[], object] = lambda: datetime.now(timezone.utc),
) -> ReleaseAuthorizationReceipt:
    """Authorize one exact release operation after fresh controls and immutable audit."""
    if type(readiness_packet) is not ReleaseReadinessReviewPacket:
        raise ReleaseAuthorizationError("readiness_packet must be an exact ReleaseReadinessReviewPacket")
    try:
        tag = _validate_tag(tag_name)
        release_actor = _validate_actor_reference(release_actor_reference, "release_actor_reference")
    except ValueError as exc:
        raise ReleaseAuthorizationError(str(exc)) from exc

    readiness_json = readiness_packet.canonical_json()
    readiness_document = json.loads(readiness_json)
    readiness_digest = sha256(readiness_json.encode("utf-8")).hexdigest()
    candidate_revision = readiness_document["candidate_revision_sha"]
    if release_actor in {
        readiness_document.get("requester_actor_reference"),
        readiness_document.get("reviewer_actor_reference"),
    }:
        raise ReleaseAuthorizationError("release actor must differ from readiness requester and reviewer")

    verification = authority.verify_release_controls(readiness_packet, tag)
    if type(verification) is not ReleaseControlVerification:
        raise ReleaseAuthorizationError("authority must return an exact ReleaseControlVerification")
    control_snapshot = verification.snapshot()
    _validate_control_snapshot(control_snapshot, candidate_revision)
    verified_at = cast(datetime, control_snapshot["verified_at"])

    try:
        authorized_at = _validate_timestamp(clock(), "authorized_at")
    except ValueError as exc:
        raise ReleaseAuthorizationError(str(exc)) from exc
    if authorized_at < verified_at:
        raise ReleaseAuthorizationError("authorized_at cannot precede fresh control verification")
    if authorized_at - verified_at > _MAX_CONTROL_AGE:
        raise ReleaseAuthorizationError("fresh control verification is stale for release authorization")

    control_document = dict(control_snapshot)
    control_document["verified_at"] = _canonical_timestamp(verified_at)
    control_json = _canonical_json(control_document)
    control_digest = sha256(control_json.encode("utf-8")).hexdigest()
    evidence = {
        "authorized_at": _canonical_timestamp(authorized_at),
        "candidate_revision_sha": candidate_revision,
        "control_verification_digest_sha256": control_digest,
        "evidence_version": _EVIDENCE_VERSION,
        "publication_state": _PUBLICATION_STATE,
        "purpose_code": _PURPOSE_CODE,
        "readiness_evidence_digest_sha256": readiness_digest,
        "reason_code": _REASON_CODE,
        "release_actor_reference": release_actor,
        "release_authority": _RELEASE_AUTHORITY,
        "tag_name": tag,
    }
    evidence_json = _canonical_json(evidence)
    evidence_digest = sha256(evidence_json.encode("utf-8")).hexdigest()
    audit_receipt = audit_port.append_release_authorization(evidence_json, evidence_digest)
    if type(audit_receipt) is not ReleaseAuditReceipt:
        raise ReleaseAuthorizationError("audit_port must return an exact ReleaseAuditReceipt")
    audit_snapshot = audit_receipt.snapshot()
    try:
        audit_digest = _validate_digest(
            audit_snapshot["authorization_evidence_digest_sha256"],
            "authorization_evidence_digest_sha256",
        )
        audit_envelope_digest = _validate_digest(
            audit_snapshot["audit_event_envelope_digest_sha256"],
            "audit_event_envelope_digest_sha256",
        )
        audit_recorded_at = _validate_timestamp(audit_snapshot["recorded_at"], "audit recorded_at")
    except (KeyError, ValueError) as exc:
        raise ReleaseAuthorizationError("audit receipt contains invalid trust evidence") from exc
    if audit_digest != evidence_digest:
        raise ReleaseAuthorizationError("audit receipt digest does not bind the exact authorization evidence")
    if audit_recorded_at < authorized_at:
        raise ReleaseAuthorizationError("audit recorded_at cannot precede release authorization")
    if audit_recorded_at - verified_at > _MAX_CONTROL_AGE:
        raise ReleaseAuthorizationError("fresh control verification became stale before immutable audit completed")

    return ReleaseAuthorizationReceipt(
        candidate_revision_sha=candidate_revision,
        readiness_evidence_digest_sha256=readiness_digest,
        control_verification_digest_sha256=control_digest,
        audit_event_envelope_digest_sha256=audit_envelope_digest,
        tag_name=tag,
        release_actor_reference=release_actor,
        authorized_at=authorized_at,
        audit_recorded_at=audit_recorded_at,
        _capability=_RECEIPT_CAPABILITY,
    )
