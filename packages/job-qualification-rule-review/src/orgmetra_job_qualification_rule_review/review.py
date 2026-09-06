"""Governed, PII-minimized Job qualification-rule review evidence.

This module records a human-reviewed proposal tying one qualification-rule artifact to
an authoritative Job Analysis snapshot and its Task/KSAO/source provenance. It never
evaluates a candidate, rejects an applicant, mutates Job truth, or authorizes an
employment decision. Authoritative use must re-resolve the reviewed evidence and
human authority before persisting any rule or applying it to a person.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import re
from threading import RLock
from typing import ClassVar
from uuid import UUID
from weakref import WeakKeyDictionary

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_MAX_UUID_INT = (1 << 128) - 1
_MAX_EVIDENCE_VERSION = 2_147_483_647
_PURPOSE_CODE = "job_qualification_rule_review"
_REVIEW_STATE = "reviewed_for_authoritative_resolution"
_DECISION_AUTHORITY = "not_authorized_for_candidate_or_employment_decision"
_ALLOWED_RULE_CATEGORIES = frozenset(
    {
        "credential_requirement",
        "education_training_requirement",
        "experience_requirement",
        "knowledge_skill_ability_requirement",
        "task_or_work_requirement",
    }
)
_ALLOWED_REASON_CODES = frozenset(
    {
        "new_job_analysis",
        "job_analysis_revision",
        "periodic_job_analysis_review",
        "source_evidence_change",
    }
)
_NEXT_ACTION = (
    "Within tenant_record_id, re-resolve the authoritative Job and Job Analysis snapshot, "
    "verify the exact qualification-rule artifact and Task/KSAO/source evidence digests, "
    "confirm accountable reviewer identity and authority at the business-effective coordinate, "
    "then persist any authoritative Job-rule change with immutable audit/outbox evidence. "
    "Candidate evaluation and employment decisions require separate governed human review."
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


def _validate_rule_category(value: object) -> str:
    """Require one reviewed non-sensitive qualification-rule category."""
    text = _require_exact_text(value, "rule_category")
    if text not in _ALLOWED_RULE_CATEGORIES:
        raise ValueError("rule_category must use a reviewed Job qualification category")
    return text


def _validate_reason_code(value: object) -> str:
    """Require one reviewed non-sensitive Job-analysis review reason."""
    text = _require_exact_text(value, "reason_code")
    if text not in _ALLOWED_REASON_CODES:
        raise ValueError("reason_code must use a reviewed Job-analysis reason")
    return text


def _validate_effective_date(value: object) -> date:
    """Require an exact built-in date for business-effective rule semantics."""
    if type(value) is not date:
        raise ValueError("effective_on must be an exact built-in date")
    return value


def _validate_utc_timestamp(value: object, field_name: str) -> datetime:
    """Require an exact built-in datetime whose timezone is the UTC singleton."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError(f"{field_name} must be an exact built-in UTC datetime")
    return value


def _validate_evidence_version(value: object) -> int:
    """Require one bounded positive exact integer evidence version."""
    if type(value) is not int or not 1 <= value <= _MAX_EVIDENCE_VERSION:
        raise ValueError("evidence_version must be an exact integer from 1 through 2147483647")
    return value


def _canonical_timestamp(value: datetime) -> str:
    """Render a previously validated UTC datetime as deterministic RFC 3339 text."""
    return value.isoformat().replace("+00:00", "Z")


def _canonical_json(payload: dict[str, object]) -> str:
    """Serialize one evidence payload deterministically for audit correlation."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True, slots=True, weakref_slot=True, eq=False, repr=False)
class JobQualificationRuleReviewPacket:
    """Human-reviewed Job qualification-rule proposal without candidate-decision authority.

    The packet is deliberately non-subclassable: trust-boundary validation must
    never be bypassable by an in-process subclass overriding the validation hook.
    """

    tenant_record_id: str
    job_record_reference: str
    job_analysis_snapshot_reference: str
    job_analysis_snapshot_digest: str
    qualification_rule_artifact_reference: str
    qualification_rule_artifact_digest: str
    task_linkage_digest: str
    ksao_linkage_digest: str
    source_evidence_digest: str
    rule_category: str
    effective_on: date
    requester_actor_reference: str
    reviewer_actor_reference: str
    reason_code: str
    evidence_version: int
    reviewed_at: datetime
    recorded_at: datetime = field(init=False)
    purpose_code: str = _PURPOSE_CODE
    review_state: str = _REVIEW_STATE
    decision_authority: str = _DECISION_AUTHORITY
    human_review_required: bool = True
    next_action: str = _NEXT_ACTION

    _issuance_digests: ClassVar[
        WeakKeyDictionary["JobQualificationRuleReviewPacket", str]
    ] = WeakKeyDictionary()
    _issuance_lock: ClassVar[RLock] = RLock()

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Reject every subclass so validation can never be overridden away."""
        raise TypeError(
            "JobQualificationRuleReviewPacket must not be subclassed; "
            "trust-boundary validation is non-overridable"
        )

    def __post_init__(self) -> None:
        """Generate system time, validate all trust-bearing fields, and seal evidence."""
        object.__setattr__(self, "recorded_at", datetime.now(timezone.utc))
        payload = self._validated_payload()
        digest = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
        with self._issuance_lock:
            self._issuance_digests[self] = digest

    def __repr__(self) -> str:
        """Return a fully redacted representation safe for routine logs and assertions."""
        return "JobQualificationRuleReviewPacket(<redacted>)"

    def _validated_payload(self) -> dict[str, object]:
        """Revalidate and snapshot every canonical evidence field exactly once."""
        tenant_record_id = _validate_operational_uuid_text(
            self.tenant_record_id, "tenant_record_id"
        )
        job_record_reference = _validate_reference(
            self.job_record_reference,
            "job_record",
            "job_record_reference",
            require_uuid4=False,
        )
        job_analysis_snapshot_reference = _validate_reference(
            self.job_analysis_snapshot_reference,
            "job_analysis_snapshot",
            "job_analysis_snapshot_reference",
            require_uuid4=False,
        )
        job_analysis_snapshot_digest = _validate_digest(
            self.job_analysis_snapshot_digest, "job_analysis_snapshot_digest"
        )
        qualification_rule_artifact_reference = _validate_reference(
            self.qualification_rule_artifact_reference,
            "qualification_rule_artifact",
            "qualification_rule_artifact_reference",
            require_uuid4=True,
        )
        qualification_rule_artifact_digest = _validate_digest(
            self.qualification_rule_artifact_digest,
            "qualification_rule_artifact_digest",
        )
        task_linkage_digest = _validate_digest(self.task_linkage_digest, "task_linkage_digest")
        ksao_linkage_digest = _validate_digest(self.ksao_linkage_digest, "ksao_linkage_digest")
        source_evidence_digest = _validate_digest(
            self.source_evidence_digest, "source_evidence_digest"
        )
        rule_category = _validate_rule_category(self.rule_category)
        effective_on = _validate_effective_date(self.effective_on)
        requester_actor_reference = _validate_reference(
            self.requester_actor_reference,
            "actor",
            "requester_actor_reference",
            require_uuid4=True,
        )
        reviewer_actor_reference = _validate_reference(
            self.reviewer_actor_reference,
            "actor",
            "reviewer_actor_reference",
            require_uuid4=True,
        )
        if requester_actor_reference == reviewer_actor_reference:
            raise ValueError("requester and reviewer must be different actor references")
        reason_code = _validate_reason_code(self.reason_code)
        evidence_version = _validate_evidence_version(self.evidence_version)
        reviewed_at = _validate_utc_timestamp(self.reviewed_at, "reviewed_at")
        recorded_at = _validate_utc_timestamp(self.recorded_at, "recorded_at")
        if recorded_at < reviewed_at:
            raise ValueError("recorded_at cannot precede reviewed_at")
        if type(self.purpose_code) is not str or self.purpose_code != _PURPOSE_CODE:
            raise ValueError("purpose_code must remain job_qualification_rule_review")
        if type(self.review_state) is not str or self.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain reviewed_for_authoritative_resolution")
        if (
            type(self.decision_authority) is not str
            or self.decision_authority != _DECISION_AUTHORITY
        ):
            raise ValueError(
                "decision_authority must remain not_authorized_for_candidate_or_employment_decision"
            )
        if self.human_review_required is not True:
            raise ValueError("human review is mandatory for Job qualification-rule evidence")
        if type(self.next_action) is not str or self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed qualification-rule instruction")

        return {
            "decision_authority": self.decision_authority,
            "effective_on": effective_on.isoformat(),
            "evidence_version": evidence_version,
            "human_review_required": self.human_review_required,
            "job_analysis_snapshot_digest": job_analysis_snapshot_digest,
            "job_analysis_snapshot_reference": job_analysis_snapshot_reference,
            "job_record_reference": job_record_reference,
            "ksao_linkage_digest": ksao_linkage_digest,
            "next_action": self.next_action,
            "purpose_code": self.purpose_code,
            "qualification_rule_artifact_digest": qualification_rule_artifact_digest,
            "qualification_rule_artifact_reference": qualification_rule_artifact_reference,
            "reason_code": reason_code,
            "recorded_at": _canonical_timestamp(recorded_at),
            "requester_actor_reference": requester_actor_reference,
            "review_state": self.review_state,
            "reviewed_at": _canonical_timestamp(reviewed_at),
            "reviewer_actor_reference": reviewer_actor_reference,
            "rule_category": rule_category,
            "source_evidence_digest": source_evidence_digest,
            "task_linkage_digest": task_linkage_digest,
            "tenant_record_id": tenant_record_id,
        }

    def _verified_payload(self) -> dict[str, object]:
        """Return one verified snapshot or fail closed after any post-issuance mutation."""
        payload = self._validated_payload()
        digest = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
        with self._issuance_lock:
            issued_digest = self._issuance_digests.get(self)
        if issued_digest != digest:
            raise ValueError("Job qualification-rule evidence was modified after issuance")
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


def build_job_qualification_rule_review_packet(
    *,
    tenant_record_id: str,
    job_record_reference: str,
    job_analysis_snapshot_reference: str,
    job_analysis_snapshot_digest: str,
    qualification_rule_artifact_reference: str,
    qualification_rule_artifact_digest: str,
    task_linkage_digest: str,
    ksao_linkage_digest: str,
    source_evidence_digest: str,
    rule_category: str,
    effective_on: date,
    requester_actor_reference: str,
    reviewer_actor_reference: str,
    reason_code: str,
    evidence_version: int,
    reviewed_at: datetime,
) -> JobQualificationRuleReviewPacket:
    """Build one human-reviewed Job qualification-rule proposal without decision authority."""
    return JobQualificationRuleReviewPacket(
        tenant_record_id=tenant_record_id,
        job_record_reference=job_record_reference,
        job_analysis_snapshot_reference=job_analysis_snapshot_reference,
        job_analysis_snapshot_digest=job_analysis_snapshot_digest,
        qualification_rule_artifact_reference=qualification_rule_artifact_reference,
        qualification_rule_artifact_digest=qualification_rule_artifact_digest,
        task_linkage_digest=task_linkage_digest,
        ksao_linkage_digest=ksao_linkage_digest,
        source_evidence_digest=source_evidence_digest,
        rule_category=rule_category,
        effective_on=effective_on,
        requester_actor_reference=requester_actor_reference,
        reviewer_actor_reference=reviewer_actor_reference,
        reason_code=reason_code,
        evidence_version=evidence_version,
        reviewed_at=reviewed_at,
    )
