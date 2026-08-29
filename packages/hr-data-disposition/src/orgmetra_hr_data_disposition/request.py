"""Govern value-minimized HR data disposition requests without authorizing execution."""

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
    """Require exact, non-future UTC system time without caller-defined behavior."""
    if type(value) is not datetime:
        raise ValueError("recorded_at must be exact built-in datetime")
    if value.tzinfo is not timezone.utc:
        raise ValueError("recorded_at must use datetime.timezone.utc exactly")
    if value > datetime.now(timezone.utc):
        raise ValueError("recorded_at cannot be in the future")
    return value


@dataclass(frozen=True, slots=True, repr=False)
class HrDataDispositionExecutionRequest:
    """Bind one post-retention disposition request while remaining unauthorized to execute."""

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
    DISPOSITION_ACTIONS: ClassVar[frozenset[str]] = frozenset(
        {
            "delete_application_record",
            "pseudonymize_derived_record",
        }
    )
    UPSTREAM_RETENTION_WINDOW_STATES: ClassVar[frozenset[str]] = frozenset(
        {"requires_authoritative_disposition_review"}
    )
    UPSTREAM_AUTHORIZATION_STATES: ClassVar[frozenset[str]] = frozenset(
        {"not_authorized_to_delete"}
    )

    tenant_record_id: str
    disposition_request_reference: str
    retention_review_reference: str
    retention_review_digest: str
    resource_kind: str
    resource_reference: str
    record_category_code: str
    retention_policy_reference: str
    retention_policy_digest: str
    retention_due_on: date
    reviewed_on: date
    legal_hold_state: str
    requested_disposition_action: str
    requester_actor_reference: str
    reviewer_actor_reference: str
    evidence_version: int
    recorded_at: datetime
    upstream_retention_window_state: str = "requires_authoritative_disposition_review"
    upstream_disposition_authorization_state: str = "not_authorized_to_delete"

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Keep derived execution authority from being overridden by subclasses."""
        raise TypeError("HrDataDispositionExecutionRequest is final and cannot be subclassed")

    def __post_init__(self) -> None:
        """Fail closed on stale retention state, legal holds, chronology, or malformed scope."""
        self._assert_integrity()

    def _assert_integrity(self) -> None:
        """Revalidate all trust-bearing evidence at construction and canonicalization time."""
        _validate_tenant(self.tenant_record_id)
        _validate_reference(
            self.disposition_request_reference,
            "disposition_request",
            "disposition_request_reference",
        )
        _validate_reference(
            self.retention_review_reference,
            "retention_review",
            "retention_review_reference",
        )
        _validate_digest(self.retention_review_digest, "retention_review_digest")
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
        retention_due_on = _validate_business_date(self.retention_due_on, "retention_due_on")
        reviewed_on = _validate_business_date(self.reviewed_on, "reviewed_on")
        if reviewed_on <= retention_due_on:
            raise ValueError(
                "reviewed_on must be after retention_due_on before disposition can be requested"
            )
        _validate_code(
            self.legal_hold_state,
            "legal_hold_state",
            frozenset({"clear"}),
        )
        _validate_code(
            self.requested_disposition_action,
            "requested_disposition_action",
            self.DISPOSITION_ACTIONS,
        )
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
        _validate_code(
            self.upstream_retention_window_state,
            "upstream_retention_window_state",
            self.UPSTREAM_RETENTION_WINDOW_STATES,
        )
        _validate_code(
            self.upstream_disposition_authorization_state,
            "upstream_disposition_authorization_state",
            self.UPSTREAM_AUTHORIZATION_STATES,
        )

    @property
    def purpose_code(self) -> str:
        """Return the fixed review purpose."""
        return "hr_data_disposition_execution_request"

    @property
    def human_review_required(self) -> bool:
        """Require an accountable human before any execution boundary may act."""
        return True

    @property
    def scope_verification_state(self) -> str:
        """Require authoritative re-resolution immediately before execution."""
        return "requires_authoritative_resolution"

    @property
    def execution_authorization_state(self) -> str:
        """Prevent the request itself from granting destructive authority."""
        return "not_authorized_to_execute"

    @property
    def media_sanitization_state(self) -> str:
        """Avoid claiming storage-media sanitization from an application-layer request."""
        return "not_claimed"

    @property
    def next_action(self) -> str:
        """Tell the operator which authoritative evidence must be re-resolved next."""
        return (
            "Re-resolve the exact retention review and policy, current legal-hold state, "
            "tenant/resource scope, requester/reviewer authority, and immutable audit evidence; "
            "then obtain separate human execution approval at the owning Orgmetra service boundary. "
            "Do not treat this request as deletion authority or media-sanitization evidence."
        )

    def canonical_document(self) -> dict[str, object]:
        """Return deterministic, value-minimized request evidence after live revalidation."""
        self._assert_integrity()
        return {
            "tenant_record_id": self.tenant_record_id,
            "disposition_request_reference": self.disposition_request_reference,
            "retention_review_reference": self.retention_review_reference,
            "retention_review_digest": self.retention_review_digest,
            "resource_kind": self.resource_kind,
            "resource_reference": self.resource_reference,
            "record_category_code": self.record_category_code,
            "retention_policy_reference": self.retention_policy_reference,
            "retention_policy_digest": self.retention_policy_digest,
            "retention_due_on": self.retention_due_on.isoformat(),
            "reviewed_on": self.reviewed_on.isoformat(),
            "legal_hold_state": self.legal_hold_state,
            "requested_disposition_action": self.requested_disposition_action,
            "requester_actor_reference": self.requester_actor_reference,
            "reviewer_actor_reference": self.reviewer_actor_reference,
            "evidence_version": self.evidence_version,
            "recorded_at": self.recorded_at.isoformat().replace("+00:00", "Z"),
            "upstream_retention_window_state": self.upstream_retention_window_state,
            "upstream_disposition_authorization_state": self.upstream_disposition_authorization_state,
            "purpose_code": self.purpose_code,
            "human_review_required": self.human_review_required,
            "scope_verification_state": self.scope_verification_state,
            "execution_authorization_state": self.execution_authorization_state,
            "media_sanitization_state": self.media_sanitization_state,
            "next_action": self.next_action,
        }

    def canonical_json(self) -> str:
        """Serialize request evidence with stable ordering and no whitespace ambiguity."""
        return json.dumps(
            self.canonical_document(),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )

    def evidence_digest(self) -> str:
        """Hash the exact canonical request evidence with SHA-256."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        """Keep tenant, actor, resource, and policy correlation out of routine logs."""
        return "HrDataDispositionExecutionRequest(<redacted>)"
