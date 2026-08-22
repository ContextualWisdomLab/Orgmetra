"""Govern value-minimized HR data-retention review evidence without authorizing deletion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
import re
from typing import ClassVar
from uuid import UUID

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_UUID_MAX = (1 << 128) - 1


def _require_text(value: object, field_name: str, *, max_length: int = 200) -> str:
    """Return exact built-in bounded text so caller polymorphism cannot forge checks."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be exact built-in str")
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    if len(value) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters")
    return value


def _validate_tenant(value: object) -> str:
    """Accept one canonical non-sentinel operational UUID without imposing a UUID version."""
    text = _require_text(value, "tenant_record_id")
    try:
        parsed = UUID(text)
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("tenant_record_id must be a canonical UUID") from error
    if str(parsed) != text or parsed.int in (0, _UUID_MAX):
        raise ValueError("tenant_record_id must be a canonical non-sentinel UUID")
    return text


def _validate_reference(value: object, prefix: str, field_name: str) -> str:
    """Require an opaque namespace-bound canonical UUIDv4 packet reference."""
    text = _require_text(value, field_name)
    namespace = f"{prefix}:"
    if not text.startswith(namespace):
        raise ValueError(f"{field_name} must use the {prefix}: namespace")
    suffix = text[len(namespace) :]
    try:
        parsed = UUID(suffix)
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError(f"{field_name} must end in a canonical UUIDv4") from error
    if str(parsed) != suffix or parsed.version != 4:
        raise ValueError(f"{field_name} must end in a canonical UUIDv4")
    return text


def _validate_digest(value: object, field_name: str) -> str:
    """Require a lowercase SHA-256 digest rather than caller-defined text semantics."""
    text = _require_text(value, field_name, max_length=64)
    if _SHA256_PATTERN.fullmatch(text) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return text


def _validate_code(value: object, field_name: str, allowed: frozenset[str]) -> str:
    """Require exact built-in text from one reviewed closed vocabulary."""
    text = _require_text(value, field_name, max_length=64)
    if text not in allowed:
        raise ValueError(f"{field_name} is not an allowed reviewed value")
    return text


def _validate_evidence_version(value: object) -> int:
    """Require a positive signed-32-bit evidence version and reject bool/subclasses."""
    if type(value) is not int:
        raise ValueError("evidence_version must be exact built-in int")
    if not 1 <= value <= 2_147_483_647:
        raise ValueError("evidence_version must be between 1 and 2147483647")
    return value


def _validate_business_date(value: object, field_name: str) -> date:
    """Require an exact date so datetime subclasses cannot alter business-day semantics."""
    if type(value) is not date:
        raise ValueError(f"{field_name} must be exact built-in date")
    return value


def _validate_recorded_at(value: object) -> datetime:
    """Require exact UTC system time without executing caller-defined timezone behavior."""
    if type(value) is not datetime:
        raise ValueError("recorded_at must be exact built-in datetime")
    if value.tzinfo is not timezone.utc:
        raise ValueError("recorded_at must use datetime.timezone.utc exactly")
    return value


@dataclass(frozen=True, slots=True, repr=False)
class HrDataRetentionReviewPacket:
    """Bind one HR retention review while remaining explicitly unauthorized to delete data."""

    RESOURCE_KINDS: ClassVar[frozenset[str]] = frozenset(
        {
            "candidate_profile",
            "person_record",
            "employment_record",
            "selection_decision",
            "criterion_observation",
            "compensation_record",
        }
    )
    RECORD_CATEGORIES: ClassVar[frozenset[str]] = frozenset(
        {
            "candidate_employment_record",
            "worker_personnel_record",
            "selection_evidence_record",
            "performance_criterion_record",
            "compensation_governance_record",
        }
    )
    LEGAL_HOLD_STATES: ClassVar[frozenset[str]] = frozenset({"clear", "active"})

    tenant_record_id: str
    retention_review_reference: str
    resource_kind: str
    resource_reference: str
    record_category_code: str
    retention_policy_reference: str
    retention_policy_digest: str
    retention_due_on: date
    reviewed_on: date
    legal_hold_state: str
    legal_hold_reference: str | None
    legal_hold_digest: str | None
    requester_actor_reference: str
    reviewer_actor_reference: str
    evidence_version: int
    recorded_at: datetime

    def __post_init__(self) -> None:
        """Fail closed on malformed scope, contradictory hold evidence, or review chronology."""
        self._assert_integrity()

    def _assert_integrity(self) -> None:
        """Revalidate all trust-bearing evidence at construction and canonicalization time."""
        _validate_tenant(self.tenant_record_id)
        _validate_reference(
            self.retention_review_reference,
            "retention_review",
            "retention_review_reference",
        )
        resource_kind = _validate_code(self.resource_kind, "resource_kind", self.RESOURCE_KINDS)
        _validate_reference(self.resource_reference, resource_kind, "resource_reference")
        _validate_code(
            self.record_category_code,
            "record_category_code",
            self.RECORD_CATEGORIES,
        )
        _validate_reference(
            self.retention_policy_reference,
            "retention_policy",
            "retention_policy_reference",
        )
        _validate_digest(self.retention_policy_digest, "retention_policy_digest")
        _validate_business_date(self.retention_due_on, "retention_due_on")
        reviewed_on = _validate_business_date(self.reviewed_on, "reviewed_on")
        hold_state = _validate_code(
            self.legal_hold_state,
            "legal_hold_state",
            self.LEGAL_HOLD_STATES,
        )
        if hold_state == "active":
            if self.legal_hold_reference is None or self.legal_hold_digest is None:
                raise ValueError("active legal hold requires reference and digest evidence")
            _validate_reference(self.legal_hold_reference, "legal_hold", "legal_hold_reference")
            _validate_digest(self.legal_hold_digest, "legal_hold_digest")
        elif self.legal_hold_reference is not None or self.legal_hold_digest is not None:
            raise ValueError("clear legal hold state cannot carry hold reference or digest")
        requester = _validate_reference(
            self.requester_actor_reference,
            "actor",
            "requester_actor_reference",
        )
        reviewer = _validate_reference(
            self.reviewer_actor_reference,
            "actor",
            "reviewer_actor_reference",
        )
        if requester == reviewer:
            raise ValueError("requester_actor_reference and reviewer_actor_reference must differ")
        _validate_evidence_version(self.evidence_version)
        recorded_at = _validate_recorded_at(self.recorded_at)
        if recorded_at.date() < reviewed_on:
            raise ValueError("recorded_at cannot precede reviewed_on")

    @property
    def purpose_code(self) -> str:
        """Return the fixed non-decision review purpose."""
        return "hr_data_retention_review"

    @property
    def requested_action(self) -> str:
        """Return the fixed request that asks only for disposition eligibility review."""
        return "review_disposition_eligibility"

    @property
    def human_review_required(self) -> bool:
        """Require accountable human review before any downstream disposition action."""
        return True

    @property
    def scope_verification_state(self) -> str:
        """Make clear that packet references still require authoritative re-resolution."""
        return "requires_authoritative_resolution"

    @property
    def disposition_authorization_state(self) -> str:
        """Make deletion authority impossible to infer from this review packet."""
        return "not_authorized_to_delete"

    @property
    def retention_window_state(self) -> str:
        """Describe whether the record must remain or can only enter authoritative review."""
        if self.legal_hold_state == "active":
            return "retain_legal_hold"
        if self.reviewed_on <= self.retention_due_on:
            return "retain_until_due"
        return "requires_authoritative_disposition_review"

    @property
    def next_action(self) -> str:
        """Tell an operator the safe next action without granting data-deletion authority."""
        state = self.retention_window_state
        if state == "retain_legal_hold":
            return (
                "Retain the record under the legal hold; re-resolve hold scope and authority "
                "before any future disposition review."
            )
        if state == "retain_until_due":
            return (
                "Retain the record through the reviewed retention due date; re-review policy "
                "and legal-hold state before any disposition action."
            )
        return (
            "Re-resolve the authoritative retention policy, legal-hold state, tenant/resource "
            "scope, reviewer authority, and immutable audit evidence before a separate "
            "human-approved disposition execution."
        )

    def canonical_document(self) -> dict[str, object]:
        """Return deterministic governance evidence after revalidating the live object state."""
        self._assert_integrity()
        return {
            "tenant_record_id": self.tenant_record_id,
            "retention_review_reference": self.retention_review_reference,
            "resource_kind": self.resource_kind,
            "resource_reference": self.resource_reference,
            "record_category_code": self.record_category_code,
            "retention_policy_reference": self.retention_policy_reference,
            "retention_policy_digest": self.retention_policy_digest,
            "retention_due_on": self.retention_due_on.isoformat(),
            "reviewed_on": self.reviewed_on.isoformat(),
            "legal_hold_state": self.legal_hold_state,
            "legal_hold_reference": self.legal_hold_reference,
            "legal_hold_digest": self.legal_hold_digest,
            "requester_actor_reference": self.requester_actor_reference,
            "reviewer_actor_reference": self.reviewer_actor_reference,
            "evidence_version": self.evidence_version,
            "recorded_at": self.recorded_at.isoformat().replace("+00:00", "Z"),
            "purpose_code": self.purpose_code,
            "requested_action": self.requested_action,
            "human_review_required": self.human_review_required,
            "scope_verification_state": self.scope_verification_state,
            "disposition_authorization_state": self.disposition_authorization_state,
            "retention_window_state": self.retention_window_state,
            "next_action": self.next_action,
        }

    def canonical_json(self) -> str:
        """Serialize the packet with stable ordering and no whitespace ambiguity."""
        return json.dumps(
            self.canonical_document(),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )

    def evidence_digest(self) -> str:
        """Hash the exact canonical review evidence with SHA-256."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        """Keep tenant and policy correlation references out of routine logs."""
        return "HrDataRetentionReviewPacket(<redacted>)"
