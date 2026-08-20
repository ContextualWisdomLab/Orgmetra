"""Governed, value-minimized human performance-review evidence.

The packet correlates one proposed employee review to Employment and Job references,
a performance cycle, predetermined criteria and goals, an exact criterion-observation
snapshot, an optional development plan, and an accountable human reviewer. It does not
assert that those references resolve to one authoritative scope; that verification must
occur at the authoritative HRIS/performance boundary before rating. Opaque worker
references remain personal data because they can be re-associated with an identifiable
person through the authoritative HRIS boundary. Direct identifiers, rating values,
free-form feedback, and free-form model output remain outside this envelope.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import re
from uuid import UUID

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]{1,31}:[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$"
)
_PURPOSE_CODE = "performance_review"
_ALLOWED_REASON_CODES = frozenset({"scheduled_cycle_review"})
_DECISION_AUTHORITY = "human_review_only"
_REVIEW_STATE = "requires_human_review"
_SCOPE_VERIFICATION_STATE = "requires_authoritative_resolution"
_NEXT_ACTION = (
    "Verify authoritative Employment/Job scope, performance-cycle dates, governed "
    "criteria and goals, criterion-observation evidence, and any development-plan "
    "provenance; then record accountable human rating and feedback through the "
    "authoritative performance workflow."
)


def _validate_operational_uuid(value: str, field_name: str) -> None:
    """Require canonical non-sentinel UUID text for a governance identity."""
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{field_name} must be canonical UUID text") from exc
    if str(parsed) != value or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(f"{field_name} must be a canonical operational UUID")


def _validate_reference(value: str, prefix: str, field_name: str) -> None:
    """Require an expected namespace plus a canonical opaque UUIDv4 suffix."""
    error_message = f"{field_name} must be an opaque {prefix}: reference"
    if (
        not isinstance(value, str)
        or len(value) > 160
        or not _REFERENCE_PATTERN.fullmatch(value)
        or not value.startswith(f"{prefix}:")
    ):
        raise ValueError(error_message)
    suffix = value.split(":", 1)[1]
    try:
        parsed = UUID(suffix)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(error_message) from exc
    if str(parsed) != suffix or parsed.version != 4 or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(error_message)


def _validate_digest(value: str, field_name: str) -> None:
    """Require lowercase SHA-256 hexadecimal evidence."""
    if not isinstance(value, str) or not _DIGEST_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _canonical_timestamp(value: datetime) -> str:
    """Render an aware instant as precision-preserving UTC RFC 3339 text."""
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_business_date(value: date, field_name: str) -> None:
    """Require a business date rather than a datetime or textual date."""
    if type(value) is not date:
        raise ValueError(f"{field_name} must be a date")


def _validate_reason_code(value: str) -> None:
    """Require a closed, reviewed reason code so free-form PII cannot enter evidence."""
    if not isinstance(value, str) or value not in _ALLOWED_REASON_CODES:
        raise ValueError("reason_code must be an authorized performance-review reason code")


def _validate_evidence_version(value: int) -> None:
    """Require a bounded positive integer version for high-impact review evidence."""
    if type(value) is not int or value < 1 or value > 2_147_483_647:
        raise ValueError("evidence_version must be an integer from 1 through 2147483647")


@dataclass(frozen=True, slots=True, repr=False)
class PerformanceReviewPacket:
    """Immutable value-minimized review packet awaiting authoritative resolution."""

    tenant_record_id: str
    performance_review_reference: str
    person_record_reference: str
    employment_record_reference: str
    job_profile_reference: str
    performance_cycle_reference: str
    criterion_set_reference: str
    criterion_set_digest: str
    goal_plan_reference: str
    goal_plan_digest: str
    criterion_observation_snapshot_reference: str
    criterion_observation_snapshot_digest: str
    development_plan_reference: str | None
    development_plan_digest: str | None
    reviewer_reference: str
    purpose_code: str
    reason_code: str
    review_period_start: date
    review_period_end: date
    generated_at: datetime
    evidence_version: int = 1
    contains_personal_data: bool = True
    contains_direct_person_identifiers: bool = False
    contains_rating_value: bool = False
    contains_free_form_model_output: bool = False
    human_confirmation_required: bool = True
    decision_authority: str = _DECISION_AUTHORITY
    review_state: str = _REVIEW_STATE
    scope_verification_state: str = _SCOPE_VERIFICATION_STATE
    next_action: str = _NEXT_ACTION

    def __repr__(self) -> str:
        """Return a representation that never emits worker/rating correlation evidence."""
        return "PerformanceReviewPacket(<redacted>)"

    def __post_init__(self) -> None:
        """Fail closed when direct construction drifts from the governed contract."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.performance_review_reference,
            "performance_review",
            "performance_review_reference",
        )
        _validate_reference(self.person_record_reference, "person_record", "person_record_reference")
        _validate_reference(
            self.employment_record_reference,
            "employment_record",
            "employment_record_reference",
        )
        _validate_reference(self.job_profile_reference, "job_profile", "job_profile_reference")
        _validate_reference(
            self.performance_cycle_reference,
            "performance_cycle",
            "performance_cycle_reference",
        )
        _validate_reference(self.criterion_set_reference, "criterion_set", "criterion_set_reference")
        _validate_digest(self.criterion_set_digest, "criterion_set_digest")
        _validate_reference(self.goal_plan_reference, "performance_goal_plan", "goal_plan_reference")
        _validate_digest(self.goal_plan_digest, "goal_plan_digest")
        _validate_reference(
            self.criterion_observation_snapshot_reference,
            "criterion_observation_snapshot",
            "criterion_observation_snapshot_reference",
        )
        _validate_digest(
            self.criterion_observation_snapshot_digest,
            "criterion_observation_snapshot_digest",
        )
        if (self.development_plan_reference is None) != (self.development_plan_digest is None):
            raise ValueError("development plan reference and digest must be supplied together")
        if self.development_plan_reference is not None:
            _validate_reference(
                self.development_plan_reference,
                "development_plan",
                "development_plan_reference",
            )
            _validate_digest(self.development_plan_digest, "development_plan_digest")
        _validate_reference(self.reviewer_reference, "actor", "reviewer_reference")
        if self.purpose_code != _PURPOSE_CODE:
            raise ValueError("purpose_code must remain performance_review")
        _validate_reason_code(self.reason_code)
        _validate_business_date(self.review_period_start, "review_period_start")
        _validate_business_date(self.review_period_end, "review_period_end")
        if self.review_period_start > self.review_period_end:
            raise ValueError("review period start must not be after review period end")
        _canonical_timestamp(self.generated_at)
        _validate_evidence_version(self.evidence_version)
        if self.contains_personal_data is not True:
            raise ValueError("performance review packet contains personal data through worker references")
        if self.contains_direct_person_identifiers is not False:
            raise ValueError("performance review packet must not contain direct person identifiers")
        if self.contains_rating_value is not False:
            raise ValueError("performance review packet must not contain rating values")
        if self.contains_free_form_model_output is not False:
            raise ValueError("performance review packet must not contain free-form model output")
        if self.human_confirmation_required is not True:
            raise ValueError("human confirmation is mandatory before performance rating")
        if self.decision_authority != _DECISION_AUTHORITY:
            raise ValueError("decision_authority must remain human_review_only")
        if self.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain requires_human_review")
        if self.scope_verification_state != _SCOPE_VERIFICATION_STATE:
            raise ValueError(
                "scope_verification_state must remain requires_authoritative_resolution"
            )
        if self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed performance-review instruction")

    def canonical_json(self) -> str:
        """Return deterministic canonical JSON for immutable audit correlation."""
        payload = {
            "contains_direct_person_identifiers": self.contains_direct_person_identifiers,
            "contains_free_form_model_output": self.contains_free_form_model_output,
            "contains_personal_data": self.contains_personal_data,
            "contains_rating_value": self.contains_rating_value,
            "criterion_observation_snapshot_digest": self.criterion_observation_snapshot_digest,
            "criterion_observation_snapshot_reference": self.criterion_observation_snapshot_reference,
            "criterion_set_digest": self.criterion_set_digest,
            "criterion_set_reference": self.criterion_set_reference,
            "decision_authority": self.decision_authority,
            "development_plan_digest": self.development_plan_digest,
            "development_plan_reference": self.development_plan_reference,
            "employment_record_reference": self.employment_record_reference,
            "evidence_version": self.evidence_version,
            "generated_at": _canonical_timestamp(self.generated_at),
            "goal_plan_digest": self.goal_plan_digest,
            "goal_plan_reference": self.goal_plan_reference,
            "human_confirmation_required": self.human_confirmation_required,
            "job_profile_reference": self.job_profile_reference,
            "next_action": self.next_action,
            "performance_cycle_reference": self.performance_cycle_reference,
            "performance_review_reference": self.performance_review_reference,
            "person_record_reference": self.person_record_reference,
            "purpose_code": self.purpose_code,
            "reason_code": self.reason_code,
            "review_period_end": self.review_period_end.isoformat(),
            "review_period_start": self.review_period_start.isoformat(),
            "review_state": self.review_state,
            "reviewer_reference": self.reviewer_reference,
            "scope_verification_state": self.scope_verification_state,
            "tenant_record_id": self.tenant_record_id,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical UTF-8 performance-review packet."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_performance_review_packet(
    *,
    tenant_record_id: str,
    performance_review_reference: str,
    person_record_reference: str,
    employment_record_reference: str,
    job_profile_reference: str,
    performance_cycle_reference: str,
    criterion_set_reference: str,
    criterion_set_digest: str,
    goal_plan_reference: str,
    goal_plan_digest: str,
    criterion_observation_snapshot_reference: str,
    criterion_observation_snapshot_digest: str,
    development_plan_reference: str | None,
    development_plan_digest: str | None,
    reviewer_reference: str,
    purpose_code: str,
    reason_code: str,
    review_period_start: date,
    review_period_end: date,
    generated_at: datetime,
    evidence_version: int = 1,
) -> PerformanceReviewPacket:
    """Build value-minimized performance-review evidence pending authoritative resolution."""
    return PerformanceReviewPacket(
        tenant_record_id=tenant_record_id,
        performance_review_reference=performance_review_reference,
        person_record_reference=person_record_reference,
        employment_record_reference=employment_record_reference,
        job_profile_reference=job_profile_reference,
        performance_cycle_reference=performance_cycle_reference,
        criterion_set_reference=criterion_set_reference,
        criterion_set_digest=criterion_set_digest,
        goal_plan_reference=goal_plan_reference,
        goal_plan_digest=goal_plan_digest,
        criterion_observation_snapshot_reference=criterion_observation_snapshot_reference,
        criterion_observation_snapshot_digest=criterion_observation_snapshot_digest,
        development_plan_reference=development_plan_reference,
        development_plan_digest=development_plan_digest,
        reviewer_reference=reviewer_reference,
        purpose_code=purpose_code,
        reason_code=reason_code,
        review_period_start=review_period_start,
        review_period_end=review_period_end,
        generated_at=generated_at,
        evidence_version=evidence_version,
    )
