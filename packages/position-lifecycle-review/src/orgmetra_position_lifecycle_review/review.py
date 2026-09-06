"""Governed, value-minimized evidence for reviewing a Position lifecycle change.

This package deliberately does not mutate Position truth.  It records one human
review of a proposed lifecycle transition and remains fail-closed until an
Orgmetra authoritative host re-resolves current Position and Assignment truth,
re-authorizes actors, and persists the later mutation with immutable audit/outbox.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import re
from threading import RLock
import weakref
from uuid import UUID

_MAX_UUID_INT = (1 << 128) - 1
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_STATUSES = frozenset({"active", "open", "closed", "frozen", "abolished"})
_REASONS = frozenset({"temporary_freeze", "position_reactivation", "position_closure", "position_abolition"})
_OUTCOMES = frozenset({"approved_for_authoritative_resolution", "rejected"})
_ALLOWED_TRANSITIONS = {
    "open": frozenset({"active", "frozen", "closed", "abolished"}),
    "active": frozenset({"frozen", "closed", "abolished"}),
    "frozen": frozenset({"open", "active", "closed", "abolished"}),
    "closed": frozenset({"open", "abolished"}),
    "abolished": frozenset(),
}
_EXPECTED_REASON = {
    "active": "position_reactivation",
    "open": "position_reactivation",
    "frozen": "temporary_freeze",
    "closed": "position_closure",
    "abolished": "position_abolition",
}
_LOCK = RLock()
_ISSUANCE_DIGESTS: dict[int, str] = {}
_REFERENCE_BINDINGS: dict[tuple[UUID, UUID], tuple[str, int]] = {}


def _require_operational_uuid(field_name: str, value: object) -> UUID:
    """Return one exact operational UUID while rejecting protocol sentinels."""
    if type(value) is not UUID or value.int in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be an operational UUID.")
    return value


def _require_uuid4(field_name: str, value: object) -> UUID:
    """Return one exact UUIDv4 owned by this evidence packet."""
    if type(value) is not UUID or value.version != 4:
        raise ValueError(f"{field_name} must be a UUIDv4.")
    return value


def _require_text(field_name: str, value: object, allowed: frozenset[str]) -> str:
    """Require exact built-in governance text before membership evaluation."""
    if type(value) is not str:
        raise TypeError(f"{field_name} must be exact built-in str.")
    if value not in allowed:
        raise ValueError(f"{field_name} is not in the governed vocabulary.")
    return value


def _require_digest(field_name: str, value: object) -> str:
    """Require the lowercase textual form of one SHA-256 digest."""
    if type(value) is not str:
        raise TypeError(f"{field_name} must be exact built-in str.")
    if _SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest.")
    return value


def _require_actor_reference(field_name: str, value: object) -> str:
    """Require one Orgmetra-local pseudonymous actor UUIDv4 correlation."""
    if type(value) is not str or not value.startswith("actor:"):
        raise ValueError(f"{field_name} must be an actor: UUIDv4 correlation.")
    suffix = value.removeprefix("actor:")
    try:
        parsed = UUID(suffix)
    except ValueError as error:
        raise ValueError(f"{field_name} must be an actor: UUIDv4 correlation.") from error
    if parsed.version != 4 or str(parsed) != suffix:
        raise ValueError(f"{field_name} must be an actor: UUIDv4 correlation.")
    return value


def _require_utc(field_name: str, value: object) -> datetime:
    """Require an exact built-in UTC datetime already detached from caller timezone code."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError(f"{field_name} must be an exact UTC datetime.")
    return value


def _utc_text(value: datetime) -> str:
    """Return deterministic RFC 3339-compatible UTC text."""
    return value.isoformat().replace("+00:00", "Z")


def _canonical_bytes(document: dict[str, object]) -> bytes:
    """Serialize one canonical evidence document deterministically."""
    return json.dumps(document, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode("utf-8")


def _release_binding(object_id: int, key: tuple[UUID, UUID], digest: str) -> None:
    """Release one process-local issuance/reference binding after packet collection."""
    with _LOCK:
        _ISSUANCE_DIGESTS.pop(object_id, None)
        bound_digest, count = _REFERENCE_BINDINGS[key]
        if bound_digest != digest:
            raise AssertionError("reference binding digest drifted from its issuance")
        if count == 1:
            del _REFERENCE_BINDINGS[key]
        else:
            _REFERENCE_BINDINGS[key] = (digest, count - 1)


@dataclass(frozen=True, slots=True, weakref_slot=True)
class PositionLifecycleChangeReviewPacket:
    """Human-reviewed, non-authorizing evidence for one Position lifecycle proposal."""

    tenant_record_id: UUID
    position_record_id: UUID
    position_lifecycle_change_reference: UUID
    current_status_code: str
    proposed_status_code: str
    effective_on: date
    position_snapshot_digest_sha256: str
    assignment_snapshot_digest_sha256: str
    requester_actor_reference: str
    reviewer_actor_reference: str
    reason_code: str
    review_outcome_code: str
    evidence_version: int
    reviewed_at: datetime
    recorded_at: datetime

    def __post_init__(self) -> None:
        """Validate reviewed evidence and seal live correlation semantics."""
        _require_operational_uuid("tenant_record_id", self.tenant_record_id)
        _require_operational_uuid("position_record_id", self.position_record_id)
        _require_uuid4("position_lifecycle_change_reference", self.position_lifecycle_change_reference)
        current = _require_text("current_status_code", self.current_status_code, _STATUSES)
        proposed = _require_text("proposed_status_code", self.proposed_status_code, _STATUSES)
        reason = _require_text("reason_code", self.reason_code, _REASONS)
        _require_text("review_outcome_code", self.review_outcome_code, _OUTCOMES)
        if proposed not in _ALLOWED_TRANSITIONS[current]:
            raise ValueError("proposed_status_code is not an allowed reviewed transition from current_status_code.")
        if reason != _EXPECTED_REASON[proposed]:
            raise ValueError("reason_code does not match the proposed Position lifecycle state.")
        if type(self.effective_on) is not date:
            raise TypeError("effective_on must be an exact business date.")
        _require_digest("position_snapshot_digest_sha256", self.position_snapshot_digest_sha256)
        _require_digest("assignment_snapshot_digest_sha256", self.assignment_snapshot_digest_sha256)
        requester = _require_actor_reference("requester_actor_reference", self.requester_actor_reference)
        reviewer = _require_actor_reference("reviewer_actor_reference", self.reviewer_actor_reference)
        if requester == reviewer:
            raise ValueError("requester and reviewer must be distinct pseudonymous actors.")
        if type(self.evidence_version) is not int or self.evidence_version != 1:
            raise ValueError("evidence_version must be exact integer 1.")
        reviewed_at = _require_utc("reviewed_at", self.reviewed_at)
        recorded_at = _require_utc("recorded_at", self.recorded_at)
        if recorded_at < reviewed_at:
            raise ValueError("recorded_at must be at or after reviewed_at.")

        document = self._payload()
        digest = sha256(_canonical_bytes(document)).hexdigest()
        key = (self.tenant_record_id, self.position_lifecycle_change_reference)
        with _LOCK:
            existing = _REFERENCE_BINDINGS.get(key)
            if existing is None:
                _REFERENCE_BINDINGS[key] = (digest, 1)
            else:
                existing_digest, count = existing
                if existing_digest != digest:
                    raise ValueError("position lifecycle change reference is already bound to conflicting live evidence.")
                _REFERENCE_BINDINGS[key] = (digest, count + 1)
            _ISSUANCE_DIGESTS[id(self)] = digest
        weakref.finalize(self, _release_binding, id(self), key, digest)

    def _payload(self) -> dict[str, object]:
        """Return the complete value-minimized canonical evidence snapshot."""
        next_action = (
            "Do not apply the proposed Position lifecycle change."
            if self.review_outcome_code == "rejected"
            else (
                "Re-resolve tenant-qualified Position and Assignment truth at the requested business/system "
                "coordinate; require authoritative actor separation, reviewed evidence, staffing safety, "
                "and immutable audit/outbox before any lifecycle mutation."
            )
        )
        return {
            "assignment_snapshot_digest_sha256": self.assignment_snapshot_digest_sha256,
            "current_status_code": self.current_status_code,
            "decision_authority": "human_review_only",
            "effective_on": self.effective_on.isoformat(),
            "evidence_version": self.evidence_version,
            "mutation_state": "not_authorized_to_apply",
            "next_action": next_action,
            "position_lifecycle_change_reference": str(self.position_lifecycle_change_reference),
            "position_record_id": str(self.position_record_id),
            "position_snapshot_digest_sha256": self.position_snapshot_digest_sha256,
            "proposed_status_code": self.proposed_status_code,
            "reason_code": self.reason_code,
            "recorded_at": _utc_text(self.recorded_at),
            "requester_actor_reference": self.requester_actor_reference,
            "review_outcome_code": self.review_outcome_code,
            "review_state": "human_reviewed",
            "reviewed_at": _utc_text(self.reviewed_at),
            "reviewer_actor_reference": self.reviewer_actor_reference,
            "scope_verification_state": "requires_authoritative_resolution",
            "tenant_record_id": str(self.tenant_record_id),
        }

    def canonical_document(self) -> dict[str, object]:
        """Return the same snapshot whose digest remains bound to issuance."""
        document = self._payload()
        digest = sha256(_canonical_bytes(document)).hexdigest()
        with _LOCK:
            issued_digest = _ISSUANCE_DIGESTS.get(id(self))
        if issued_digest != digest:
            raise ValueError("position lifecycle review evidence changed after issuance.")
        return document

    def canonical_json(self) -> str:
        """Return deterministic canonical JSON for immutable audit correlation."""
        return _canonical_bytes(self.canonical_document()).decode("utf-8")

    def content_digest(self) -> str:
        """Return SHA-256 of the verified canonical evidence bytes."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        """Avoid leaking tenant, Position, actor, or evidence correlations in routine logs."""
        return "PositionLifecycleChangeReviewPacket(redacted)"
