"""Governed, aggregate-only selection-outcome monitoring plan evidence.

The packet binds one Job-scoped total selection process to exact aggregate snapshot,
protected-attribute handling, small-sample interpretation, and statistical-plan evidence.
It carries no candidate identities, protected-attribute values, scores, or decisions and
does not itself compute or assert adverse impact.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
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
_PROCESS_PLAN_SEAL_KEY = secrets.token_bytes(32)
_PLAN_SEALS: dict[int, str] = {}
_ISSUED_PLAN_IDENTITIES: WeakValueDictionary[int, object] = WeakValueDictionary()
_PLAN_SEALS_LOCK = RLock()


def _discard_plan_seal(plan_id: int) -> None:
    """Discard process-local seal bytes without resetting live issuance identity."""
    with _PLAN_SEALS_LOCK:
        _PLAN_SEALS.pop(plan_id, None)


def _register_plan_seal(plan: object, seal: str) -> None:
    """Atomically bind one live monitoring-plan identity to one issuance seal."""
    plan_id = id(plan)
    with _PLAN_SEALS_LOCK:
        if _ISSUED_PLAN_IDENTITIES.get(plan_id) is plan:
            raise ValueError("selection monitoring plan issuance evidence already exists")
        _PLAN_SEALS[plan_id] = seal
        _ISSUED_PLAN_IDENTITIES[plan_id] = plan
    finalize(plan, _discard_plan_seal, plan_id)


def _authoritative_plan_seal(plan: object) -> str | None:
    """Return process-local issuance evidence without trusting plan-owned state."""
    with _PLAN_SEALS_LOCK:
        return _PLAN_SEALS.get(id(plan))


def _seal_plan(payload_json: str) -> str:
    """Bind one process-local issuance to its exact canonical monitoring-plan bytes."""
    return hmac.new(_PROCESS_PLAN_SEAL_KEY, payload_json.encode("utf-8"), "sha256").hexdigest()


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
    """Require an expected namespace plus a canonical opaque UUIDv4 suffix."""
    error_message = f"{field_name} must be an opaque {prefix}: reference"
    if (
        type(value) is not str
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
    """Require exact built-in lowercase SHA-256 hexadecimal evidence."""
    if type(value) is not str or not _DIGEST_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _freeze_timestamp(value: datetime) -> datetime:
    """Resolve caller timezone behavior once and store one immutable UTC instant."""
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError("generated_at must be an exact timezone-aware datetime")
    try:
        offset = value.utcoffset()
    except Exception as exc:
        raise ValueError("generated_at must be an exact timezone-aware datetime") from exc
    if type(offset) is not timedelta:
        raise ValueError("generated_at must be an exact timezone-aware datetime")
    try:
        frozen = (value.replace(tzinfo=None) - offset).replace(tzinfo=timezone.utc)
    except (OverflowError, ValueError) as exc:
        raise ValueError("generated_at must be an exact timezone-aware datetime") from exc
    if frozen > datetime.now(timezone.utc):
        raise ValueError("generated_at must not be in the future")
    return frozen


def _canonical_timestamp(value: datetime) -> str:
    """Render one already-frozen UTC instant as precision-preserving RFC 3339 text."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError("generated_at must be an exact timezone-aware datetime")
    return value.isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True, repr=False, weakref_slot=True)
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
        if type(self.monitoring_start) is not date:
            raise ValueError("monitoring_start must be a calendar date")
        if type(self.monitoring_end) is not date:
            raise ValueError("monitoring_end must be a calendar date")
        if self.monitoring_end < self.monitoring_start:
            raise ValueError("monitoring_end must not precede monitoring_start")
        _validate_code(self.purpose_code, "purpose_code")
        if self.purpose_code != _PURPOSE_CODE:
            raise ValueError("purpose_code must remain selection_outcome_monitoring")
        _validate_code(self.reason_code, "reason_code")
        if self.reason_code not in _ALLOWED_REASON_CODES:
            raise ValueError("reason_code must use a reviewed non-sensitive monitoring reason")
        object.__setattr__(self, "generated_at", _freeze_timestamp(self.generated_at))
        if type(self.evidence_version) is not int or not 1 <= self.evidence_version <= 2_147_483_647:
            raise ValueError("evidence_version must be an integer from 1 through 2147483647")
        if type(self.analysis_scope) is not str or self.analysis_scope != _ANALYSIS_SCOPE:
            raise ValueError("analysis_scope must remain total_selection_process_by_job")
        if self.contains_individual_records is not False:
            raise ValueError("monitoring plan must remain aggregate-only")
        if self.human_confirmation_required is not True:
            raise ValueError("human confirmation is mandatory before monitoring use")
        if type(self.decision_authority) is not str or self.decision_authority != _DECISION_AUTHORITY:
            raise ValueError("decision_authority must remain human_review_only")
        if type(self.review_state) is not str or self.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain requires_human_review")
        if type(self.next_action) is not str or self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed monitoring instruction")
        _register_plan_seal(self, _seal_plan(_canonical_plan_json_unchecked(self)))

    def __repr__(self) -> str:
        """Return a fully redacted representation safe for routine logs and assertions."""
        return "SelectionOutcomeMonitoringPlan(<redacted>)"

    def canonical_json(self) -> str:
        """Return issuance-verified deterministic JSON for immutable audit correlation."""
        payload_json = _canonical_plan_json_unchecked(self)
        authoritative_seal = _authoritative_plan_seal(self)
        if authoritative_seal is None:
            raise ValueError("selection monitoring plan issuance evidence is unavailable")
        if not hmac.compare_digest(authoritative_seal, _seal_plan(payload_json)):
            raise ValueError("selection monitoring plan evidence changed after issuance")
        return payload_json

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact issuance-verified UTF-8 monitoring plan."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _canonical_plan_json_unchecked(plan: SelectionOutcomeMonitoringPlan) -> str:
    """Render canonical bytes without consulting process-local issuance state."""
    payload = {
        "actor_reference": plan.actor_reference,
        "analysis_scope": plan.analysis_scope,
        "contains_individual_records": plan.contains_individual_records,
        "decision_authority": plan.decision_authority,
        "evidence_version": plan.evidence_version,
        "generated_at": _canonical_timestamp(plan.generated_at),
        "human_confirmation_required": plan.human_confirmation_required,
        "job_profile_reference": plan.job_profile_reference,
        "monitoring_end": plan.monitoring_end.isoformat(),
        "monitoring_plan_reference": plan.monitoring_plan_reference,
        "monitoring_start": plan.monitoring_start.isoformat(),
        "next_action": plan.next_action,
        "outcome_snapshot_digest": plan.outcome_snapshot_digest,
        "outcome_snapshot_reference": plan.outcome_snapshot_reference,
        "population_snapshot_digest": plan.population_snapshot_digest,
        "population_snapshot_reference": plan.population_snapshot_reference,
        "protected_attribute_policy_digest": plan.protected_attribute_policy_digest,
        "protected_attribute_policy_reference": plan.protected_attribute_policy_reference,
        "purpose_code": plan.purpose_code,
        "reason_code": plan.reason_code,
        "review_state": plan.review_state,
        "reviewer_reference": plan.reviewer_reference,
        "selection_process_reference": plan.selection_process_reference,
        "small_sample_policy_digest": plan.small_sample_policy_digest,
        "small_sample_policy_reference": plan.small_sample_policy_reference,
        "statistical_plan_digest": plan.statistical_plan_digest,
        "statistical_plan_reference": plan.statistical_plan_reference,
        "tenant_record_id": plan.tenant_record_id,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


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
