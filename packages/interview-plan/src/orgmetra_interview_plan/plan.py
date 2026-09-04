"""Governed, candidate-neutral structured-interview plan evidence.

The plan binds an interview to job-analysis evidence, predetermined competencies,
question/rating artifacts, and an accountable interviewer panel. It contains no
candidate PII or candidate response/score and remains pending explicit human approval.
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import hmac
import json
import re
import secrets
from threading import RLock
from uuid import UUID
from weakref import WeakValueDictionary, finalize

_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PURPOSE_CODE = "structured_interview_plan"
_REVIEW_STATE = "requires_human_approval"
_ALLOWED_REASON_CODES = frozenset({"approved_requisition_interview"})
_NEXT_ACTION = (
    "Within tenant_record_id, re-resolve every plan reference and verify the "
    "requisition-to-Job-to-job-analysis binding; verify question-set, "
    "question-to-competency mapping, and rating-anchor provenance; re-resolve every "
    "panel_actor_reference, prove the resolved panel actor identities are distinct, "
    "and verify panel eligibility and training before an accountable human activates "
    "this structured interview plan."
)
_MAX_EVIDENCE_VERSION = 2_147_483_647
_PROCESS_PLAN_SEAL_KEY = secrets.token_bytes(32)
_PLAN_SEALS: dict[int, str] = {}
_CONSTRUCTING_PLAN_IDENTITIES: WeakValueDictionary[int, object] = WeakValueDictionary()
_ISSUED_PLAN_IDENTITIES: WeakValueDictionary[int, object] = WeakValueDictionary()
_ACTIVE_PLAN_CONSTRUCTOR = ContextVar("_ACTIVE_PLAN_CONSTRUCTOR", default=None)
_PLAN_SEALS_LOCK = RLock()


def _discard_plan_seal(plan_id: int) -> None:
    """Discard process-local issuance evidence after the plan is collected."""
    with _PLAN_SEALS_LOCK:
        _PLAN_SEALS.pop(plan_id, None)


def _register_plan_seal(plan: object, seal: str) -> None:
    """Bind one live plan identity once to evidence outside plan-writable slots."""
    plan_id = id(plan)
    with _PLAN_SEALS_LOCK:
        if plan_id in _PLAN_SEALS:
            raise ValueError("structured interview plan issuance evidence already exists")
        _PLAN_SEALS[plan_id] = seal
    finalize(plan, _discard_plan_seal, plan_id)


def _authoritative_plan_seal(plan: object) -> str | None:
    """Return process-local issuance evidence without trusting plan-owned state."""
    with _PLAN_SEALS_LOCK:
        return _PLAN_SEALS.get(id(plan))


def _seal_plan(payload_json: str) -> str:
    """Bind one process-local plan issuance to exact canonical payload bytes."""
    return hmac.new(
        _PROCESS_PLAN_SEAL_KEY,
        payload_json.encode("utf-8"),
        "sha256",
    ).hexdigest()


def _validate_operational_uuid(value: str, field_name: str) -> None:
    """Require canonical non-sentinel UUID text owned by the authoritative HRIS."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be canonical UUID text")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{field_name} must be canonical UUID text") from exc
    if str(parsed) != value or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(f"{field_name} must be a canonical operational UUID")


def _validate_code(value: str, field_name: str) -> None:
    """Require exact bounded descriptive lower snake_case governance text."""
    if type(value) is not str or len(value) > 64 or not _CODE_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be bounded two-or-more-word lower snake_case")


def _validate_reference(value: str, prefix: str, field_name: str) -> None:
    """Require the expected namespace plus a canonical non-sentinel UUIDv4 suffix."""
    namespace = f"{prefix}:"
    if type(value) is not str or len(value) > 160 or not value.startswith(namespace):
        raise ValueError(f"{field_name} must be an opaque {prefix}:<canonical-uuid> reference")
    suffix = value[len(namespace) :]
    try:
        parsed = UUID(suffix)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{field_name} must be an opaque {prefix}:<canonical-uuid> reference") from exc
    if str(parsed) != suffix or parsed.version != 4 or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(f"{field_name} must be an opaque {prefix}:<canonical-uuid> reference")


def _validate_digest(value: str, field_name: str) -> None:
    """Require exact built-in string lowercase SHA-256 hexadecimal evidence."""
    if type(value) is not str or not _DIGEST_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _snapshot_utc_datetime(value: datetime, field_name: str) -> datetime:
    """Detach one caller-owned aware datetime into a representable built-in UTC instant."""
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError(f"{field_name} must be an exact timezone-aware datetime")
    try:
        offset = value.utcoffset()
    except Exception as exc:
        raise ValueError(f"{field_name} must be an exact timezone-aware datetime") from exc
    if type(offset) is not timedelta:
        raise ValueError(f"{field_name} must be an exact timezone-aware datetime")
    local_naive = value.replace(tzinfo=None)
    try:
        normalized = local_naive - offset
    except OverflowError as exc:
        raise ValueError(f"{field_name} must be an exact timezone-aware datetime") from exc
    return normalized.replace(tzinfo=timezone.utc)


def _canonical_timestamp(value: datetime, field_name: str = "generated_at") -> str:
    """Render an aware instant as UTC RFC 3339 text after fail-closed detachment."""
    return _snapshot_utc_datetime(value, field_name).isoformat().replace("+00:00", "Z")


class _StructuredInterviewPlanMeta(type):
    """Gate plan provenance on one allocator ticket per normal class construction."""

    def __call__(cls, *args: object, **kwargs: object) -> object:
        """Arm one allocator ticket before Python enters this class's constructor."""
        token = _ACTIVE_PLAN_CONSTRUCTOR.set(cls)
        try:
            return super().__call__(*args, **kwargs)
        finally:
            _ACTIVE_PLAN_CONSTRUCTOR.reset(token)


@dataclass(frozen=True, slots=True, repr=False, weakref_slot=True)
class StructuredInterviewPlan(metaclass=_StructuredInterviewPlanMeta):
    """Immutable candidate-neutral interview-plan evidence awaiting human approval."""

    tenant_record_id: str
    interview_plan_reference: str
    requisition_reference: str
    job_profile_reference: str
    job_analysis_reference: str
    job_analysis_digest: str
    question_set_reference: str
    question_set_digest: str
    question_competency_map_reference: str
    question_competency_map_digest: str
    rating_anchor_reference: str
    rating_anchor_digest: str
    competency_references: tuple[str, ...]
    panel_actor_references: tuple[str, ...]
    question_count: int
    purpose_code: str
    reason_code: str
    generated_at: datetime
    evidence_version: int = 1
    human_confirmation_required: bool = True
    review_state: str = _REVIEW_STATE
    next_action: str = _NEXT_ACTION

    def __new__(cls, *_args: object, **_kwargs: object) -> StructuredInterviewPlan:
        """Consume constructor eligibility before caller-controlled validation can run."""
        instance = object.__new__(cls)
        if _ACTIVE_PLAN_CONSTRUCTOR.get() is cls:
            _ACTIVE_PLAN_CONSTRUCTOR.set(None)
            with _PLAN_SEALS_LOCK:
                _CONSTRUCTING_PLAN_IDENTITIES[id(instance)] = instance
        return instance

    def __post_init__(self) -> None:
        """Fail closed when direct construction drifts from the governed contract."""
        with _PLAN_SEALS_LOCK:
            if _ISSUED_PLAN_IDENTITIES.get(id(self)) is self:
                raise ValueError("structured interview plan issuance evidence already exists")
            if _CONSTRUCTING_PLAN_IDENTITIES.get(id(self)) is not self:
                raise ValueError("structured interview plan constructor provenance is unavailable")
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(self.interview_plan_reference, "interview_plan", "interview_plan_reference")
        _validate_reference(self.requisition_reference, "requisition", "requisition_reference")
        _validate_reference(self.job_profile_reference, "job_profile", "job_profile_reference")
        _validate_reference(self.job_analysis_reference, "job_analysis", "job_analysis_reference")
        _validate_digest(self.job_analysis_digest, "job_analysis_digest")
        _validate_reference(self.question_set_reference, "question_set", "question_set_reference")
        _validate_digest(self.question_set_digest, "question_set_digest")
        _validate_reference(
            self.question_competency_map_reference,
            "question_competency_map",
            "question_competency_map_reference",
        )
        _validate_digest(self.question_competency_map_digest, "question_competency_map_digest")
        _validate_reference(self.rating_anchor_reference, "rating_anchor", "rating_anchor_reference")
        _validate_digest(self.rating_anchor_digest, "rating_anchor_digest")
        if type(self.competency_references) is not tuple or not 1 <= len(self.competency_references) <= 12:
            raise ValueError("competency_references must be a tuple containing 1 through 12 competencies")
        for reference in self.competency_references:
            _validate_reference(reference, "competency", "competency_references")
        if tuple(sorted(set(self.competency_references))) != self.competency_references:
            raise ValueError("competency_references must be sorted and unique")
        if type(self.panel_actor_references) is not tuple or not 2 <= len(self.panel_actor_references) <= 8:
            raise ValueError("panel_actor_references must be a tuple containing 2 through 8 actors")
        for reference in self.panel_actor_references:
            _validate_reference(reference, "actor", "panel_actor_references")
        if tuple(sorted(set(self.panel_actor_references))) != self.panel_actor_references:
            raise ValueError("panel_actor_references must be sorted and unique")
        if type(self.question_count) is not int or not 1 <= self.question_count <= 20:
            raise ValueError("question_count must be an integer from 1 through 20")
        if self.question_count < len(self.competency_references):
            raise ValueError("question_count must be at least the number of governed competencies")
        _validate_code(self.purpose_code, "purpose_code")
        if self.purpose_code != _PURPOSE_CODE:
            raise ValueError("purpose_code must remain structured_interview_plan")
        _validate_code(self.reason_code, "reason_code")
        if self.reason_code not in _ALLOWED_REASON_CODES:
            raise ValueError("reason_code must use a reviewed non-sensitive interview-plan reason")
        generated_at_snapshot = _snapshot_utc_datetime(self.generated_at, "generated_at")
        object.__setattr__(self, "generated_at", generated_at_snapshot)
        if type(self.evidence_version) is not int or not 1 <= self.evidence_version <= _MAX_EVIDENCE_VERSION:
            raise ValueError("evidence_version must be an integer from 1 through 2147483647")
        if self.human_confirmation_required is not True:
            raise ValueError("human confirmation is mandatory for interview-plan approval")
        if type(self.review_state) is not str or self.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain requires_human_approval")
        if type(self.next_action) is not str or self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed interview-plan instruction")
        _register_plan_seal(self, _seal_plan(self._canonical_json_unchecked()))
        with _PLAN_SEALS_LOCK:
            _ISSUED_PLAN_IDENTITIES[id(self)] = self
            _CONSTRUCTING_PLAN_IDENTITIES.pop(id(self), None)

    def __repr__(self) -> str:
        """Return a fully redacted representation safe for routine logs and assertions."""
        return "StructuredInterviewPlan(<redacted>)"

    def _canonical_json_unchecked(self) -> str:
        """Render canonical plan bytes without process-local issuance state."""
        payload = {
            "competency_references": list(self.competency_references),
            "evidence_version": self.evidence_version,
            "generated_at": _canonical_timestamp(self.generated_at),
            "human_confirmation_required": self.human_confirmation_required,
            "interview_plan_reference": self.interview_plan_reference,
            "job_analysis_digest": self.job_analysis_digest,
            "job_analysis_reference": self.job_analysis_reference,
            "job_profile_reference": self.job_profile_reference,
            "next_action": self.next_action,
            "panel_actor_references": list(self.panel_actor_references),
            "purpose_code": self.purpose_code,
            "question_competency_map_digest": self.question_competency_map_digest,
            "question_competency_map_reference": self.question_competency_map_reference,
            "question_count": self.question_count,
            "question_set_digest": self.question_set_digest,
            "question_set_reference": self.question_set_reference,
            "rating_anchor_digest": self.rating_anchor_digest,
            "rating_anchor_reference": self.rating_anchor_reference,
            "reason_code": self.reason_code,
            "requisition_reference": self.requisition_reference,
            "review_state": self.review_state,
            "tenant_record_id": self.tenant_record_id,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def canonical_json(self) -> str:
        """Return creation-bound canonical JSON for immutable audit correlation."""
        with _PLAN_SEALS_LOCK:
            if _ISSUED_PLAN_IDENTITIES.get(id(self)) is not self:
                raise ValueError("structured interview plan issuance evidence is unavailable")
        canonical = self._canonical_json_unchecked()
        authoritative_seal = _authoritative_plan_seal(self)
        if type(authoritative_seal) is not str:
            raise ValueError("structured interview plan issuance evidence is unavailable")
        if not hmac.compare_digest(_seal_plan(canonical), authoritative_seal):
            raise ValueError("structured interview plan changed after plan issuance")
        return canonical

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact creation-bound canonical UTF-8 plan."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_structured_interview_plan(
    *,
    tenant_record_id: str,
    interview_plan_reference: str,
    requisition_reference: str,
    job_profile_reference: str,
    job_analysis_reference: str,
    job_analysis_digest: str,
    question_set_reference: str,
    question_set_digest: str,
    question_competency_map_reference: str,
    question_competency_map_digest: str,
    rating_anchor_reference: str,
    rating_anchor_digest: str,
    competency_references: tuple[str, ...],
    panel_actor_references: tuple[str, ...],
    question_count: int,
    purpose_code: str,
    reason_code: str,
    generated_at: datetime,
    evidence_version: int = 1,
) -> StructuredInterviewPlan:
    """Build a governed structured-interview plan that remains pending human approval."""
    return StructuredInterviewPlan(
        tenant_record_id=tenant_record_id,
        interview_plan_reference=interview_plan_reference,
        requisition_reference=requisition_reference,
        job_profile_reference=job_profile_reference,
        job_analysis_reference=job_analysis_reference,
        job_analysis_digest=job_analysis_digest,
        question_set_reference=question_set_reference,
        question_set_digest=question_set_digest,
        question_competency_map_reference=question_competency_map_reference,
        question_competency_map_digest=question_competency_map_digest,
        rating_anchor_reference=rating_anchor_reference,
        rating_anchor_digest=rating_anchor_digest,
        competency_references=competency_references,
        panel_actor_references=panel_actor_references,
        question_count=question_count,
        purpose_code=purpose_code,
        reason_code=reason_code,
        generated_at=generated_at,
        evidence_version=evidence_version,
    )
