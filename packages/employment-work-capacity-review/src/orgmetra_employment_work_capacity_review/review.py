"""Governed review evidence for changing one Employment's contracted work capacity.

This module records human-reviewed evidence for a proposed work-capacity change. It
never changes Employment, Assignment, compensation, payroll, leave, or scheduling
truth. The authoritative Orgmetra host must re-resolve tenant, Employment, reviewer
authority, reviewed evidence, and downstream allocation implications before any
bitemporal mutation and immutable audit/outbox write.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
import re
from threading import RLock
from typing import ClassVar
from uuid import UUID
from weakref import WeakKeyDictionary

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_MAX_UUID_INT = (1 << 128) - 1
_ZERO_CAPACITY = Decimal("0.0000")
_ONE_CAPACITY = Decimal("1.0000")
_PURPOSE_CODE = "employment_work_capacity_review"
_REVIEW_STATE = "reviewed_for_authoritative_resolution"
_DECISION_AUTHORITY = "not_authorized_to_change_employment_or_compensation"
_ALLOWED_REASON_CODES = frozenset(
    {
        "employee_agreed_change",
        "contractual_hours_change",
        "business_schedule_change",
        "return_from_leave",
    }
)
_NEXT_ACTION = (
    "Within tenant_record_id, re-resolve the authoritative Employment and current work-capacity "
    "truth at effective_on, verify reviewer identity/authority and the exact reviewed employment-terms "
    "and capacity-policy evidence, recalculate Assignment allocation and compensation/payroll impacts, "
    "then persist any approved bitemporal capacity change with immutable audit/outbox evidence. This "
    "packet does not itself mutate Employment, Assignment, compensation, payroll, leave, or scheduling."
)


def _require_exact_text(value: object, field_name: str) -> str:
    """Return trust-bearing text only when it is an exact built-in string."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be an exact string")
    return value


def _validate_operational_uuid_text(value: object, field_name: str) -> str:
    """Require canonical non-sentinel UUID text without imposing one UUID version."""
    text = _require_exact_text(value, field_name)
    try:
        parsed = UUID(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be canonical operational UUID text") from exc
    if str(parsed) != text or parsed.int in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be canonical operational UUID text")
    return text


def _validate_reference(
    value: object,
    prefix: str,
    field_name: str,
    *,
    require_uuid4: bool,
) -> str:
    """Require one namespaced canonical UUID reference with explicit ownership semantics."""
    text = _require_exact_text(value, field_name)
    namespace = f"{prefix}:"
    if len(text) > 160 or not text.startswith(namespace):
        raise ValueError(f"{field_name} must be an opaque {prefix}:<canonical-uuid> reference")
    suffix = text[len(namespace) :]
    try:
        parsed = UUID(suffix)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must be an opaque {prefix}:<canonical-uuid> reference"
        ) from exc
    if str(parsed) != suffix or parsed.int in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be an opaque {prefix}:<canonical-uuid> reference")
    if require_uuid4 and parsed.version != 4:
        raise ValueError(f"{field_name} must use an opaque canonical UUIDv4 reference")
    return text


def _validate_digest(value: object, field_name: str) -> str:
    """Require exact lower-case SHA-256 hexadecimal evidence."""
    text = _require_exact_text(value, field_name)
    if not _DIGEST_PATTERN.fullmatch(text):
        raise ValueError(f"{field_name} must be lower-case SHA-256 hex")
    return text


def _validate_capacity_ratio(value: object, field_name: str) -> Decimal:
    """Require a finite exact Decimal in canonical four-place [0, 1] form."""
    if type(value) is not Decimal:
        raise ValueError(f"{field_name} must be an exact Decimal")
    if not value.is_finite() or value < _ZERO_CAPACITY or value > _ONE_CAPACITY:
        raise ValueError(f"{field_name} must be finite and between 0.0000 and 1.0000")
    if value.is_zero() and value.is_signed():
        raise ValueError(f"{field_name} must not use signed negative zero")
    if value.as_tuple().exponent != -4:
        raise ValueError(f"{field_name} must use exactly four decimal places")
    return value


def _validate_reason_code(value: object) -> str:
    """Require one reviewed, value-free reason code."""
    text = _require_exact_text(value, "reason_code")
    if text not in _ALLOWED_REASON_CODES:
        raise ValueError("reason_code must use a reviewed employment-capacity reason")
    return text


def _validate_effective_date(value: object) -> date:
    """Require an exact date rather than datetime's date subclass behavior."""
    if type(value) is not date:
        raise ValueError("effective_on must be an exact built-in date")
    return value


def _validate_utc_timestamp(value: object, field_name: str) -> datetime:
    """Require an exact built-in datetime whose timezone is the UTC singleton."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError(f"{field_name} must be an exact built-in UTC datetime")
    return value


def _validate_evidence_version(value: object) -> int:
    """Require a positive bounded exact integer for immutable evidence evolution."""
    if type(value) is not int or value < 1 or value > 2_147_483_647:
        raise ValueError("evidence_version must be an integer from 1 through 2147483647")
    return value


def _system_recorded_utc() -> datetime:
    """Return the system-owned UTC issuance instant for this evidence object."""
    return datetime.now(timezone.utc)


def _canonical_timestamp(value: datetime) -> str:
    """Render a validated UTC timestamp as deterministic RFC 3339 text."""
    return value.isoformat().replace("+00:00", "Z")


def _canonical_json(payload: dict[str, object]) -> str:
    """Serialize one evidence payload deterministically for audit correlation."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True, slots=True, weakref_slot=True, eq=False, repr=False)
class EmploymentWorkCapacityReviewPacket:
    """Human-reviewed proposed Employment capacity change without mutation authority."""

    tenant_record_id: str
    employment_record_reference: str
    current_capacity_ratio: Decimal
    proposed_capacity_ratio: Decimal
    effective_on: date
    employment_terms_evidence_digest: str
    capacity_policy_evidence_digest: str
    reviewer_identity_evidence_digest: str
    requester_actor_reference: str
    reviewer_actor_reference: str
    reason_code: str
    evidence_version: int
    reviewed_at: datetime
    recorded_at: datetime = field(init=False, default_factory=_system_recorded_utc)
    purpose_code: str = _PURPOSE_CODE
    review_state: str = _REVIEW_STATE
    decision_authority: str = _DECISION_AUTHORITY
    human_review_required: bool = True
    next_action: str = _NEXT_ACTION

    _issuance_digests: ClassVar[
        WeakKeyDictionary["EmploymentWorkCapacityReviewPacket", str]
    ] = WeakKeyDictionary()
    _issuance_lock: ClassVar[RLock] = RLock()

    def __post_init__(self) -> None:
        """Validate all trust-bearing fields and seal creation-time evidence."""
        payload = self._validated_payload()
        digest = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
        with self._issuance_lock:
            self._issuance_digests[self] = digest

    def __repr__(self) -> str:
        """Return a fully redacted representation safe for routine logs."""
        return "EmploymentWorkCapacityReviewPacket(<redacted>)"

    def _validated_payload(self) -> dict[str, object]:
        """Revalidate and snapshot every trust-bearing field before any export."""
        tenant_record_id = _validate_operational_uuid_text(
            self.tenant_record_id, "tenant_record_id"
        )
        employment_record_reference = _validate_reference(
            self.employment_record_reference,
            "employment_record",
            "employment_record_reference",
            require_uuid4=False,
        )
        current = _validate_capacity_ratio(
            self.current_capacity_ratio, "current_capacity_ratio"
        )
        proposed = _validate_capacity_ratio(
            self.proposed_capacity_ratio, "proposed_capacity_ratio"
        )
        if current == proposed:
            raise ValueError("proposed_capacity_ratio must differ from current_capacity_ratio")
        effective_on = _validate_effective_date(self.effective_on)
        employment_terms_evidence_digest = _validate_digest(
            self.employment_terms_evidence_digest, "employment_terms_evidence_digest"
        )
        capacity_policy_evidence_digest = _validate_digest(
            self.capacity_policy_evidence_digest, "capacity_policy_evidence_digest"
        )
        reviewer_identity_evidence_digest = _validate_digest(
            self.reviewer_identity_evidence_digest, "reviewer_identity_evidence_digest"
        )
        requester_actor_reference = _validate_reference(
            self.requester_actor_reference,
            "actor",
            "requester_actor_reference",
            require_uuid4=True,
        )
        reviewer_actor_reference = _validate_reference(
            self.reviewer_actor_reference,
            "actor",
            "reviewer_actor_reference",
            require_uuid4=True,
        )
        if requester_actor_reference == reviewer_actor_reference:
            raise ValueError("requester and reviewer must be different actor references")
        reason_code = _validate_reason_code(self.reason_code)
        evidence_version = _validate_evidence_version(self.evidence_version)
        reviewed_at = _validate_utc_timestamp(self.reviewed_at, "reviewed_at")
        recorded_at = _validate_utc_timestamp(self.recorded_at, "recorded_at")
        if recorded_at < reviewed_at:
            raise ValueError("recorded_at cannot precede reviewed_at")
        purpose_code = _require_exact_text(self.purpose_code, "purpose_code")
        if purpose_code != _PURPOSE_CODE:
            raise ValueError("purpose_code must remain employment_work_capacity_review")
        review_state = _require_exact_text(self.review_state, "review_state")
        if review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain reviewed_for_authoritative_resolution")
        decision_authority = _require_exact_text(self.decision_authority, "decision_authority")
        if decision_authority != _DECISION_AUTHORITY:
            raise ValueError(
                "decision_authority must remain not_authorized_to_change_employment_or_compensation"
            )
        if self.human_review_required is not True:
            raise ValueError("human review is mandatory for Employment work-capacity evidence")
        next_action = _require_exact_text(self.next_action, "next_action")
        if next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed work-capacity instruction")

        return {
            "capacity_policy_evidence_digest": capacity_policy_evidence_digest,
            "current_capacity_ratio": format(current, "f"),
            "decision_authority": decision_authority,
            "effective_on": effective_on.isoformat(),
            "employment_record_reference": employment_record_reference,
            "employment_terms_evidence_digest": employment_terms_evidence_digest,
            "evidence_version": evidence_version,
            "human_review_required": self.human_review_required,
            "next_action": next_action,
            "proposed_capacity_ratio": format(proposed, "f"),
            "purpose_code": purpose_code,
            "reason_code": reason_code,
            "recorded_at": _canonical_timestamp(recorded_at),
            "requester_actor_reference": requester_actor_reference,
            "review_state": review_state,
            "reviewed_at": _canonical_timestamp(reviewed_at),
            "reviewer_actor_reference": reviewer_actor_reference,
            "reviewer_identity_evidence_digest": reviewer_identity_evidence_digest,
            "tenant_record_id": tenant_record_id,
        }

    def _verified_payload(self) -> dict[str, object]:
        """Return one verified snapshot or fail closed after post-issuance mutation."""
        payload = self._validated_payload()
        digest = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
        with self._issuance_lock:
            issued_digest = self._issuance_digests.get(self)
        if issued_digest != digest:
            raise ValueError("Employment work-capacity evidence was modified after issuance")
        return payload

    def canonical_document(self) -> dict[str, object]:
        """Return a detached verified canonical evidence document."""
        return dict(self._verified_payload())

    def canonical_json(self) -> str:
        """Return deterministic JSON from the exact verified evidence snapshot."""
        return _canonical_json(self._verified_payload())

    def sha256_digest(self) -> str:
        """Return SHA-256 over exact verified canonical JSON bytes."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_employment_work_capacity_review_packet(
    *,
    tenant_record_id: str,
    employment_record_reference: str,
    current_capacity_ratio: Decimal,
    proposed_capacity_ratio: Decimal,
    effective_on: date,
    employment_terms_evidence_digest: str,
    capacity_policy_evidence_digest: str,
    reviewer_identity_evidence_digest: str,
    requester_actor_reference: str,
    reviewer_actor_reference: str,
    reason_code: str,
    evidence_version: int,
    reviewed_at: datetime,
) -> EmploymentWorkCapacityReviewPacket:
    """Build one non-authoritative review with Orgmetra-owned system-recorded time."""
    return EmploymentWorkCapacityReviewPacket(
        tenant_record_id=tenant_record_id,
        employment_record_reference=employment_record_reference,
        current_capacity_ratio=current_capacity_ratio,
        proposed_capacity_ratio=proposed_capacity_ratio,
        effective_on=effective_on,
        employment_terms_evidence_digest=employment_terms_evidence_digest,
        capacity_policy_evidence_digest=capacity_policy_evidence_digest,
        reviewer_identity_evidence_digest=reviewer_identity_evidence_digest,
        requester_actor_reference=requester_actor_reference,
        reviewer_actor_reference=reviewer_actor_reference,
        reason_code=reason_code,
        evidence_version=evidence_version,
        reviewed_at=reviewed_at,
    )
