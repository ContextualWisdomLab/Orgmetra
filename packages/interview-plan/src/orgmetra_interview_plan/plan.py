"""Governed, candidate-neutral structured-interview plan evidence.

The plan binds an interview to job-analysis evidence, predetermined competencies,
question/rating artifacts, and an accountable interviewer panel. It contains no
candidate PII or candidate response/score and remains pending explicit human approval.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from uuid import UUID

_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,31}:[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$")
_PURPOSE_CODE = "structured_interview_plan"
_REVIEW_STATE = "requires_human_approval"
_NEXT_ACTION = (
    "Confirm the competencies, predetermined questions, rating anchors, and trained panel "
    "are job-related and appropriate before activating this structured interview plan."
)


def _validate_operational_uuid(value: str, field_name: str) -> None:
    """Require canonical non-sentinel UUID text for a governance identity."""
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{field_name} must be canonical UUID text") from exc
    if str(parsed) != value or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(f"{field_name} must be a canonical operational UUID")


def _validate_code(value: str, field_name: str) -> None:
    """Require a bounded descriptive lower snake_case governance code."""
    if not isinstance(value, str) or len(value) > 64 or not _CODE_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be bounded two-or-more-word lower snake_case")


def _validate_reference(value: str, prefix: str, field_name: str) -> None:
    """Require a bounded namespaced opaque reference with the expected prefix."""
    if (
        not isinstance(value, str)
        or len(value) > 160
        or not _REFERENCE_PATTERN.fullmatch(value)
        or not value.startswith(f"{prefix}:")
    ):
        raise ValueError(f"{field_name} must be an opaque {prefix}: reference")


def _validate_digest(value: str, field_name: str) -> None:
    """Require lowercase SHA-256 hexadecimal evidence."""
    if not isinstance(value, str) or not _DIGEST_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _canonical_timestamp(value: datetime) -> str:
    """Render an aware instant as precision-preserving UTC RFC 3339 text."""
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class StructuredInterviewPlan:
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
    human_confirmation_required: bool = True
    review_state: str = _REVIEW_STATE
    next_action: str = _NEXT_ACTION

    def __post_init__(self) -> None:
        """Fail closed when direct construction drifts from the governed contract."""
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
        if not isinstance(self.competency_references, tuple) or not 1 <= len(self.competency_references) <= 12:
            raise ValueError("competency_references must be a tuple containing 1 through 12 competencies")
        for reference in self.competency_references:
            _validate_reference(reference, "competency", "competency_references")
        if tuple(sorted(set(self.competency_references))) != self.competency_references:
            raise ValueError("competency_references must be sorted and unique")
        if not isinstance(self.panel_actor_references, tuple) or not 2 <= len(self.panel_actor_references) <= 8:
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
        _canonical_timestamp(self.generated_at)
        if self.human_confirmation_required is not True:
            raise ValueError("human confirmation is mandatory for interview-plan approval")
        if self.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain requires_human_approval")
        if self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed interview-plan instruction")

    def canonical_json(self) -> str:
        """Return deterministic canonical JSON for immutable audit correlation."""
        payload = {
            "competency_references": list(self.competency_references),
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

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical UTF-8 plan."""
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
    )
