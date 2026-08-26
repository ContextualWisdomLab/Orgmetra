"""Publish one exact authorized release with reconciliation-only ambiguity handling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import re
from threading import RLock
from typing import Callable, ClassVar, Protocol, cast
from weakref import WeakKeyDictionary

from orgmetra_release_authorization import ReleaseAuthorizationReceipt

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_TAG_PATTERN = re.compile(r"^v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$")
_PUBLICATION_REFERENCE_PATTERN = re.compile(
    r"^release_publication:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_AUTHORITY_STATE = "authorized_for_exact_release_operation"
_PARENT_PUBLICATION_STATE = "not_published"
_PUBLICATION_STATE = "published"
_CONSUMPTION_STATE = "consumed_once"
_PURPOSE_CODE = "release_publication"
_REASON_CODE = "authorized_commercial_release"
_EVIDENCE_VERSION = 1
_MAX_AUTHORIZATION_AGE = timedelta(seconds=60)
_RECEIPT_CAPABILITY = object()


class ReleasePublicationError(ValueError):
    """Report a fail-closed release-publication contract violation."""


class ReleasePublicationIndeterminateError(ReleasePublicationError):
    """Report an ambiguous prior side effect that must not be republished."""


class ReleasePublicationPort(Protocol):
    """Publish at most once under one idempotency correlation and support lookup-only recovery."""

    def publish_release(
        self,
        *,
        candidate_revision_sha: str,
        tag_name: str,
        publication_reference: str,
        authorization_evidence_digest_sha256: str,
    ) -> object:
        """Publish the exact authorized release once and return durable host evidence."""
        ...

    def reconcile_release(
        self,
        *,
        candidate_revision_sha: str,
        tag_name: str,
        publication_reference: str,
        authorization_evidence_digest_sha256: str,
    ) -> object | None:
        """Look up an existing publication without creating or republishing it."""
        ...


def _canonical_json(payload: dict[str, object]) -> str:
    """Serialize one evidence object deterministically."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _canonical_timestamp(value: datetime) -> str:
    """Render one trusted UTC timestamp as RFC 3339 text."""
    return value.isoformat().replace("+00:00", "Z")


def _exact_text(value: object, field_name: str) -> str:
    """Require exact built-in text before regex, equality, or serialization."""
    if type(value) is not str:
        raise ReleasePublicationError(f"{field_name} must be an exact string")
    return value


def _digest(value: object, field_name: str) -> str:
    """Require exact lower-case SHA-256 evidence text."""
    text = _exact_text(value, field_name)
    if not _SHA256_PATTERN.fullmatch(text):
        raise ReleasePublicationError(f"{field_name} must be lower-case SHA-256 hex")
    return text


def _revision(value: object, field_name: str) -> str:
    """Require one exact lower-case forty-hex Git revision."""
    text = _exact_text(value, field_name)
    if not _REVISION_PATTERN.fullmatch(text):
        raise ReleasePublicationError(f"{field_name} must be 40 lower-case hexadecimal characters")
    return text


def _tag(value: object) -> str:
    """Require one canonical full-release tag."""
    text = _exact_text(value, "tag_name")
    if not _TAG_PATTERN.fullmatch(text):
        raise ReleasePublicationError("tag_name must be canonical vMAJOR.MINOR.PATCH")
    return text


def _publication_reference(value: object) -> str:
    """Require an opaque packet-owned UUIDv4 publication correlation."""
    text = _exact_text(value, "publication_reference")
    if not _PUBLICATION_REFERENCE_PATTERN.fullmatch(text):
        raise ReleasePublicationError(
            "publication_reference must be release_publication:<canonical-uuidv4>"
        )
    return text


def _timestamp(value: object, field_name: str) -> datetime:
    """Require one exact built-in timezone.utc timestamp."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ReleasePublicationError(f"{field_name} must be an exact built-in timezone.utc datetime")
    return value


def _parse_canonical_timestamp(value: object, field_name: str) -> datetime:
    """Parse one parent canonical UTC timestamp without accepting alternate forms."""
    text = _exact_text(value, field_name)
    if not text.endswith("Z"):
        raise ReleasePublicationError(f"{field_name} must be canonical RFC 3339 UTC text")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise ReleasePublicationError(f"{field_name} must be canonical RFC 3339 UTC text") from exc
    if _canonical_timestamp(parsed) != text:
        raise ReleasePublicationError(f"{field_name} must be canonical RFC 3339 UTC text")
    return parsed


@dataclass(frozen=True, slots=True)
class ReleasePlatformReceipt:
    """Host-owned durable evidence that one exact release was published and audited."""

    authorization_evidence_digest_sha256: str
    candidate_revision_sha: str
    tag_name: str
    publication_reference: str
    platform_release_digest_sha256: str
    audit_event_envelope_digest_sha256: str
    published_at: datetime

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Reject subtype overrides of host publication-evidence semantics."""
        raise TypeError("ReleasePlatformReceipt is a final trust-bearing runtime type")

    def __post_init__(self) -> None:
        """Reject malformed publication evidence at the host boundary."""
        _digest(self.authorization_evidence_digest_sha256, "authorization_evidence_digest_sha256")
        _revision(self.candidate_revision_sha, "candidate_revision_sha")
        _tag(self.tag_name)
        _publication_reference(self.publication_reference)
        _digest(self.platform_release_digest_sha256, "platform_release_digest_sha256")
        _digest(self.audit_event_envelope_digest_sha256, "audit_event_envelope_digest_sha256")
        _timestamp(self.published_at, "published_at")

    def snapshot(self) -> dict[str, object]:
        """Read every trust-bearing host field once for validation."""
        return {
            "audit_event_envelope_digest_sha256": self.audit_event_envelope_digest_sha256,
            "authorization_evidence_digest_sha256": self.authorization_evidence_digest_sha256,
            "candidate_revision_sha": self.candidate_revision_sha,
            "platform_release_digest_sha256": self.platform_release_digest_sha256,
            "publication_reference": self.publication_reference,
            "published_at": self.published_at,
            "tag_name": self.tag_name,
        }


@dataclass(frozen=True, slots=True, weakref_slot=True, eq=False, repr=False, init=False)
class ReleasePublicationReceipt:
    """Factory-issued canonical evidence for one completed exact release publication."""

    authorization_evidence_digest_sha256: str
    candidate_revision_sha: str
    tag_name: str
    publication_reference: str
    platform_release_digest_sha256: str
    audit_event_envelope_digest_sha256: str
    publication_started_at: datetime
    published_at: datetime
    purpose_code: str
    reason_code: str
    evidence_version: int
    publication_state: str
    authorization_consumption_state: str

    _issuance_digests: ClassVar[WeakKeyDictionary["ReleasePublicationReceipt", str]] = WeakKeyDictionary()
    _issuance_lock: ClassVar[RLock] = RLock()

    def __init__(
        self,
        *,
        authorization_evidence_digest_sha256: str,
        candidate_revision_sha: str,
        tag_name: str,
        publication_reference: str,
        platform_release_digest_sha256: str,
        audit_event_envelope_digest_sha256: str,
        publication_started_at: datetime,
        published_at: datetime,
        _capability: object | None = None,
    ) -> None:
        """Allow construction only after successful publication-evidence verification."""
        if _capability is not _RECEIPT_CAPABILITY:
            raise TypeError("ReleasePublicationReceipt must be factory-issued")
        values = {
            "authorization_evidence_digest_sha256": authorization_evidence_digest_sha256,
            "candidate_revision_sha": candidate_revision_sha,
            "tag_name": tag_name,
            "publication_reference": publication_reference,
            "platform_release_digest_sha256": platform_release_digest_sha256,
            "audit_event_envelope_digest_sha256": audit_event_envelope_digest_sha256,
            "publication_started_at": publication_started_at,
            "published_at": published_at,
            "purpose_code": _PURPOSE_CODE,
            "reason_code": _REASON_CODE,
            "evidence_version": _EVIDENCE_VERSION,
            "publication_state": _PUBLICATION_STATE,
            "authorization_consumption_state": _CONSUMPTION_STATE,
        }
        for field_name, value in values.items():
            object.__setattr__(self, field_name, value)
        payload = self._payload()
        with self._issuance_lock:
            self._issuance_digests[self] = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Reject subtype overrides of canonical publication evidence."""
        raise TypeError("ReleasePublicationReceipt is a final trust-bearing runtime type")

    def __repr__(self) -> str:
        """Return a correlation-safe routine representation."""
        return "ReleasePublicationReceipt(<redacted>)"

    def _payload(self) -> dict[str, object]:
        """Snapshot every canonical publication field exactly once."""
        return {
            "audit_event_envelope_digest_sha256": self.audit_event_envelope_digest_sha256,
            "authorization_consumption_state": self.authorization_consumption_state,
            "authorization_evidence_digest_sha256": self.authorization_evidence_digest_sha256,
            "candidate_revision_sha": self.candidate_revision_sha,
            "evidence_version": self.evidence_version,
            "platform_release_digest_sha256": self.platform_release_digest_sha256,
            "publication_reference": self.publication_reference,
            "publication_started_at": _canonical_timestamp(self.publication_started_at),
            "publication_state": self.publication_state,
            "published_at": _canonical_timestamp(self.published_at),
            "purpose_code": self.purpose_code,
            "reason_code": self.reason_code,
            "tag_name": self.tag_name,
        }

    def _verified_payload(self) -> dict[str, object]:
        """Return the exact issued payload or fail closed after mutation."""
        payload = self._payload()
        digest = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
        with self._issuance_lock:
            issued_digest = self._issuance_digests.get(self)
        if digest != issued_digest:
            raise ValueError("release-publication receipt was modified after issuance")
        return payload

    def canonical_document(self) -> dict[str, object]:
        """Return detached canonical publication evidence."""
        return dict(self._verified_payload())

    def canonical_json(self) -> str:
        """Return deterministic JSON for exact issued publication evidence."""
        return _canonical_json(self._verified_payload())

    def sha256_digest(self) -> str:
        """Return SHA-256 over exact issued canonical JSON bytes."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _authorization_snapshot(receipt: ReleaseAuthorizationReceipt) -> tuple[dict[str, object], str]:
    """Verify and snapshot parent authorization evidence exactly once."""
    try:
        canonical_json = receipt.canonical_json()
        document = json.loads(canonical_json)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ReleasePublicationError("release authorization evidence is invalid") from exc
    if type(document) is not dict:
        raise ReleasePublicationError("release authorization evidence must be one canonical object")
    if document.get("release_authority") != _AUTHORITY_STATE:
        raise ReleasePublicationError("release authorization does not grant exact release authority")
    if document.get("publication_state") != _PARENT_PUBLICATION_STATE:
        raise ReleasePublicationError("release authorization has already been consumed or published")
    if document.get("evidence_version") != _EVIDENCE_VERSION:
        raise ReleasePublicationError("release authorization evidence_version must be exact integer 1")
    _revision(document.get("candidate_revision_sha"), "candidate_revision_sha")
    _tag(document.get("tag_name"))
    _parse_canonical_timestamp(document.get("audit_recorded_at"), "audit_recorded_at")
    return document, sha256(canonical_json.encode("utf-8")).hexdigest()


def _matching_platform_snapshot(
    receipt: object,
    *,
    authorization_digest: str,
    candidate_revision: str,
    tag_name: str,
    publication_reference: str,
    publication_started_at: datetime,
) -> dict[str, object] | None:
    """Return validated exact-scope host evidence, or None when reconciliation is required."""
    if type(receipt) is not ReleasePlatformReceipt:
        return None
    snapshot = receipt.snapshot()
    try:
        bound_authorization = _digest(
            snapshot.get("authorization_evidence_digest_sha256"),
            "authorization_evidence_digest_sha256",
        )
        candidate = _revision(snapshot.get("candidate_revision_sha"), "candidate_revision_sha")
        tag = _tag(snapshot.get("tag_name"))
        correlation = _publication_reference(snapshot.get("publication_reference"))
        _digest(snapshot.get("platform_release_digest_sha256"), "platform_release_digest_sha256")
        _digest(snapshot.get("audit_event_envelope_digest_sha256"), "audit_event_envelope_digest_sha256")
        published_at = _timestamp(snapshot.get("published_at"), "published_at")
    except ReleasePublicationError:
        return None
    if (
        bound_authorization != authorization_digest
        or candidate != candidate_revision
        or tag != tag_name
        or correlation != publication_reference
        or published_at < publication_started_at
    ):
        return None
    return snapshot


def _reconcile_or_raise(
    publisher: ReleasePublicationPort,
    *,
    authorization_digest: str,
    candidate_revision: str,
    tag_name: str,
    publication_reference: str,
    publication_started_at: datetime,
) -> dict[str, object]:
    """Resolve ambiguous publication by lookup only; never invoke publication twice."""
    try:
        reconciled = publisher.reconcile_release(
            candidate_revision_sha=candidate_revision,
            tag_name=tag_name,
            publication_reference=publication_reference,
            authorization_evidence_digest_sha256=authorization_digest,
        )
    except Exception as exc:
        raise ReleasePublicationIndeterminateError(
            "release publication outcome is indeterminate; do not republish"
        ) from exc
    snapshot = _matching_platform_snapshot(
        reconciled,
        authorization_digest=authorization_digest,
        candidate_revision=candidate_revision,
        tag_name=tag_name,
        publication_reference=publication_reference,
        publication_started_at=publication_started_at,
    )
    if snapshot is None:
        raise ReleasePublicationIndeterminateError(
            "release publication outcome is indeterminate; do not republish"
        )
    return snapshot


def publish_authorized_release(
    *,
    authorization_receipt: object,
    publication_reference: object,
    publisher: ReleasePublicationPort,
    clock: Callable[[], object] = lambda: datetime.now(timezone.utc),
) -> ReleasePublicationReceipt:
    """Consume one exact authorization and publish at most once with lookup-only recovery."""
    if type(authorization_receipt) is not ReleaseAuthorizationReceipt:
        raise ReleasePublicationError("authorization_receipt must be an exact ReleaseAuthorizationReceipt")
    correlation = _publication_reference(publication_reference)
    authorization_document, authorization_digest = _authorization_snapshot(authorization_receipt)
    candidate_revision = _revision(authorization_document["candidate_revision_sha"], "candidate_revision_sha")
    tag_name = _tag(authorization_document["tag_name"])
    audit_recorded_at = _parse_canonical_timestamp(
        authorization_document["audit_recorded_at"], "audit_recorded_at"
    )
    try:
        publication_started_at = _timestamp(clock(), "publication_started_at")
    except Exception as exc:
        if isinstance(exc, ReleasePublicationError):
            raise
        raise ReleasePublicationError("publication clock failed before release side effects") from exc
    if publication_started_at < audit_recorded_at:
        raise ReleasePublicationError("publication_started_at cannot precede authorization audit")
    if publication_started_at - audit_recorded_at > _MAX_AUTHORIZATION_AGE:
        raise ReleasePublicationError("release authorization is stale for publication")

    publish_kwargs = {
        "candidate_revision_sha": candidate_revision,
        "tag_name": tag_name,
        "publication_reference": correlation,
        "authorization_evidence_digest_sha256": authorization_digest,
    }
    try:
        immediate = publisher.publish_release(**publish_kwargs)
    except Exception:
        platform_snapshot = _reconcile_or_raise(
            publisher,
            authorization_digest=authorization_digest,
            candidate_revision=candidate_revision,
            tag_name=tag_name,
            publication_reference=correlation,
            publication_started_at=publication_started_at,
        )
    else:
        platform_snapshot = _matching_platform_snapshot(
            immediate,
            authorization_digest=authorization_digest,
            candidate_revision=candidate_revision,
            tag_name=tag_name,
            publication_reference=correlation,
            publication_started_at=publication_started_at,
        )
        if platform_snapshot is None:
            platform_snapshot = _reconcile_or_raise(
                publisher,
                authorization_digest=authorization_digest,
                candidate_revision=candidate_revision,
                tag_name=tag_name,
                publication_reference=correlation,
                publication_started_at=publication_started_at,
            )

    return ReleasePublicationReceipt(
        authorization_evidence_digest_sha256=authorization_digest,
        candidate_revision_sha=candidate_revision,
        tag_name=tag_name,
        publication_reference=correlation,
        platform_release_digest_sha256=cast(str, platform_snapshot["platform_release_digest_sha256"]),
        audit_event_envelope_digest_sha256=cast(str, platform_snapshot["audit_event_envelope_digest_sha256"]),
        publication_started_at=publication_started_at,
        published_at=cast(datetime, platform_snapshot["published_at"]),
        _capability=_RECEIPT_CAPABILITY,
    )
