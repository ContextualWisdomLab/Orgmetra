"""Value-minimized human HR access-review evidence.

The packet records what an accountable reviewer recommended about an existing access
snapshot. It does not carry HR values, credentials, raw entitlements, or authority to
grant, reduce, or revoke access. Enforcement must re-enter Orgmetra's authoritative
identity, purpose, resource-scope, and immutable-audit boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import re
from threading import RLock
from typing import Any
from uuid import UUID
from weakref import WeakKeyDictionary

_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_OPAQUE_REFERENCE_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]{1,31}:[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$"
)
_ALLOWED_REASON_CODES = frozenset(
    {"periodic_access_review", "privileged_access_review", "role_change_access_review"}
)
_ALLOWED_RECOMMENDATIONS = frozenset(
    {"retain_existing_access", "reduce_existing_access", "remove_existing_access"}
)
_PURPOSE_CODE = "hr_access_recertification"
_REVIEW_STATE = "human_review_recorded"
_ENFORCEMENT_STATE = "not_authorized_to_modify_access"
_SCOPE_VERIFICATION_STATE = "requires_authoritative_resolution"
_NEXT_ACTION = (
    "Before changing access, re-resolve the exact tenant, reviewed subject, current resource "
    "scope, purpose, authorization policy, entitlement state, and accountable reviewer through "
    "the authoritative identity and authorization boundary; then record any approved access "
    "mutation through its separate immutable audit/outbox contract."
)
_ISSUANCE_LOCK = RLock()
_ISSUANCE_DIGESTS: WeakKeyDictionary[HrAccessReviewPacket, str]


def _validate_operational_uuid(value: str, field_name: str) -> None:
    """Require exact canonical non-sentinel UUID text for authoritative HRIS identity."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be canonical UUID text")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{field_name} must be canonical UUID text") from exc
    if str(parsed) != value or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(f"{field_name} must be a canonical operational UUID")


def _validate_packet_reference(value: str, prefix: str, field_name: str) -> None:
    """Require exact opaque packet-owned UUIDv4 reference text."""
    error_message = f"{field_name} must be an opaque {prefix}: UUIDv4 reference"
    if (
        type(value) is not str
        or len(value) > 160
        or not _OPAQUE_REFERENCE_PATTERN.fullmatch(value)
        or not value.startswith(f"{prefix}:")
    ):
        raise ValueError(error_message)
    suffix = value.split(":", 1)[1]
    try:
        parsed = UUID(suffix)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(error_message) from exc
    if str(parsed) != suffix or parsed.version != 4:
        raise ValueError(error_message)


def _validate_actor_reference(value: str, field_name: str) -> None:
    """Require packet-local opaque UUIDv4 actor correlation for later identity resolution."""
    _validate_packet_reference(value, "actor", field_name)


def _validate_digest(value: str, field_name: str) -> None:
    """Require exact lowercase SHA-256 evidence text."""
    if type(value) is not str or not _DIGEST_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _validate_code(value: str, field_name: str) -> None:
    """Require exact bounded descriptive two-or-more-word lower snake_case text."""
    if type(value) is not str or len(value) > 64 or not _CODE_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be bounded two-or-more-word lower snake_case")


def _validate_reason_code(value: str) -> None:
    """Require a reviewed non-sensitive reason for existing-access review."""
    _validate_code(value, "review_reason_code")
    if value not in _ALLOWED_REASON_CODES:
        raise ValueError("review_reason_code must use the reviewed access-review vocabulary")


def _validate_recommendation(value: str) -> None:
    """Reject any recommendation that could expand access or escape the review vocabulary."""
    _validate_code(value, "review_recommendation_code")
    if value not in _ALLOWED_RECOMMENDATIONS:
        raise ValueError(
            "review_recommendation_code must retain, reduce, or remove existing access only"
        )


def _validate_utc_timestamp(value: datetime, field_name: str) -> None:
    """Require exact built-in UTC datetime evidence without executable timezone semantics."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError(f"{field_name} must be an exact built-in UTC datetime")


def _validate_evidence_version(value: int) -> None:
    """Require a bounded positive integer evidence version."""
    if type(value) is not int or value < 1 or value > 2_147_483_647:
        raise ValueError("evidence_version must be an integer from 1 through 2147483647")


def _require_fixed_text(value: str, expected: str, field_name: str) -> None:
    """Require exact built-in fixed governance text before comparison or serialization."""
    if type(value) is not str or value != expected:
        raise ValueError(f"{field_name} must remain {expected}")


def _require_fixed_bool(value: bool, expected: bool, field_name: str) -> None:
    """Require an exact fixed boolean rather than an int-like substitute."""
    if type(value) is not bool or value is not expected:
        raise ValueError(f"{field_name} must remain {expected}")


@dataclass(frozen=True, slots=True, weakref_slot=True, repr=False, eq=False)
class HrAccessReviewPacket:
    """Immutable, value-minimized human review evidence for existing HR access."""

    tenant_record_id: str
    access_review_reference: str
    subject_actor_reference: str
    requester_actor_reference: str
    reviewer_actor_reference: str
    resource_scope_digest: str
    authorization_policy_digest: str
    entitlement_snapshot_digest: str
    reviewer_identity_evidence_digest: str
    review_reason_code: str
    review_recommendation_code: str
    reviewed_at: datetime
    recorded_at: datetime
    evidence_version: int = 1
    purpose_code: str = _PURPOSE_CODE
    contains_hr_data: bool = False
    contains_credentials: bool = False
    human_confirmation_required: bool = True
    review_state: str = _REVIEW_STATE
    enforcement_state: str = _ENFORCEMENT_STATE
    scope_verification_state: str = _SCOPE_VERIFICATION_STATE
    next_action: str = _NEXT_ACTION

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Keep governed review behavior final so subclasses cannot override exports."""
        raise TypeError("HrAccessReviewPacket is final")

    def __post_init__(self) -> None:
        """Validate the full packet and register its creation-time evidence digest."""
        self._validate()
        with _ISSUANCE_LOCK:
            _ISSUANCE_DIGESTS[self] = self._payload_digest()

    def __repr__(self) -> str:
        """Avoid disclosing actor, tenant, policy, scope, or entitlement correlation in logs."""
        return "HrAccessReviewPacket(<redacted>)"

    def _validate(self) -> None:
        """Fail closed when live fields drift from the reviewed non-enforcing contract."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_packet_reference(
            self.access_review_reference, "access_review", "access_review_reference"
        )
        _validate_actor_reference(self.subject_actor_reference, "subject_actor_reference")
        _validate_actor_reference(self.requester_actor_reference, "requester_actor_reference")
        _validate_actor_reference(self.reviewer_actor_reference, "reviewer_actor_reference")
        if self.reviewer_actor_reference in (
            self.requester_actor_reference,
            self.subject_actor_reference,
        ):
            raise ValueError(
                "reviewer_actor_reference must differ from requester and reviewed subject"
            )
        _validate_digest(self.resource_scope_digest, "resource_scope_digest")
        _validate_digest(self.authorization_policy_digest, "authorization_policy_digest")
        _validate_digest(self.entitlement_snapshot_digest, "entitlement_snapshot_digest")
        _validate_digest(
            self.reviewer_identity_evidence_digest, "reviewer_identity_evidence_digest"
        )
        _validate_reason_code(self.review_reason_code)
        _validate_recommendation(self.review_recommendation_code)
        _validate_utc_timestamp(self.reviewed_at, "reviewed_at")
        _validate_utc_timestamp(self.recorded_at, "recorded_at")
        if self.recorded_at < self.reviewed_at:
            raise ValueError("recorded_at must be at or after reviewed_at")
        _validate_evidence_version(self.evidence_version)
        _require_fixed_text(self.purpose_code, _PURPOSE_CODE, "purpose_code")
        _require_fixed_bool(self.contains_hr_data, False, "contains_hr_data")
        _require_fixed_bool(self.contains_credentials, False, "contains_credentials")
        _require_fixed_bool(
            self.human_confirmation_required, True, "human_confirmation_required"
        )
        _require_fixed_text(self.review_state, _REVIEW_STATE, "review_state")
        _require_fixed_text(self.enforcement_state, _ENFORCEMENT_STATE, "enforcement_state")
        _require_fixed_text(
            self.scope_verification_state,
            _SCOPE_VERIFICATION_STATE,
            "scope_verification_state",
        )
        _require_fixed_text(self.next_action, _NEXT_ACTION, "next_action")

    def _payload(self) -> dict[str, Any]:
        """Return the exact minimized evidence fields in canonicalizable form."""
        return {
            "access_review_reference": self.access_review_reference,
            "authorization_policy_digest": self.authorization_policy_digest,
            "contains_credentials": self.contains_credentials,
            "contains_hr_data": self.contains_hr_data,
            "enforcement_state": self.enforcement_state,
            "entitlement_snapshot_digest": self.entitlement_snapshot_digest,
            "evidence_version": self.evidence_version,
            "human_confirmation_required": self.human_confirmation_required,
            "next_action": self.next_action,
            "purpose_code": self.purpose_code,
            "recorded_at": self.recorded_at.isoformat().replace("+00:00", "Z"),
            "requester_actor_reference": self.requester_actor_reference,
            "resource_scope_digest": self.resource_scope_digest,
            "review_reason_code": self.review_reason_code,
            "review_recommendation_code": self.review_recommendation_code,
            "review_state": self.review_state,
            "reviewed_at": self.reviewed_at.isoformat().replace("+00:00", "Z"),
            "reviewer_actor_reference": self.reviewer_actor_reference,
            "reviewer_identity_evidence_digest": self.reviewer_identity_evidence_digest,
            "scope_verification_state": self.scope_verification_state,
            "subject_actor_reference": self.subject_actor_reference,
            "tenant_record_id": self.tenant_record_id,
        }

    def _payload_digest(self, payload: dict[str, Any] | None = None) -> str:
        """Hash one canonicalizable payload without consulting issuance state."""
        evidence = self._payload() if payload is None else payload
        encoded = json.dumps(
            evidence, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
        return sha256(encoded).hexdigest()

    def _assert_integrity(self) -> dict[str, Any]:
        """Return the checked payload while rejecting copies or evidence rewrites."""
        self._validate()
        with _ISSUANCE_LOCK:
            expected = _ISSUANCE_DIGESTS.get(self)
        if expected is None:
            raise ValueError("access review evidence is not registered as constructed")
        payload = self._payload()
        if not hmac.compare_digest(expected, self._payload_digest(payload)):
            raise ValueError("access review evidence changed after construction")
        return payload

    def canonical_document(self) -> dict[str, Any]:
        """Return one verified value-minimized document for immutable audit correlation."""
        return self._assert_integrity()

    def canonical_json(self) -> str:
        """Return deterministic verified canonical JSON for durable audit/outbox evidence."""
        return json.dumps(
            self.canonical_document(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact verified canonical UTF-8 evidence."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


_ISSUANCE_DIGESTS = WeakKeyDictionary()


def build_hr_access_review_packet(
    *,
    tenant_record_id: str,
    access_review_reference: str,
    subject_actor_reference: str,
    requester_actor_reference: str,
    reviewer_actor_reference: str,
    resource_scope_digest: str,
    authorization_policy_digest: str,
    entitlement_snapshot_digest: str,
    reviewer_identity_evidence_digest: str,
    review_reason_code: str,
    review_recommendation_code: str,
    reviewed_at: datetime,
    recorded_at: datetime,
    evidence_version: int = 1,
) -> HrAccessReviewPacket:
    """Build non-enforcing access-review evidence for authoritative downstream confirmation."""
    return HrAccessReviewPacket(
        tenant_record_id=tenant_record_id,
        access_review_reference=access_review_reference,
        subject_actor_reference=subject_actor_reference,
        requester_actor_reference=requester_actor_reference,
        reviewer_actor_reference=reviewer_actor_reference,
        resource_scope_digest=resource_scope_digest,
        authorization_policy_digest=authorization_policy_digest,
        entitlement_snapshot_digest=entitlement_snapshot_digest,
        reviewer_identity_evidence_digest=reviewer_identity_evidence_digest,
        review_reason_code=review_reason_code,
        review_recommendation_code=review_recommendation_code,
        reviewed_at=reviewed_at,
        recorded_at=recorded_at,
        evidence_version=evidence_version,
    )
