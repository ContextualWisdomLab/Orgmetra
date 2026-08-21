"""Governed pre-mutation compensation-change review evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
import re
from typing import Final
from uuid import UUID

_DIGEST_PATTERN: Final = re.compile(r"[0-9a-f]{64}")
_CODE_PATTERN: Final = re.compile(r"[a-z][a-z0-9_]{0,63}")
_MAX_REFERENCE_LENGTH: Final = 160
_SENTINEL_UUIDS: Final = {0, (1 << 128) - 1}
_ALLOWED_REASON_CODES: Final = frozenset(
    {
        "annual_compensation_review",
        "promotion_adjustment",
        "market_adjustment",
        "internal_equity_adjustment",
        "approved_retention_adjustment",
    }
)
_NEXT_ACTION: Final = (
    "Re-resolve every packet reference in tenant_record_id, prove requester and reviewer "
    "resolve to distinct authoritative actor identities, prove the Person-to-Employment and "
    "active Assignment/Job/Position scope, then verify exact current/proposed compensation, "
    "policy, pay-equity review, budget authorization, effective date, and payroll handoff "
    "provenance before human approval or any People mutation."
)


def _validate_operational_uuid(value: str, field_name: str) -> None:
    """Require a canonical non-sentinel operational UUID accepted by core HRIS."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be canonical UUID text")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{field_name} must be canonical UUID text") from exc
    if str(parsed) != value or parsed.int in _SENTINEL_UUIDS:
        raise ValueError(f"{field_name} must be a canonical operational UUID")


def _validate_reference(value: str, prefix: str, field_name: str) -> None:
    """Require a value-minimized canonical non-sentinel UUIDv4 namespaced reference."""
    message = f"{field_name} must be an opaque {prefix}: reference"
    namespace = f"{prefix}:"
    if (
        not isinstance(value, str)
        or len(value) > _MAX_REFERENCE_LENGTH
        or not value.startswith(namespace)
    ):
        raise ValueError(message)
    suffix = value.split(":", 1)[1]
    try:
        parsed = UUID(suffix)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(message) from exc
    if str(parsed) != suffix or parsed.version != 4 or parsed.int in _SENTINEL_UUIDS:
        raise ValueError(message)


def _validate_digest(value: str, field_name: str) -> None:
    """Require lowercase SHA-256 hexadecimal evidence."""
    if not isinstance(value, str) or not _DIGEST_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _canonical_timestamp(value: datetime) -> str:
    """Render an aware instant as precision-preserving UTC RFC 3339 text."""
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware exact datetime")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_business_date(value: date, field_name: str) -> None:
    """Require a business date rather than a datetime or textual date."""
    if type(value) is not date:
        raise ValueError(f"{field_name} must be a date")


def _validate_evidence_version(value: int) -> None:
    """Require a bounded positive integer version for high-impact review evidence."""
    if type(value) is not int or value < 1 or value > 2_147_483_647:
        raise ValueError("evidence_version must be an integer from 1 through 2147483647")


@dataclass(frozen=True, slots=True)
class CompensationChangeReviewPacket:
    """Value-minimized evidence envelope for human compensation-change review."""

    tenant_record_id: str
    compensation_review_reference: str
    person_record_reference: str
    employment_record_reference: str
    active_assignment_snapshot_reference: str
    active_assignment_snapshot_digest: str
    current_compensation_snapshot_reference: str
    current_compensation_snapshot_digest: str
    proposed_compensation_plan_reference: str
    proposed_compensation_plan_digest: str
    compensation_policy_reference: str
    compensation_policy_digest: str
    pay_equity_review_reference: str
    pay_equity_review_digest: str
    budget_authorization_reference: str
    budget_authorization_digest: str
    payroll_handoff_plan_reference: str
    payroll_handoff_plan_digest: str
    requester_reference: str
    reviewer_reference: str
    proposed_effective_on: date
    purpose_code: str
    reason_code: str
    evidence_version: int
    generated_at: datetime
    review_state: str = "requires_human_review"
    mutation_authorized: bool = False
    scope_verification_state: str = "requires_authoritative_resolution"
    next_action: str = _NEXT_ACTION

    def __post_init__(self) -> None:
        """Validate privacy, scope-correlation, timing, and high-impact review invariants."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        reference_prefixes = {
            "compensation_review_reference": "compensation_change_review",
            "person_record_reference": "person_record",
            "employment_record_reference": "employment_record",
            "active_assignment_snapshot_reference": "active_assignment_snapshot",
            "current_compensation_snapshot_reference": "compensation_snapshot",
            "proposed_compensation_plan_reference": "compensation_plan",
            "compensation_policy_reference": "compensation_policy",
            "pay_equity_review_reference": "pay_equity_review",
            "budget_authorization_reference": "budget_authorization",
            "payroll_handoff_plan_reference": "payroll_handoff_plan",
            "requester_reference": "actor",
            "reviewer_reference": "actor",
        }
        for field_name, prefix in reference_prefixes.items():
            _validate_reference(getattr(self, field_name), prefix, field_name)

        if self.requester_reference == self.reviewer_reference:
            raise ValueError("requester_reference and reviewer_reference must be different actor references")

        digest_fields = (
            "active_assignment_snapshot_digest",
            "current_compensation_snapshot_digest",
            "proposed_compensation_plan_digest",
            "compensation_policy_digest",
            "pay_equity_review_digest",
            "budget_authorization_digest",
            "payroll_handoff_plan_digest",
        )
        for field_name in digest_fields:
            _validate_digest(getattr(self, field_name), field_name)

        _validate_business_date(self.proposed_effective_on, "proposed_effective_on")
        if self.purpose_code != "compensation_change_review":
            raise ValueError("purpose_code must remain compensation_change_review")
        if self.reason_code not in _ALLOWED_REASON_CODES:
            raise ValueError("reason_code must be an approved non-sensitive compensation-review category")
        _validate_evidence_version(self.evidence_version)
        _canonical_timestamp(self.generated_at)
        if self.review_state != "requires_human_review":
            raise ValueError("review_state must remain requires_human_review")
        if type(self.mutation_authorized) is not bool or self.mutation_authorized:
            raise ValueError("mutation_authorized must remain false")
        if self.scope_verification_state != "requires_authoritative_resolution":
            raise ValueError("scope_verification_state must remain requires_authoritative_resolution")
        if self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed approval instruction")

    def to_dict(self) -> dict[str, object]:
        """Return canonical value-minimized audit evidence without compensation values."""
        return {
            "active_assignment_snapshot_digest": self.active_assignment_snapshot_digest,
            "active_assignment_snapshot_reference": self.active_assignment_snapshot_reference,
            "budget_authorization_digest": self.budget_authorization_digest,
            "budget_authorization_reference": self.budget_authorization_reference,
            "compensation_policy_digest": self.compensation_policy_digest,
            "compensation_policy_reference": self.compensation_policy_reference,
            "compensation_review_reference": self.compensation_review_reference,
            "current_compensation_snapshot_digest": self.current_compensation_snapshot_digest,
            "current_compensation_snapshot_reference": self.current_compensation_snapshot_reference,
            "employment_record_reference": self.employment_record_reference,
            "evidence_version": self.evidence_version,
            "generated_at": _canonical_timestamp(self.generated_at),
            "mutation_authorized": self.mutation_authorized,
            "next_action": self.next_action,
            "pay_equity_review_digest": self.pay_equity_review_digest,
            "pay_equity_review_reference": self.pay_equity_review_reference,
            "payroll_handoff_plan_digest": self.payroll_handoff_plan_digest,
            "payroll_handoff_plan_reference": self.payroll_handoff_plan_reference,
            "person_record_reference": self.person_record_reference,
            "proposed_compensation_plan_digest": self.proposed_compensation_plan_digest,
            "proposed_compensation_plan_reference": self.proposed_compensation_plan_reference,
            "proposed_effective_on": self.proposed_effective_on.isoformat(),
            "purpose_code": self.purpose_code,
            "reason_code": self.reason_code,
            "requester_reference": self.requester_reference,
            "review_state": self.review_state,
            "reviewer_reference": self.reviewer_reference,
            "scope_verification_state": self.scope_verification_state,
            "tenant_record_id": self.tenant_record_id,
        }

    def canonical_json(self) -> str:
        """Return deterministic JSON suitable for immutable audit correlation."""
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical JSON evidence."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        """Return a correlation-free representation suitable for routine logs."""
        return (
            "CompensationChangeReviewPacket("
            f"review_state={self.review_state!r}, "
            f"mutation_authorized={self.mutation_authorized!r}, "
            f"scope_verification_state={self.scope_verification_state!r})"
        )


def build_compensation_change_review_packet(**values: object) -> CompensationChangeReviewPacket:
    """Build a validated compensation-change review packet from explicit governed fields."""
    return CompensationChangeReviewPacket(**values)  # type: ignore[arg-type]
