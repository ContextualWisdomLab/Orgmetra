"""Governed performance-goal plan activation evidence.

The packet keeps goal text and performance ratings outside durable governance
evidence while binding the exact reviewed scope, provenance, feedback cadence,
and accountable human actors required before goal-plan activation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from threading import RLock
from uuid import UUID
from weakref import ReferenceType, WeakKeyDictionary, ref

_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_MAX_UUID_INT = (1 << 128) - 1
_TIMEZONE_TYPE = type(timezone.utc)
_PURPOSE_CODE = "performance_goal_plan_review"
_REASON_CODE = "goal_plan_activation_review"
_ALLOWED_FEEDBACK_CADENCES = frozenset(
    {"continuous_feedback", "monthly_check_in", "quarterly_check_in"}
)
_REVIEW_STATE = "requires_human_review"
_DECISION_AUTHORITY = "not_authorized_for_performance_rating"
_EMPLOYMENT_DECISION_AUTHORITY = "not_authorized_for_employment_decision"
_NEXT_ACTION = (
    "Within tenant_record_id, re-resolve the Employment, Job, performance cycle, requester, "
    "reviewer, goal-set digest, and measurement-definition digest through authoritative "
    "Orgmetra boundaries; confirm the reviewer is accountable and distinct from the requester; "
    "then activate the reviewed goal plan through the authoritative performance workflow. "
    "Do not use this packet as a performance rating or employment decision."
)

_REGISTRY_LOCK = RLock()
_CREATION_DIGESTS: WeakKeyDictionary[PerformanceGoalPlanPacket, str] = WeakKeyDictionary()
_LIVE_REFERENCES: dict[
    tuple[str, str], dict[ReferenceType[PerformanceGoalPlanPacket], str]
] = {}


def _release_live_reference(
    plan_key: tuple[str, str],
    packet_reference: ReferenceType[PerformanceGoalPlanPacket],
) -> None:
    """Forget one dead packet without dropping another live packet for the key."""
    with _REGISTRY_LOCK:
        live_evidence = _LIVE_REFERENCES[plan_key]
        live_evidence.pop(packet_reference, None)
        if not live_evidence:
            _LIVE_REFERENCES.pop(plan_key, None)


def _validate_operational_uuid_text(value: object, field_name: str) -> None:
    """Require exact canonical non-sentinel UUID text owned by the HRIS boundary."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be canonical UUID text")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{field_name} must be canonical UUID text") from exc
    if str(parsed) != value or parsed.int in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be a canonical operational UUID")


def _validate_reference(
    value: object,
    prefix: str,
    field_name: str,
    *,
    require_uuid4: bool,
) -> None:
    """Require one namespaced canonical UUID reference with the requested ownership rule."""
    error = f"{field_name} must be a canonical {prefix}: reference"
    if type(value) is not str or len(value) > 160 or not value.startswith(f"{prefix}:"):
        raise ValueError(error)
    suffix = value[len(prefix) + 1 :]
    try:
        parsed = UUID(suffix)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(error) from exc
    if str(parsed) != suffix or parsed.int in (0, _MAX_UUID_INT):
        raise ValueError(error)
    if require_uuid4 and parsed.version != 4:
        raise ValueError(error)


def _validate_digest(value: object, field_name: str) -> None:
    """Require exact built-in lowercase SHA-256 hexadecimal evidence."""
    if type(value) is not str or not _DIGEST_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _validate_code(value: object, field_name: str) -> None:
    """Require exact bounded two-or-more-word lower snake_case governance text."""
    if (
        type(value) is not str
        or len(value) > 64
        or not _CODE_PATTERN.fullmatch(value)
    ):
        raise ValueError(f"{field_name} must be bounded lower snake_case governance text")


def _canonical_timestamp(value: object) -> str:
    """Render one exact datetime with a built-in fixed offset as UTC RFC 3339 text."""
    if type(value) is not datetime or type(value.tzinfo) is not _TIMEZONE_TYPE:
        raise ValueError("generated_at must use a built-in fixed-offset timezone")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_positive_int(value: object, field_name: str, *, maximum: int) -> None:
    """Require one exact positive bounded built-in integer."""
    if type(value) is not int or value < 1 or value > maximum:
        raise ValueError(f"{field_name} must be an integer from 1 through {maximum}")


def _payload(packet: PerformanceGoalPlanPacket) -> dict[str, object]:
    """Snapshot trust-bearing fields once for validation and canonical emission."""
    return {
        "contains_employment_decision": packet.contains_employment_decision,
        "contains_goal_text": packet.contains_goal_text,
        "contains_performance_rating": packet.contains_performance_rating,
        "decision_authority": packet.decision_authority,
        "employment_decision_authority": packet.employment_decision_authority,
        "employment_record_reference": packet.employment_record_reference,
        "evidence_version": packet.evidence_version,
        "feedback_cadence_code": packet.feedback_cadence_code,
        "generated_at": _canonical_timestamp(packet.generated_at),
        "goal_count": packet.goal_count,
        "goal_set_digest": packet.goal_set_digest,
        "human_review_required": packet.human_review_required,
        "job_profile_reference": packet.job_profile_reference,
        "measurement_definition_digest": packet.measurement_definition_digest,
        "next_action": packet.next_action,
        "performance_cycle_reference": packet.performance_cycle_reference,
        "performance_goal_plan_reference": packet.performance_goal_plan_reference,
        "purpose_code": packet.purpose_code,
        "reason_code": packet.reason_code,
        "requester_reference": packet.requester_reference,
        "review_state": packet.review_state,
        "reviewer_reference": packet.reviewer_reference,
        "tenant_record_id": packet.tenant_record_id,
    }


def _canonical_payload_json(payload: dict[str, object]) -> str:
    """Serialize one already-snapshotted payload deterministically."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True, slots=True, repr=False, eq=False, weakref_slot=True)
class PerformanceGoalPlanPacket:
    """Value-minimized, human-reviewed evidence for one goal-plan activation."""

    tenant_record_id: str
    performance_goal_plan_reference: str
    employment_record_reference: str
    job_profile_reference: str
    performance_cycle_reference: str
    goal_set_digest: str
    measurement_definition_digest: str
    goal_count: int
    feedback_cadence_code: str
    requester_reference: str
    reviewer_reference: str
    purpose_code: str
    reason_code: str
    generated_at: datetime
    evidence_version: int = 1
    contains_goal_text: bool = False
    contains_performance_rating: bool = False
    contains_employment_decision: bool = False
    human_review_required: bool = True
    review_state: str = _REVIEW_STATE
    decision_authority: str = _DECISION_AUTHORITY
    employment_decision_authority: str = _EMPLOYMENT_DECISION_AUTHORITY
    next_action: str = _NEXT_ACTION

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Keep governed packet behavior final so subclasses cannot override exports."""
        raise TypeError("PerformanceGoalPlanPacket is final")

    def __repr__(self) -> str:
        """Return a representation that never emits worker or goal correlation evidence."""
        return "PerformanceGoalPlanPacket(<redacted>)"

    def __post_init__(self) -> None:
        """Validate the governed contract and bind one live plan reference to its evidence."""
        _validate_operational_uuid_text(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.performance_goal_plan_reference,
            "performance_goal_plan",
            "performance_goal_plan_reference",
            require_uuid4=True,
        )
        _validate_reference(
            self.employment_record_reference,
            "employment_record",
            "employment_record_reference",
            require_uuid4=False,
        )
        _validate_reference(
            self.job_profile_reference,
            "job_profile",
            "job_profile_reference",
            require_uuid4=False,
        )
        _validate_reference(
            self.performance_cycle_reference,
            "performance_cycle",
            "performance_cycle_reference",
            require_uuid4=False,
        )
        _validate_digest(self.goal_set_digest, "goal_set_digest")
        _validate_digest(self.measurement_definition_digest, "measurement_definition_digest")
        _validate_positive_int(self.goal_count, "goal_count", maximum=20)
        _validate_code(self.feedback_cadence_code, "feedback_cadence_code")
        if self.feedback_cadence_code not in _ALLOWED_FEEDBACK_CADENCES:
            raise ValueError("feedback_cadence_code must use the reviewed cadence vocabulary")
        _validate_reference(
            self.requester_reference,
            "actor",
            "requester_reference",
            require_uuid4=True,
        )
        _validate_reference(
            self.reviewer_reference,
            "actor",
            "reviewer_reference",
            require_uuid4=True,
        )
        if self.requester_reference == self.reviewer_reference:
            raise ValueError("reviewer_reference must identify a different accountable actor")
        _validate_code(self.purpose_code, "purpose_code")
        if self.purpose_code != _PURPOSE_CODE:
            raise ValueError("purpose_code must remain performance_goal_plan_review")
        _validate_code(self.reason_code, "reason_code")
        if self.reason_code != _REASON_CODE:
            raise ValueError("reason_code must remain goal_plan_activation_review")
        _canonical_timestamp(self.generated_at)
        _validate_positive_int(self.evidence_version, "evidence_version", maximum=2_147_483_647)
        if self.contains_goal_text is not False:
            raise ValueError("goal-plan evidence must not contain goal text")
        if self.contains_performance_rating is not False:
            raise ValueError("goal-plan evidence must not contain a performance rating")
        if self.contains_employment_decision is not False:
            raise ValueError("goal-plan evidence must not contain an employment decision")
        if self.human_review_required is not True:
            raise ValueError("human review is mandatory before goal-plan activation")
        _validate_code(self.review_state, "review_state")
        if self.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain requires_human_review")
        _validate_code(self.decision_authority, "decision_authority")
        if self.decision_authority != _DECISION_AUTHORITY:
            raise ValueError("decision_authority must remain not_authorized_for_performance_rating")
        _validate_code(self.employment_decision_authority, "employment_decision_authority")
        if self.employment_decision_authority != _EMPLOYMENT_DECISION_AUTHORITY:
            raise ValueError(
                "employment_decision_authority must remain not_authorized_for_employment_decision"
            )
        if type(self.next_action) is not str or self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed activation instruction")

        payload_json = _canonical_payload_json(_payload(self))
        creation_digest = sha256(payload_json.encode("utf-8")).hexdigest()
        key = (self.tenant_record_id, self.performance_goal_plan_reference)
        with _REGISTRY_LOCK:
            live_evidence = _LIVE_REFERENCES.get(key)
            if live_evidence is not None:
                if any(
                    live_digest != creation_digest
                    for live_digest in live_evidence.values()
                ):
                    raise ValueError(
                        "performance goal-plan reference is bound to different live evidence"
                    )
            else:
                live_evidence = {}
                _LIVE_REFERENCES[key] = live_evidence
            _CREATION_DIGESTS[self] = creation_digest
            packet_reference = ref(
                self,
                lambda dead_reference, plan_key=key: _release_live_reference(
                    plan_key,
                    dead_reference,
                ),
            )
            live_evidence[packet_reference] = creation_digest

    def canonical_json(self) -> str:
        """Return one verified snapshot of deterministic canonical audit evidence."""
        payload_json = _canonical_payload_json(_payload(self))
        current_digest = sha256(payload_json.encode("utf-8")).hexdigest()
        with _REGISTRY_LOCK:
            creation_digest = _CREATION_DIGESTS.get(self)
        if creation_digest is None:
            raise ValueError(
                "performance goal-plan evidence was not issued through the governed constructor"
            )
        if current_digest != creation_digest:
            raise ValueError("performance goal-plan evidence changed after issuance")
        return payload_json

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact verified canonical UTF-8 evidence."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_performance_goal_plan_packet(
    *,
    tenant_record_id: str,
    performance_goal_plan_reference: str,
    employment_record_reference: str,
    job_profile_reference: str,
    performance_cycle_reference: str,
    goal_set_digest: str,
    measurement_definition_digest: str,
    goal_count: int,
    feedback_cadence_code: str,
    requester_reference: str,
    reviewer_reference: str,
    purpose_code: str,
    reason_code: str,
    generated_at: datetime,
    evidence_version: int = 1,
) -> PerformanceGoalPlanPacket:
    """Build value-minimized goal-plan evidence pending accountable human activation."""
    return PerformanceGoalPlanPacket(
        tenant_record_id=tenant_record_id,
        performance_goal_plan_reference=performance_goal_plan_reference,
        employment_record_reference=employment_record_reference,
        job_profile_reference=job_profile_reference,
        performance_cycle_reference=performance_cycle_reference,
        goal_set_digest=goal_set_digest,
        measurement_definition_digest=measurement_definition_digest,
        goal_count=goal_count,
        feedback_cadence_code=feedback_cadence_code,
        requester_reference=requester_reference,
        reviewer_reference=reviewer_reference,
        purpose_code=purpose_code,
        reason_code=reason_code,
        generated_at=generated_at,
        evidence_version=evidence_version,
    )
