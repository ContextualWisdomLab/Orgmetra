"""Governed, PII-minimized Job grade and band design review evidence.

This module records a human-reviewed proposal for an enterprise-local Job grade and
band.  It never assigns the grade, changes compensation, or authorizes an employment
decision.  Authoritative persistence must re-resolve the Job, Job Analysis snapshot,
grade/band architecture, reviewer authority, and tenant scope before writing any
bitemporal HRIS fact and immutable audit/outbox evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from threading import RLock
from typing import ClassVar
from uuid import UUID
from weakref import WeakKeyDictionary

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_METHOD_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_ARCHITECTURE_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_-]{0,31}$")
_MAX_UUID_INT = (1 << 128) - 1
_PURPOSE_CODE = "job_grade_design_review"
_REVIEW_STATE = "reviewed_for_authoritative_resolution"
_DECISION_AUTHORITY = "not_authorized_to_assign_grade_or_compensation"
_EVIDENCE_VERSION = 1
_ALLOWED_REASON_CODES = frozenset(
    {
        "job_architecture_alignment",
        "new_job_design",
        "job_content_change",
        "periodic_job_review",
    }
)
_NEXT_ACTION = (
    "Within tenant_record_id, re-resolve the authoritative Job and persisted Job Analysis "
    "snapshot, verify their exact evidence digest and the reviewed enterprise grade/band "
    "definition digest, confirm accountable reviewer authority and human review, then persist "
    "any bitemporal Job-grade fact with immutable audit/outbox evidence. This packet does not "
    "mutate Job, Position, Assignment, compensation, or any employment decision."
)


def _require_exact_text(value: object, field_name: str) -> str:
    """Return trust-bearing text only when it is an exact built-in string."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be an exact string")
    return value


def _validate_operational_uuid_text(value: object, field_name: str) -> str:
    """Require canonical non-sentinel UUID text without imposing one UUID version."""
    text = _require_exact_text(value, field_name)
    try:
        parsed = UUID(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be canonical operational UUID text") from exc
    if str(parsed) != text or parsed.int in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be canonical operational UUID text")
    return text


def _validate_reference(
    value: object,
    prefix: str,
    field_name: str,
    *,
    require_uuid4: bool,
) -> str:
    """Require a namespaced canonical UUID reference owned by the stated boundary."""
    text = _require_exact_text(value, field_name)
    namespace = f"{prefix}:"
    if len(text) > 160 or not text.startswith(namespace):
        raise ValueError(f"{field_name} must be an opaque {prefix}:<canonical-uuid> reference")
    suffix = text[len(namespace) :]
    try:
        parsed = UUID(suffix)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must be an opaque {prefix}:<canonical-uuid> reference"
        ) from exc
    if str(parsed) != suffix or parsed.int in (0, _MAX_UUID_INT):
        raise ValueError(
            f"{field_name} must be an opaque {prefix}:<canonical-uuid> reference"
        )
    if require_uuid4 and parsed.version != 4:
        raise ValueError(f"{field_name} must use an opaque canonical UUIDv4 reference")
    return text


def _validate_digest(value: object, field_name: str) -> str:
    """Require exact lower-case SHA-256 hexadecimal evidence."""
    text = _require_exact_text(value, field_name)
    if not _DIGEST_PATTERN.fullmatch(text):
        raise ValueError(f"{field_name} must be lower-case SHA-256 hex")
    return text


def _validate_method_code(value: object) -> str:
    """Require a bounded descriptive lower snake_case evaluation-method code."""
    text = _require_exact_text(value, "job_evaluation_method_code")
    if len(text) > 64 or not _METHOD_CODE_PATTERN.fullmatch(text):
        raise ValueError(
            "job_evaluation_method_code must be bounded two-or-more-word lower snake_case"
        )
    return text


def _validate_architecture_code(value: object, field_name: str) -> str:
    """Require one bounded enterprise-local uppercase grade or band token."""
    text = _require_exact_text(value, field_name)
    if not _ARCHITECTURE_CODE_PATTERN.fullmatch(text):
        raise ValueError(f"{field_name} must be a bounded uppercase enterprise-local token")
    return text


def _validate_reason_code(value: object) -> str:
    """Require one reviewed non-sensitive Job architecture reason code."""
    text = _require_exact_text(value, "reason_code")
    if text not in _ALLOWED_REASON_CODES:
        raise ValueError("reason_code must use a reviewed Job architecture reason")
    return text


def _validate_evidence_version(value: object) -> int:
    """Require the exact supported canonical evidence-schema version."""
    if type(value) is not int or value != _EVIDENCE_VERSION:
        raise ValueError(f"evidence_version must be exact integer {_EVIDENCE_VERSION}")
    return value


def _validate_utc_timestamp(value: object, field_name: str) -> datetime:
    """Require an exact built-in datetime whose timezone is the UTC singleton."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError(f"{field_name} must be an exact built-in UTC datetime")
    return value


def _canonical_timestamp(value: datetime) -> str:
    """Render a previously validated UTC datetime as deterministic RFC 3339 text."""
    return value.isoformat().replace("+00:00", "Z")


def _canonical_json(payload: dict[str, object]) -> str:
    """Serialize one evidence payload deterministically for audit correlation."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True, slots=True, weakref_slot=True, eq=False, repr=False)
class JobGradeDesignReviewPacket:
    """Human-reviewed Job grade/band proposal without grade or compensation authority."""

    tenant_record_id: str
    job_record_reference: str
    job_analysis_snapshot_reference: str
    job_analysis_snapshot_digest: str
    job_evaluation_method_code: str
    job_evaluation_method_digest: str
    grade_code: str
    band_code: str
    grade_band_definition_digest: str
    requester_actor_reference: str
    reviewer_actor_reference: str
    reason_code: str
    reviewed_at: datetime
    recorded_at: datetime
    evidence_version: int = _EVIDENCE_VERSION
    purpose_code: str = _PURPOSE_CODE
    review_state: str = _REVIEW_STATE
    decision_authority: str = _DECISION_AUTHORITY
    human_review_required: bool = True
    next_action: str = _NEXT_ACTION

    _issuance_digests: ClassVar[
        WeakKeyDictionary["JobGradeDesignReviewPacket", str]
    ] = WeakKeyDictionary()
    _issuance_lock: ClassVar[RLock] = RLock()

    def __post_init__(self) -> None:
        """Validate every trust-bearing field and seal the creation-time evidence digest."""
        _validate_operational_uuid_text(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.job_record_reference,
            "job_record",
            "job_record_reference",
            require_uuid4=False,
        )
        _validate_reference(
            self.job_analysis_snapshot_reference,
            "job_analysis_snapshot",
            "job_analysis_snapshot_reference",
            require_uuid4=False,
        )
        _validate_digest(self.job_analysis_snapshot_digest, "job_analysis_snapshot_digest")
        _validate_method_code(self.job_evaluation_method_code)
        _validate_digest(self.job_evaluation_method_digest, "job_evaluation_method_digest")
        _validate_architecture_code(self.grade_code, "grade_code")
        _validate_architecture_code(self.band_code, "band_code")
        _validate_digest(self.grade_band_definition_digest, "grade_band_definition_digest")
        _validate_reference(
            self.requester_actor_reference,
            "actor",
            "requester_actor_reference",
            require_uuid4=True,
        )
        _validate_reference(
            self.reviewer_actor_reference,
            "actor",
            "reviewer_actor_reference",
            require_uuid4=True,
        )
        if self.requester_actor_reference == self.reviewer_actor_reference:
            raise ValueError("requester and reviewer must be different actor references")
        _validate_reason_code(self.reason_code)
        reviewed_at = _validate_utc_timestamp(self.reviewed_at, "reviewed_at")
        recorded_at = _validate_utc_timestamp(self.recorded_at, "recorded_at")
        if recorded_at < reviewed_at:
            raise ValueError("recorded_at cannot precede reviewed_at")
        _validate_evidence_version(self.evidence_version)
        if type(self.purpose_code) is not str or self.purpose_code != _PURPOSE_CODE:
            raise ValueError("purpose_code must remain job_grade_design_review")
        if type(self.review_state) is not str or self.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain reviewed_for_authoritative_resolution")
        if (
            type(self.decision_authority) is not str
            or self.decision_authority != _DECISION_AUTHORITY
        ):
            raise ValueError(
                "decision_authority must remain not_authorized_to_assign_grade_or_compensation"
            )
        if self.human_review_required is not True:
            raise ValueError("human review is mandatory for Job grade design evidence")
        if type(self.next_action) is not str or self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed Job-grade instruction")

        payload = self._payload()
        digest = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
        with self._issuance_lock:
            self._issuance_digests[self] = digest

    def __repr__(self) -> str:
        """Return a fully redacted representation safe for routine logs and assertions."""
        return "JobGradeDesignReviewPacket(<redacted>)"

    def _payload(self) -> dict[str, object]:
        """Snapshot the complete canonical evidence fields exactly once for verification."""
        return {
            "band_code": self.band_code,
            "decision_authority": self.decision_authority,
            "evidence_version": self.evidence_version,
            "grade_band_definition_digest": self.grade_band_definition_digest,
            "grade_code": self.grade_code,
            "human_review_required": self.human_review_required,
            "job_analysis_snapshot_digest": self.job_analysis_snapshot_digest,
            "job_analysis_snapshot_reference": self.job_analysis_snapshot_reference,
            "job_evaluation_method_code": self.job_evaluation_method_code,
            "job_evaluation_method_digest": self.job_evaluation_method_digest,
            "job_record_reference": self.job_record_reference,
            "next_action": self.next_action,
            "purpose_code": self.purpose_code,
            "reason_code": self.reason_code,
            "recorded_at": _canonical_timestamp(self.recorded_at),
            "requester_actor_reference": self.requester_actor_reference,
            "review_state": self.review_state,
            "reviewed_at": _canonical_timestamp(self.reviewed_at),
            "reviewer_actor_reference": self.reviewer_actor_reference,
            "tenant_record_id": self.tenant_record_id,
        }

    def _verified_payload(self) -> dict[str, object]:
        """Return one verified snapshot or fail closed after any post-issuance mutation."""
        payload = self._payload()
        digest = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
        with self._issuance_lock:
            issued_digest = self._issuance_digests.get(self)
        if issued_digest != digest:
            raise ValueError("Job grade design evidence was modified after issuance")
        return payload

    def canonical_document(self) -> dict[str, object]:
        """Return a detached verified canonical evidence document for audit persistence."""
        return dict(self._verified_payload())

    def canonical_json(self) -> str:
        """Return deterministic JSON from the exact verified evidence snapshot."""
        return _canonical_json(self._verified_payload())

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact verified canonical JSON evidence."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_job_grade_design_review_packet(
    *,
    tenant_record_id: str,
    job_record_reference: str,
    job_analysis_snapshot_reference: str,
    job_analysis_snapshot_digest: str,
    job_evaluation_method_code: str,
    job_evaluation_method_digest: str,
    grade_code: str,
    band_code: str,
    grade_band_definition_digest: str,
    requester_actor_reference: str,
    reviewer_actor_reference: str,
    reason_code: str,
    reviewed_at: datetime,
    recorded_at: datetime,
    evidence_version: int = _EVIDENCE_VERSION,
) -> JobGradeDesignReviewPacket:
    """Build one non-authoritative human-reviewed Job grade/band design proposal."""
    return JobGradeDesignReviewPacket(
        tenant_record_id=tenant_record_id,
        job_record_reference=job_record_reference,
        job_analysis_snapshot_reference=job_analysis_snapshot_reference,
        job_analysis_snapshot_digest=job_analysis_snapshot_digest,
        job_evaluation_method_code=job_evaluation_method_code,
        job_evaluation_method_digest=job_evaluation_method_digest,
        grade_code=grade_code,
        band_code=band_code,
        grade_band_definition_digest=grade_band_definition_digest,
        requester_actor_reference=requester_actor_reference,
        reviewer_actor_reference=reviewer_actor_reference,
        reason_code=reason_code,
        reviewed_at=reviewed_at,
        recorded_at=recorded_at,
        evidence_version=evidence_version,
    )
