"""Governed, value-minimized candidate offer-response evidence.

This module records what an authenticated candidate said about one exact reviewed offer.
It deliberately does not authorize employment creation, offer delivery, compensation
execution, or candidate-to-worker conversion. Authoritative services must re-resolve the
candidate identity and exact offer scope before taking any consequential action.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from threading import RLock
from uuid import UUID
from weakref import finalize

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$")
_ALLOWED_RESPONSE_CODES = frozenset({"offer_accepted", "offer_declined"})
_DECISION_AUTHORITY = "candidate_response_only"
_SCOPE_VERIFICATION_STATE = "requires_authoritative_resolution"
_EMPLOYMENT_EFFECT = "not_authorized_to_hire"
_NEXT_ACTION = (
    "Within tenant_record_id, re-resolve candidate_actor_reference through the approved "
    "identity boundary and re-resolve the exact offer approval and offer terms digests; "
    "verify the offer was eligible for response at responded_at and that this evidence is "
    "the authoritative candidate response before any communication, hire, employment, or "
    "candidate-to-worker conversion action."
)
_CREATION_EVIDENCE_SEALS: dict[int, str] = {}
_CREATION_EVIDENCE_SEALS_LOCK = RLock()


def _discard_creation_evidence_seal(packet_id: int) -> None:
    """Discard the process-local issuance seal when its packet is collected."""
    with _CREATION_EVIDENCE_SEALS_LOCK:
        _CREATION_EVIDENCE_SEALS.pop(packet_id, None)


def _register_creation_evidence_seal(packet: object, digest: str) -> None:
    """Bind one packet identity to its creation-time evidence outside writable slots."""
    packet_id = id(packet)
    with _CREATION_EVIDENCE_SEALS_LOCK:
        _CREATION_EVIDENCE_SEALS[packet_id] = digest
    finalize(packet, _discard_creation_evidence_seal, packet_id)


def _creation_evidence_seal(packet: object) -> str:
    """Return the authoritative process-local seal for a live governed packet."""
    with _CREATION_EVIDENCE_SEALS_LOCK:
        seal = _CREATION_EVIDENCE_SEALS.get(id(packet))
    if seal is None:
        raise ValueError("candidate offer response evidence has no issuance seal")
    return seal


def _validate_operational_uuid(value: str, field_name: str) -> None:
    """Require exact canonical non-sentinel UUID text for an HRIS-owned identifier."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be canonical UUID text")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{field_name} must be canonical UUID text") from exc
    if str(parsed) != value:
        raise ValueError(f"{field_name} must be canonical UUID text")
    if parsed.int in (0, (1 << 128) - 1):
        raise ValueError(f"{field_name} must be a canonical operational UUID")


def _validate_reference(
    value: str,
    prefix: str,
    field_name: str,
    *,
    require_uuid4: bool = True,
) -> None:
    """Require one bounded namespace and UUIDv4 only when Orgmetra owns that contract."""
    max_length = 160 if require_uuid4 else 288
    reference_kind = "UUIDv4" if require_uuid4 else "opaque"
    error_message = f"{field_name} must be a bounded {prefix}: {reference_kind} reference"
    if (
        type(value) is not str
        or len(value) > max_length
        or not _REFERENCE_PATTERN.fullmatch(value)
        or not value.startswith(f"{prefix}:")
    ):
        raise ValueError(error_message)
    if not require_uuid4:
        return
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


def _freeze_timestamp(value: datetime, field_name: str) -> datetime:
    """Detach caller-controlled timezone behavior and return one exact UTC instant."""
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError(f"{field_name} must be an exact timezone-aware datetime")
    try:
        offset = value.utcoffset()
    except Exception:
        raise ValueError(f"{field_name} must have a valid timezone offset") from None
    if offset is None:
        raise ValueError(f"{field_name} must have a valid timezone offset")
    try:
        utc_naive = value.replace(tzinfo=None) - offset
    except OverflowError:
        raise ValueError(f"{field_name} must have a valid timezone offset") from None
    return utc_naive.replace(tzinfo=timezone.utc)


def _validate_canonical_timestamp(value: datetime, field_name: str) -> None:
    """Require the already-detached built-in UTC timestamp used by canonical evidence."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError(f"{field_name} must remain a canonical UTC datetime")


def _canonical_timestamp(value: datetime) -> str:
    """Render a previously validated UTC instant as precision-preserving RFC 3339 text."""
    return value.isoformat().replace("+00:00", "Z")


def _validate_evidence_version(value: int) -> None:
    """Require one bounded built-in integer evidence version."""
    if type(value) is not int or value < 1 or value > 2_147_483_647:
        raise ValueError("evidence_version must be an integer from 1 through 2147483647")


def _validate_fixed_text(value: str, expected: str, field_name: str) -> None:
    """Prevent runtime-polymorphic text from forging fixed governance evidence."""
    if type(value) is not str or value != expected:
        raise ValueError(f"{field_name} must remain {expected}")


@dataclass(frozen=True, slots=True, repr=False, weakref_slot=True)
class CandidateOfferResponsePacket:
    """Immutable candidate-originated offer response awaiting authoritative re-resolution."""

    tenant_record_id: str
    offer_response_reference: str
    candidate_profile_reference: str
    offer_approval_reference: str
    offer_approval_digest: str
    offer_terms_reference: str
    offer_terms_digest: str
    candidate_actor_reference: str
    identity_resolution_reference: str
    identity_resolution_digest: str
    response_code: str
    responded_at: datetime
    recorded_at: datetime
    evidence_version: int = 1
    contains_candidate_pii: bool = False
    contains_compensation_values: bool = False
    contains_free_form_reason: bool = False
    candidate_confirmation_required: bool = True
    decision_authority: str = _DECISION_AUTHORITY
    scope_verification_state: str = _SCOPE_VERIFICATION_STATE
    employment_effect: str = _EMPLOYMENT_EFFECT
    next_action: str = _NEXT_ACTION
    _creation_evidence_digest: str = field(init=False, repr=False, compare=False)

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Keep the trust-bearing packet runtime-final rather than polymorphic."""
        raise TypeError("CandidateOfferResponsePacket is final")

    def __repr__(self) -> str:
        """Return a representation that emits no candidate or offer correlation evidence."""
        return "CandidateOfferResponsePacket(<redacted>)"

    def __post_init__(self) -> None:
        """Validate inputs, detach timezone behavior, and seal canonical construction evidence."""
        object.__setattr__(self, "responded_at", _freeze_timestamp(self.responded_at, "responded_at"))
        object.__setattr__(self, "recorded_at", _freeze_timestamp(self.recorded_at, "recorded_at"))
        self._validate_live()
        creation_digest = self._raw_sha256_digest()
        object.__setattr__(self, "_creation_evidence_digest", creation_digest)
        _register_creation_evidence_seal(self, creation_digest)

    def _validate_live(self) -> None:
        """Fail closed if direct construction or later rewriting drifts from the contract."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.offer_response_reference,
            "candidate_offer_response",
            "offer_response_reference",
        )
        _validate_reference(
            self.candidate_profile_reference,
            "candidate_profile",
            "candidate_profile_reference",
        )
        _validate_reference(
            self.offer_approval_reference,
            "offer_approval",
            "offer_approval_reference",
        )
        _validate_digest(self.offer_approval_digest, "offer_approval_digest")
        _validate_reference(self.offer_terms_reference, "offer_terms", "offer_terms_reference")
        _validate_digest(self.offer_terms_digest, "offer_terms_digest")
        _validate_reference(
            self.candidate_actor_reference,
            "candidate",
            "candidate_actor_reference",
            require_uuid4=False,
        )
        _validate_reference(
            self.identity_resolution_reference,
            "identity_resolution",
            "identity_resolution_reference",
        )
        _validate_digest(self.identity_resolution_digest, "identity_resolution_digest")
        if type(self.response_code) is not str or self.response_code not in _ALLOWED_RESPONSE_CODES:
            raise ValueError("response_code must be offer_accepted or offer_declined")
        _validate_canonical_timestamp(self.responded_at, "responded_at")
        _validate_canonical_timestamp(self.recorded_at, "recorded_at")
        if self.recorded_at < self.responded_at:
            raise ValueError("recorded_at must not precede responded_at")
        _validate_evidence_version(self.evidence_version)
        if self.contains_candidate_pii is not False:
            raise ValueError("candidate offer response evidence must not contain candidate PII")
        if self.contains_compensation_values is not False:
            raise ValueError("candidate offer response evidence must not contain compensation values")
        if self.contains_free_form_reason is not False:
            raise ValueError("candidate offer response evidence must not contain a free-form reason")
        if self.candidate_confirmation_required is not True:
            raise ValueError("candidate confirmation is mandatory for candidate offer response evidence")
        _validate_fixed_text(self.decision_authority, _DECISION_AUTHORITY, "decision_authority")
        _validate_fixed_text(
            self.scope_verification_state,
            _SCOPE_VERIFICATION_STATE,
            "scope_verification_state",
        )
        _validate_fixed_text(self.employment_effect, _EMPLOYMENT_EFFECT, "employment_effect")
        _validate_fixed_text(self.next_action, _NEXT_ACTION, "next_action")

    def _payload(self) -> dict[str, object]:
        """Return the exact value-minimized payload used for audit correlation."""
        return {
            "candidate_actor_reference": self.candidate_actor_reference,
            "candidate_confirmation_required": self.candidate_confirmation_required,
            "candidate_profile_reference": self.candidate_profile_reference,
            "contains_candidate_pii": self.contains_candidate_pii,
            "contains_compensation_values": self.contains_compensation_values,
            "contains_free_form_reason": self.contains_free_form_reason,
            "decision_authority": self.decision_authority,
            "employment_effect": self.employment_effect,
            "evidence_version": self.evidence_version,
            "identity_resolution_digest": self.identity_resolution_digest,
            "identity_resolution_reference": self.identity_resolution_reference,
            "next_action": self.next_action,
            "offer_approval_digest": self.offer_approval_digest,
            "offer_approval_reference": self.offer_approval_reference,
            "offer_response_reference": self.offer_response_reference,
            "offer_terms_digest": self.offer_terms_digest,
            "offer_terms_reference": self.offer_terms_reference,
            "recorded_at": _canonical_timestamp(self.recorded_at),
            "responded_at": _canonical_timestamp(self.responded_at),
            "response_code": self.response_code,
            "scope_verification_state": self.scope_verification_state,
            "tenant_record_id": self.tenant_record_id,
        }

    def _raw_canonical_json(self) -> str:
        """Serialize live fields without recursively invoking the integrity check."""
        return json.dumps(self._payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def _raw_sha256_digest(self) -> str:
        """Hash live canonical bytes without recursively invoking the integrity check."""
        return sha256(self._raw_canonical_json().encode("utf-8")).hexdigest()

    def _assert_integrity(self) -> str:
        """Validate and return the exact canonical snapshot that passed the issuance check."""
        self._validate_live()
        canonical_json = self._raw_canonical_json()
        authoritative_seal = _creation_evidence_seal(self)
        if (
            sha256(canonical_json.encode("utf-8")).hexdigest() != authoritative_seal
            or self._creation_evidence_digest != authoritative_seal
        ):
            raise ValueError("candidate offer response evidence changed after construction")
        return canonical_json

    def canonical_json(self) -> str:
        """Return the exact deterministic snapshot that passed creation-time integrity."""
        return self._assert_integrity()

    def sha256_digest(self) -> str:
        """Return SHA-256 over exact canonical UTF-8 offer-response evidence."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_candidate_offer_response(
    *,
    tenant_record_id: str,
    offer_response_reference: str,
    candidate_profile_reference: str,
    offer_approval_reference: str,
    offer_approval_digest: str,
    offer_terms_reference: str,
    offer_terms_digest: str,
    candidate_actor_reference: str,
    identity_resolution_reference: str,
    identity_resolution_digest: str,
    response_code: str,
    responded_at: datetime,
    recorded_at: datetime,
    evidence_version: int = 1,
) -> CandidateOfferResponsePacket:
    """Build candidate-originated response evidence without granting downstream authority."""
    return CandidateOfferResponsePacket(
        tenant_record_id=tenant_record_id,
        offer_response_reference=offer_response_reference,
        candidate_profile_reference=candidate_profile_reference,
        offer_approval_reference=offer_approval_reference,
        offer_approval_digest=offer_approval_digest,
        offer_terms_reference=offer_terms_reference,
        offer_terms_digest=offer_terms_digest,
        candidate_actor_reference=candidate_actor_reference,
        identity_resolution_reference=identity_resolution_reference,
        identity_resolution_digest=identity_resolution_digest,
        response_code=response_code,
        responded_at=responded_at,
        recorded_at=recorded_at,
        evidence_version=evidence_version,
    )
