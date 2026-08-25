"""Authoritative activation boundary for reviewed performance-goal plans.

The boundary verifies the exact reviewed plan through an injected Orgmetra authority,
binds accountable human approval, detects plan drift across authority work, and emits
value-minimized activation evidence. Activation never grants performance-rating or
employment-decision authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from threading import RLock
from typing import Protocol
from uuid import uuid4
from weakref import WeakKeyDictionary

from orgmetra_performance_goal_plan.plan import (
    PerformanceGoalPlanPacket,
    _ALLOWED_FEEDBACK_CADENCES,
    _validate_code,
    _validate_digest,
    _validate_operational_uuid_text,
    _validate_reference,
)

_ACTIVATION_STATE = "authoritatively_activated"
_RATING_AUTHORITY = "not_authorized_for_performance_rating"
_EMPLOYMENT_DECISION_AUTHORITY = "not_authorized_for_employment_decision"
_RECEIPT_ISSUANCE_TOKEN = object()
_RECEIPT_SEALS_LOCK = RLock()
_TIMEZONE_TYPE = type(timezone.utc)


def _freeze_timestamp(value: object, field_name: str) -> datetime:
    """Require an exact datetime with built-in fixed offset and detach it to UTC."""
    if type(value) is not datetime or type(value.tzinfo) is not _TIMEZONE_TYPE:
        raise ValueError(f"{field_name} must use an exact built-in fixed-offset datetime")
    return value.astimezone(timezone.utc)


def _canonical_timestamp(value: datetime) -> str:
    """Render one already-frozen UTC instant as RFC 3339 text."""
    return value.isoformat().replace("+00:00", "Z")


def _validate_fixed_text(value: object, expected: str, field_name: str) -> None:
    """Require one exact built-in fixed governance value."""
    if type(value) is not str or value != expected:
        raise ValueError(f"{field_name} must remain {expected}")


@dataclass(frozen=True, slots=True, repr=False)
class PerformanceGoalPlanActivationVerification:
    """Transient exact-scope evidence returned by the authoritative activation adapter."""

    tenant_record_id: str
    performance_goal_plan_reference: str
    employment_record_reference: str
    job_profile_reference: str
    performance_cycle_reference: str
    goal_set_digest: str
    measurement_definition_digest: str
    feedback_cadence_code: str
    approving_actor_reference: str
    approved_at: datetime
    verified_at: datetime
    authority_evidence_reference: str
    authority_evidence_digest: str
    activation_state: str = _ACTIVATION_STATE
    rating_authority: str = _RATING_AUTHORITY
    employment_decision_authority: str = _EMPLOYMENT_DECISION_AUTHORITY
    evidence_version: int = 1

    def __repr__(self) -> str:
        """Redact correlation and provenance from routine logs."""
        return "PerformanceGoalPlanActivationVerification(<redacted>)"

    def __post_init__(self) -> None:
        """Validate transient authority evidence and normalize its timestamps."""
        payload = self.snapshot()
        object.__setattr__(self, "approved_at", payload["approved_at"])
        object.__setattr__(self, "verified_at", payload["verified_at"])

    def snapshot(self) -> dict[str, object]:
        """Snapshot and validate every authority field once before comparison."""
        payload: dict[str, object] = {
            "tenant_record_id": self.tenant_record_id,
            "performance_goal_plan_reference": self.performance_goal_plan_reference,
            "employment_record_reference": self.employment_record_reference,
            "job_profile_reference": self.job_profile_reference,
            "performance_cycle_reference": self.performance_cycle_reference,
            "goal_set_digest": self.goal_set_digest,
            "measurement_definition_digest": self.measurement_definition_digest,
            "feedback_cadence_code": self.feedback_cadence_code,
            "approving_actor_reference": self.approving_actor_reference,
            "approved_at": _freeze_timestamp(self.approved_at, "approved_at"),
            "verified_at": _freeze_timestamp(self.verified_at, "verified_at"),
            "authority_evidence_reference": self.authority_evidence_reference,
            "authority_evidence_digest": self.authority_evidence_digest,
            "activation_state": self.activation_state,
            "rating_authority": self.rating_authority,
            "employment_decision_authority": self.employment_decision_authority,
            "evidence_version": self.evidence_version,
        }
        _validate_operational_uuid_text(payload["tenant_record_id"], "tenant_record_id")
        _validate_reference(
            payload["performance_goal_plan_reference"],
            "performance_goal_plan",
            "performance_goal_plan_reference",
            require_uuid4=True,
        )
        _validate_reference(
            payload["employment_record_reference"],
            "employment_record",
            "employment_record_reference",
            require_uuid4=False,
        )
        _validate_reference(
            payload["job_profile_reference"],
            "job_profile",
            "job_profile_reference",
            require_uuid4=False,
        )
        _validate_reference(
            payload["performance_cycle_reference"],
            "performance_cycle",
            "performance_cycle_reference",
            require_uuid4=False,
        )
        _validate_digest(payload["goal_set_digest"], "goal_set_digest")
        _validate_digest(payload["measurement_definition_digest"], "measurement_definition_digest")
        _validate_code(payload["feedback_cadence_code"], "feedback_cadence_code")
        if payload["feedback_cadence_code"] not in _ALLOWED_FEEDBACK_CADENCES:
            raise ValueError("feedback_cadence_code must use the reviewed cadence vocabulary")
        _validate_reference(
            payload["approving_actor_reference"],
            "actor",
            "approving_actor_reference",
            require_uuid4=True,
        )
        if payload["verified_at"] < payload["approved_at"]:  # type: ignore[operator]
            raise ValueError("verified_at must not precede approved_at")
        _validate_reference(
            payload["authority_evidence_reference"],
            "performance_goal_authority",
            "authority_evidence_reference",
            require_uuid4=True,
        )
        _validate_digest(payload["authority_evidence_digest"], "authority_evidence_digest")
        _validate_fixed_text(payload["activation_state"], _ACTIVATION_STATE, "activation_state")
        _validate_fixed_text(payload["rating_authority"], _RATING_AUTHORITY, "rating_authority")
        _validate_fixed_text(
            payload["employment_decision_authority"],
            _EMPLOYMENT_DECISION_AUTHORITY,
            "employment_decision_authority",
        )
        if type(payload["evidence_version"]) is not int or payload["evidence_version"] != 1:
            raise ValueError("evidence_version must remain exact integer 1")
        return payload


class PerformanceGoalPlanActivationAuthority(Protocol):
    """Host-owned authority that re-resolves reviewed plan scope before activation."""

    def verify_activation(
        self,
        *,
        plan: PerformanceGoalPlanPacket,
        approving_actor_reference: str,
        approved_at: datetime,
    ) -> PerformanceGoalPlanActivationVerification:
        """Return exact-scope evidence only after authoritative checks succeed."""


@dataclass(frozen=True, slots=True, repr=False, eq=False, weakref_slot=True)
class PerformanceGoalPlanActivationReceipt:
    """Value-minimized evidence that one reviewed plan crossed authority verification."""

    activation_reference: str
    tenant_record_id: str
    performance_goal_plan_reference: str
    plan_digest: str
    approving_actor_reference: str
    approved_at: datetime
    activated_at: datetime
    authority_evidence_reference: str
    authority_evidence_digest: str
    activation_state: str = _ACTIVATION_STATE
    rating_authority: str = _RATING_AUTHORITY
    employment_decision_authority: str = _EMPLOYMENT_DECISION_AUTHORITY
    evidence_version: int = 1
    _issuance_token: object | None = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        """Redact activation correlation and provenance from routine logs."""
        return "PerformanceGoalPlanActivationReceipt(<redacted>)"

    def __post_init__(self) -> None:
        """Allow construction only through the activation factory and seal issued evidence."""
        payload = _receipt_payload(self)
        if self._issuance_token is not _RECEIPT_ISSUANCE_TOKEN:
            raise TypeError("activation receipts can only be issued by activate_performance_goal_plan")
        canonical = _canonical_receipt_json(payload)
        with _RECEIPT_SEALS_LOCK:
            _RECEIPT_SEALS[self] = sha256(canonical.encode("utf-8")).hexdigest()

    def canonical_json(self) -> str:
        """Return one verified immutable snapshot of activation audit evidence."""
        payload = _receipt_payload(self)
        canonical = _canonical_receipt_json(payload)
        with _RECEIPT_SEALS_LOCK:
            creation_digest = _RECEIPT_SEALS.get(self)
        if creation_digest is None or sha256(canonical.encode("utf-8")).hexdigest() != creation_digest:
            raise ValueError("performance goal activation evidence was altered after issuance")
        return canonical

    def sha256_digest(self) -> str:
        """Return SHA-256 over exact canonical activation evidence."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _receipt_payload(receipt: PerformanceGoalPlanActivationReceipt) -> dict[str, object]:
    """Snapshot and validate receipt fields before canonical emission."""
    payload: dict[str, object] = {
        "activation_reference": receipt.activation_reference,
        "tenant_record_id": receipt.tenant_record_id,
        "performance_goal_plan_reference": receipt.performance_goal_plan_reference,
        "plan_digest": receipt.plan_digest,
        "approving_actor_reference": receipt.approving_actor_reference,
        "approved_at": _freeze_timestamp(receipt.approved_at, "approved_at"),
        "activated_at": _freeze_timestamp(receipt.activated_at, "activated_at"),
        "authority_evidence_reference": receipt.authority_evidence_reference,
        "authority_evidence_digest": receipt.authority_evidence_digest,
        "activation_state": receipt.activation_state,
        "rating_authority": receipt.rating_authority,
        "employment_decision_authority": receipt.employment_decision_authority,
        "evidence_version": receipt.evidence_version,
    }
    _validate_reference(
        payload["activation_reference"],
        "performance_goal_activation",
        "activation_reference",
        require_uuid4=True,
    )
    _validate_operational_uuid_text(payload["tenant_record_id"], "tenant_record_id")
    _validate_reference(
        payload["performance_goal_plan_reference"],
        "performance_goal_plan",
        "performance_goal_plan_reference",
        require_uuid4=True,
    )
    _validate_digest(payload["plan_digest"], "plan_digest")
    _validate_reference(
        payload["approving_actor_reference"],
        "actor",
        "approving_actor_reference",
        require_uuid4=True,
    )
    if payload["activated_at"] < payload["approved_at"]:  # type: ignore[operator]
        raise ValueError("activated_at must not precede approved_at")
    _validate_reference(
        payload["authority_evidence_reference"],
        "performance_goal_authority",
        "authority_evidence_reference",
        require_uuid4=True,
    )
    _validate_digest(payload["authority_evidence_digest"], "authority_evidence_digest")
    _validate_fixed_text(payload["activation_state"], _ACTIVATION_STATE, "activation_state")
    _validate_fixed_text(payload["rating_authority"], _RATING_AUTHORITY, "rating_authority")
    _validate_fixed_text(
        payload["employment_decision_authority"],
        _EMPLOYMENT_DECISION_AUTHORITY,
        "employment_decision_authority",
    )
    if type(payload["evidence_version"]) is not int or payload["evidence_version"] != 1:
        raise ValueError("evidence_version must remain exact integer 1")
    return payload


def _canonical_receipt_json(payload: dict[str, object]) -> str:
    """Serialize one already-validated receipt snapshot deterministically."""
    canonical_payload = dict(payload)
    canonical_payload["approved_at"] = _canonical_timestamp(payload["approved_at"])  # type: ignore[arg-type]
    canonical_payload["activated_at"] = _canonical_timestamp(payload["activated_at"])  # type: ignore[arg-type]
    return json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def activate_performance_goal_plan(
    plan: PerformanceGoalPlanPacket,
    *,
    approving_actor_reference: str,
    approved_at: datetime,
    authority: PerformanceGoalPlanActivationAuthority,
) -> PerformanceGoalPlanActivationReceipt:
    """Activate one reviewed plan only after fresh exact-scope authoritative verification."""
    if type(plan) is not PerformanceGoalPlanPacket:
        raise TypeError("plan must be the exact governed PerformanceGoalPlanPacket type")

    plan_json = plan.canonical_json()
    plan_payload = json.loads(plan_json)
    plan_digest = sha256(plan_json.encode("utf-8")).hexdigest()
    _validate_reference(
        approving_actor_reference,
        "actor",
        "approving_actor_reference",
        require_uuid4=True,
    )
    if approving_actor_reference != plan_payload["reviewer_reference"]:
        raise ValueError("approving_actor_reference must identify the reviewed reviewer")
    approved_at_utc = _freeze_timestamp(approved_at, "approved_at")
    generated_at_utc = datetime.fromisoformat(plan_payload["generated_at"].replace("Z", "+00:00"))
    if approved_at_utc < generated_at_utc:
        raise ValueError("approved_at must not precede the reviewed plan evidence")

    verification = authority.verify_activation(
        plan=plan,
        approving_actor_reference=approving_actor_reference,
        approved_at=approved_at_utc,
    )
    if type(verification) is not PerformanceGoalPlanActivationVerification:
        raise TypeError("authority must return exact PerformanceGoalPlanActivationVerification")
    verification_payload = verification.snapshot()

    # Re-reading through the plan's own creation seal is the mutation check. A changed
    # plan cannot emit a second valid canonical truth, so no separate unreachable
    # string-inequality branch is needed here.
    plan.canonical_json()

    expected_scope = (
        plan_payload["tenant_record_id"],
        plan_payload["performance_goal_plan_reference"],
        plan_payload["employment_record_reference"],
        plan_payload["job_profile_reference"],
        plan_payload["performance_cycle_reference"],
        plan_payload["goal_set_digest"],
        plan_payload["measurement_definition_digest"],
        plan_payload["feedback_cadence_code"],
        approving_actor_reference,
        approved_at_utc,
    )
    actual_scope = (
        verification_payload["tenant_record_id"],
        verification_payload["performance_goal_plan_reference"],
        verification_payload["employment_record_reference"],
        verification_payload["job_profile_reference"],
        verification_payload["performance_cycle_reference"],
        verification_payload["goal_set_digest"],
        verification_payload["measurement_definition_digest"],
        verification_payload["feedback_cadence_code"],
        verification_payload["approving_actor_reference"],
        verification_payload["approved_at"],
    )
    if actual_scope != expected_scope:
        raise ValueError("authority verification scope does not match the reviewed goal plan")

    receipt = PerformanceGoalPlanActivationReceipt(
        activation_reference=f"performance_goal_activation:{uuid4()}",
        tenant_record_id=plan_payload["tenant_record_id"],
        performance_goal_plan_reference=plan_payload["performance_goal_plan_reference"],
        plan_digest=plan_digest,
        approving_actor_reference=approving_actor_reference,
        approved_at=approved_at_utc,
        activated_at=verification_payload["verified_at"],  # type: ignore[arg-type]
        authority_evidence_reference=verification_payload["authority_evidence_reference"],  # type: ignore[arg-type]
        authority_evidence_digest=verification_payload["authority_evidence_digest"],  # type: ignore[arg-type]
        _issuance_token=_RECEIPT_ISSUANCE_TOKEN,
    )
    object.__setattr__(receipt, "_issuance_token", None)
    return receipt


_RECEIPT_SEALS: WeakKeyDictionary[PerformanceGoalPlanActivationReceipt, str] = WeakKeyDictionary()
