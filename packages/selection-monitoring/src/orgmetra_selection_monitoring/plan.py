"""Governed, aggregate-only selection-outcome monitoring plan evidence.

The packet binds one Job-scoped total selection process to exact aggregate snapshot,
protected-attribute handling, small-sample interpretation, and statistical-plan evidence.
It carries no candidate identities, protected-attribute values, scores, or decisions and
does not itself compute or assert adverse impact.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import re
from uuid import UUID

_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]{1,31}:[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$"
)
_PURPOSE_CODE = "selection_outcome_monitoring"
_ANALYSIS_SCOPE = "total_selection_process_by_job"
_REVIEW_STATE = "requires_human_review"
_DECISION_AUTHORITY = "human_review_only"
_ALLOWED_REASON_CODES = frozenset({"quarterly_selection_governance"})
_NEXT_ACTION = (
    "Within tenant_record_id, re-resolve every packet reference through its authoritative "
    "boundary; specifically re-resolve actor_reference and reviewer_reference and verify "
    "their resolved actor identities are distinct; then verify Job scope, aggregate "
    "population completeness, protected-attribute handling, small-sample policy, and "
    "statistical-plan provenance before submitting the aggregate evidence to an authorized "
    "analyst and accountable human reviewer for any employment-process change or legal "
    "conclusion."
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


@dataclass(frozen=True, slots=True, repr=False)
class SelectionOutcomeMonitoringPlan:
    """Immutable aggregate-monitoring plan awaiting accountable human review."""

    tenant_record_id: str
    monitoring_plan_reference: str
    job_profile_reference: str
    selection_process_reference: str
    population_snapshot_reference: str
    population_snapshot_digest: str
    outcome_snapshot_reference: str
    outcome_snapshot_digest: str
    protected_attribute_policy_reference: str
    protected_attribute_policy_digest: str
    small_sample_policy_reference: str
    small_sample_policy_digest: str
    statistical_plan_reference: str
    statistical_plan_digest: str
    actor_reference: str
    reviewer_reference: str
    monitoring_start: date
    monitoring_end: date
    purpose_code: str
    reason_code: str
    generated_at: datetime
    evidence_version: int = 1
    analysis_scope: str = _ANALYSIS_SCOPE
    contains_individual_records: bool = False
    human_confirmation_required: bool = True
    decision_authority: str = _DECISION_AUTHORITY
    review_state: str = _REVIEW_STATE
    next_action: str = _NEXT_ACTION

    def __post_init__(self) -> None:
        """Fail closed when direct construction drifts from the governed contract."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.monitoring_plan_reference,
            "selection_monitoring_plan",
            "monitoring_plan_reference",
        )
        _validate_reference(self.job_profile_reference, "job_profile", "job_profile_reference")
        _validate_reference(
            self.selection_process_reference,
            "selection_process",
            "selection_process_reference",
        )
        _validate_reference(
            self.population_snapshot_reference,
            "population_snapshot",
            "population_snapshot_reference",
        )
        _validate_digest(self.population_snapshot_digest, "population_snapshot_digest")
        _validate_reference(
            self.outcome_snapshot_reference,
            "selection_outcome_snapshot",
            "outcome_snapshot_reference",
        )
        _validate_digest(self.outcome_snapshot_digest, "outcome_snapshot_digest")
        _validate_reference(
            self.protected_attribute_policy_reference,
            "protected_attribute_policy",
            "protected_attribute_policy_reference",
        )
        _validate_digest(
            self.protected_attribute_policy_digest,
            "protected_attribute_policy_digest",
        )
        _validate_reference(
            self.small_sample_policy_reference,
            "small_sample_policy",
            "small_sample_policy_reference",
        )
        _validate_digest(self.small_sample_policy_digest, "small_sample_policy_digest")
        _validate_reference(
            self.statistical_plan_reference,
            "statistical_plan",
            "statistical_plan_reference",
        )
        _validate_digest(self.statistical_plan_digest, "statistical_plan_digest")
        _validate_reference(self.actor_reference, "actor", "actor_reference")
        _validate_reference(self.reviewer_reference, "actor", "reviewer_reference")
        if self.actor_reference == self.reviewer_reference:
            raise ValueError("reviewer_reference must identify a different accountable actor")
        if not isinstance(self.monitoring_start, date) or isinstance(self.monitoring_start, datetime):
            raise ValueError("monitoring_start must be a calendar date")
        if not isinstance(self.monitoring_end, date) or isinstance(self.monitoring_end, datetime):
            raise ValueError("monitoring_end must be a calendar date")
        if self.monitoring_end < self.monitoring_start:
            raise ValueError("monitoring_end must not precede monitoring_start")
        _validate_code(self.purpose_code, "purpose_code")
        if self.purpose_code != _PURPOSE_CODE:
            raise ValueError("purpose_code must remain selection_outcome_monitoring")
        _validate_code(self.reason_code, "reason_code")
        if self.reason_code not in _ALLOWED_REASON_CODES:
            raise ValueError("reason_code must use a reviewed non-sensitive monitoring reason")
        _canonical_timestamp(self.generated_at)
        if type(self.evidence_version) is not int or not 1 <= self.evidence_version <= 2_147_483_647:
            raise ValueError("evidence_version must be an integer from 1 through 2147483647")
        if self.analysis_scope != _ANALYSIS_SCOPE:
            raise ValueError("analysis_scope must remain total_selection_process_by_job")
        if self.contains_individual_records is not False:
            raise ValueError("monitoring plan must remain aggregate-only")
        if self.human_confirmation_required is not True:
            raise ValueError("human confirmation is mandatory before monitoring use")
        if self.decision_authority != _DECISION_AUTHORITY:
            raise ValueError("decision_authority must remain human_review_only")
        if self.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain requires_human_review")
        if self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed monitoring instruction")

    def __repr__(self) -> str:
        """Return a fully redacted representation safe for routine logs and assertions."""
        return "SelectionOutcomeMonitoringPlan(<redacted>)"

    def canonical_json(self) -> str:
        """Return deterministic canonical JSON for immutable audit correlation."""
        payload = {
            "actor_reference": self.actor_reference,
            "analysis_scope": self.analysis_scope,
            "contains_individual_records": self.contains_individual_records,
            "decision_authority": self.decision_authority,
            "evidence_version": self.evidence_version,
            "generated_at": _canonical_timestamp(self.generated_at),
            "human_confirmation_required": self.human_confirmation_required,
            "job_profile_reference": self.job_profile_reference,
            "monitoring_end": self.monitoring_end.isoformat(),
            "monitoring_plan_reference": self.monitoring_plan_reference,
            "monitoring_start": self.monitoring_start.isoformat(),
            "next_action": self.next_action,
            "outcome_snapshot_digest": self.outcome_snapshot_digest,
            "outcome_snapshot_reference": self.outcome_snapshot_reference,
            "population_snapshot_digest": self.population_snapshot_digest,
            "population_snapshot_reference": self.population_snapshot_reference,
            "protected_attribute_policy_digest": self.protected_attribute_policy_digest,
            "protected_attribute_policy_reference": self.protected_attribute_policy_reference,
            "purpose_code": self.purpose_code,
            "reason_code": self.reason_code,
            "review_state": self.review_state,
            "reviewer_reference": self.reviewer_reference,
            "selection_process_reference": self.selection_process_reference,
            "small_sample_policy_digest": self.small_sample_policy_digest,
            "small_sample_policy_reference": self.small_sample_policy_reference,
            "statistical_plan_digest": self.statistical_plan_digest,
            "statistical_plan_reference": self.statistical_plan_reference,
            "tenant_record_id": self.tenant_record_id,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical UTF-8 monitoring plan."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_selection_outcome_monitoring_plan(
    *,
    tenant_record_id: str,
    monitoring_plan_reference: str,
    job_profile_reference: str,
    selection_process_reference: str,
    population_snapshot_reference: str,
    population_snapshot_digest: str,
    outcome_snapshot_reference: str,
    outcome_snapshot_digest: str,
    protected_attribute_policy_reference: str,
    protected_attribute_policy_digest: str,
    small_sample_policy_reference: str,
    small_sample_policy_digest: str,
    statistical_plan_reference: str,
    statistical_plan_digest: str,
    actor_reference: str,
    reviewer_reference: str,
    monitoring_start: date,
    monitoring_end: date,
    purpose_code: str,
    reason_code: str,
    generated_at: datetime,
    evidence_version: int = 1,
) -> SelectionOutcomeMonitoringPlan:
    """Build an aggregate-only monitoring plan pending accountable human review."""
    return SelectionOutcomeMonitoringPlan(
        tenant_record_id=tenant_record_id,
        monitoring_plan_reference=monitoring_plan_reference,
        job_profile_reference=job_profile_reference,
        selection_process_reference=selection_process_reference,
        population_snapshot_reference=population_snapshot_reference,
        population_snapshot_digest=population_snapshot_digest,
        outcome_snapshot_reference=outcome_snapshot_reference,
        outcome_snapshot_digest=outcome_snapshot_digest,
        protected_attribute_policy_reference=protected_attribute_policy_reference,
        protected_attribute_policy_digest=protected_attribute_policy_digest,
        small_sample_policy_reference=small_sample_policy_reference,
        small_sample_policy_digest=small_sample_policy_digest,
        statistical_plan_reference=statistical_plan_reference,
        statistical_plan_digest=statistical_plan_digest,
        actor_reference=actor_reference,
        reviewer_reference=reviewer_reference,
        monitoring_start=monitoring_start,
        monitoring_end=monitoring_end,
        purpose_code=purpose_code,
        reason_code=reason_code,
        generated_at=generated_at,
        evidence_version=evidence_version,
    )
