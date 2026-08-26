"""Governed, value-minimized human performance-review evidence.

The packet correlates one proposed employee review to Employment and Job references,
a performance cycle, predetermined criteria and goals, an exact criterion-observation
snapshot, an optional development plan, and an accountable human reviewer. It does not
assert that those references resolve to one authoritative scope; that verification must
occur at the authoritative HRIS/performance boundary before rating. Opaque worker
references remain personal data because they can be re-associated with an identifiable
person through the authoritative HRIS boundary. Direct identifiers, rating values,
free-form feedback, and free-form model output remain outside this envelope.
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
from weakref import finalize

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]{1,31}:[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$"
)
_PURPOSE_CODE = "performance_review"
_ALLOWED_REASON_CODES = frozenset({"scheduled_cycle_review"})
_DECISION_AUTHORITY = "human_review_only"
_REVIEW_STATE = "requires_human_review"
_SCOPE_VERIFICATION_STATE = "requires_authoritative_resolution"
_NEXT_ACTION = (
    "Verify authoritative Employment/Job scope, performance-cycle dates, governed "
    "criteria and goals, criterion-observation evidence, and any development-plan "
    "provenance; then record accountable human rating and feedback through the "
    "authoritative performance workflow."
)
_PROCESS_PACKET_SEAL_KEY = secrets.token_bytes(32)
_PACKET_SEALS: dict[int, str] = {}
_PACKET_SEALS_LOCK = RLock()


def _discard_packet_seal(packet_id: int) -> None:
    """Discard process-local issuance evidence after its review packet is collected."""
    with _PACKET_SEALS_LOCK:
        _PACKET_SEALS.pop(packet_id, None)


def _register_packet_seal(packet: object, seal: str) -> None:
    """Bind one live review-packet identity to evidence outside writable slots."""
    packet_id = id(packet)
    with _PACKET_SEALS_LOCK:
        _PACKET_SEALS[packet_id] = seal
    finalize(packet, _discard_packet_seal, packet_id)


def _authoritative_packet_seal(packet: object) -> str | None:
    """Return process-local issuance evidence without trusting packet-owned state."""
    with _PACKET_SEALS_LOCK:
        return _PACKET_SEALS.get(id(packet))


def _seal_packet(payload_json: str) -> str:
    """Bind one process-local issuance to exact canonical performance-review bytes."""
    return hmac.new(_PROCESS_PACKET_SEAL_KEY, payload_json.encode("utf-8"), "sha256").hexdigest()


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
    """Require lowercase SHA-256 hexadecimal evidence."""
    if not isinstance(value, str) or not _DIGEST_PATTERN.fullmatch(value):
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


def _validate_business_date(value: date, field_name: str) -> None:
    """Require a business date rather than a datetime or textual date."""
    if type(value) is not date:
        raise ValueError(f"{field_name} must be a date")


def _validate_reason_code(value: str) -> None:
    """Require exact built-in text from the closed reviewed reason vocabulary."""
    if type(value) is not str or value not in _ALLOWED_REASON_CODES:
        raise ValueError("reason_code must be an authorized performance-review reason code")


def _validate_evidence_version(value: int) -> None:
    """Require a bounded positive integer version for high-impact review evidence."""
    if type(value) is not int or value < 1 or value > 2_147_483_647:
        raise ValueError("evidence_version must be an integer from 1 through 2147483647")


@dataclass(frozen=True, slots=True, repr=False, weakref_slot=True)
class PerformanceReviewPacket:
    """Immutable value-minimized review packet awaiting authoritative resolution."""

    tenant_record_id: str
    performance_review_reference: str
    person_record_reference: str
    employment_record_reference: str
    job_profile_reference: str
    performance_cycle_reference: str
    criterion_set_reference: str
    criterion_set_digest: str
    goal_plan_reference: str
    goal_plan_digest: str
    criterion_observation_snapshot_reference: str
    criterion_observation_snapshot_digest: str
    development_plan_reference: str | None
    development_plan_digest: str | None
    reviewer_reference: str
    purpose_code: str
    reason_code: str
    review_period_start: date
    review_period_end: date
    generated_at: datetime
    evidence_version: int = 1
    contains_personal_data: bool = True
    contains_direct_person_identifiers: bool = False
    contains_rating_value: bool = False
    contains_free_form_model_output: bool = False
    human_confirmation_required: bool = True
    decision_authority: str = _DECISION_AUTHORITY
    review_state: str = _REVIEW_STATE
    scope_verification_state: str = _SCOPE_VERIFICATION_STATE
    next_action: str = _NEXT_ACTION

    def __repr__(self) -> str:
        """Return a representation that never emits worker/rating correlation evidence."""
        return "PerformanceReviewPacket(<redacted>)"

    def __post_init__(self) -> None:
        """Fail closed when direct construction drifts from the governed contract."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.performance_review_reference,
            "performance_review",
            "performance_review_reference",
        )
        _validate_reference(self.person_record_reference, "person_record", "person_record_reference")
        _validate_reference(
            self.employment_record_reference,
            "employment_record",
            "employment_record_reference",
        )
        _validate_reference(self.job_profile_reference, "job_profile", "job_profile_reference")
        _validate_reference(
            self.performance_cycle_reference,
            "performance_cycle",
            "performance_cycle_reference",
        )
        _validate_reference(self.criterion_set_reference, "criterion_set", "criterion_set_reference")
        _validate_digest(self.criterion_set_digest, "criterion_set_digest")
        _validate_reference(self.goal_plan_reference, "performance_goal_plan", "goal_plan_reference")
        _validate_digest(self.goal_plan_digest, "goal_plan_digest")
        _validate_reference(
            self.criterion_observation_snapshot_reference,
            "criterion_observation_snapshot",
            "criterion_observation_snapshot_reference",
        )
        _validate_digest(
            self.criterion_observation_snapshot_digest,
            "criterion_observation_snapshot_digest",
        )
        if (self.development_plan_reference is None) != (self.development_plan_digest is None):
            raise ValueError("development plan reference and digest must be supplied together")
        if self.development_plan_reference is not None:
            _validate_reference(
                self.development_plan_reference,
                "development_plan",
                "development_plan_reference",
            )
            _validate_digest(self.development_plan_digest, "development_plan_digest")
        _validate_reference(self.reviewer_reference, "actor", "reviewer_reference")
        if type(self.purpose_code) is not str or self.purpose_code != _PURPOSE_CODE:
            raise ValueError("purpose_code must remain performance_review")
        _validate_reason_code(self.reason_code)
        _validate_business_date(self.review_period_start, "review_period_start")
        _validate_business_date(self.review_period_end, "review_period_end")
        if self.review_period_start > self.review_period_end:
            raise ValueError("review period start must not be after review period end")
        object.__setattr__(self, "generated_at", _freeze_timestamp(self.generated_at))
        _validate_evidence_version(self.evidence_version)
        if self.contains_personal_data is not True:
            raise ValueError("performance review packet contains personal data through worker references")
        if self.contains_direct_person_identifiers is not False:
            raise ValueError("performance review packet must not contain direct person identifiers")
        if self.contains_rating_value is not False:
            raise ValueError("performance review packet must not contain rating values")
        if self.contains_free_form_model_output is not False:
            raise ValueError("performance review packet must not contain free-form model output")
        if self.human_confirmation_required is not True:
            raise ValueError("human confirmation is mandatory before performance rating")
        if type(self.decision_authority) is not str or self.decision_authority != _DECISION_AUTHORITY:
            raise ValueError("decision_authority must remain human_review_only")
        if type(self.review_state) is not str or self.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain requires_human_review")
        if type(self.scope_verification_state) is not str or self.scope_verification_state != _SCOPE_VERIFICATION_STATE:
            raise ValueError(
                "scope_verification_state must remain requires_authoritative_resolution"
            )
        if type(self.next_action) is not str or self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed performance-review instruction")
        _register_packet_seal(self, _seal_packet(_canonical_packet_json_unchecked(self)))

    def canonical_json(self) -> str:
        """Return issuance-verified deterministic JSON for immutable audit correlation."""
        payload_json = _canonical_packet_json_unchecked(self)
        authoritative_seal = _authoritative_packet_seal(self)
        if authoritative_seal is None:
            raise ValueError("performance review issuance evidence is unavailable")
        if not hmac.compare_digest(authoritative_seal, _seal_packet(payload_json)):
            raise ValueError("performance review evidence changed after issuance")
        return payload_json

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact issuance-verified UTF-8 review packet."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _canonical_packet_json_unchecked(packet: PerformanceReviewPacket) -> str:
    """Render canonical bytes without consulting process-local issuance state."""
    payload = {
        "contains_direct_person_identifiers": packet.contains_direct_person_identifiers,
        "contains_free_form_model_output": packet.contains_free_form_model_output,
        "contains_personal_data": packet.contains_personal_data,
        "contains_rating_value": packet.contains_rating_value,
        "criterion_observation_snapshot_digest": packet.criterion_observation_snapshot_digest,
        "criterion_observation_snapshot_reference": packet.criterion_observation_snapshot_reference,
        "criterion_set_digest": packet.criterion_set_digest,
        "criterion_set_reference": packet.criterion_set_reference,
        "decision_authority": packet.decision_authority,
        "development_plan_digest": packet.development_plan_digest,
        "development_plan_reference": packet.development_plan_reference,
        "employment_record_reference": packet.employment_record_reference,
        "evidence_version": packet.evidence_version,
        "generated_at": _canonical_timestamp(packet.generated_at),
        "goal_plan_digest": packet.goal_plan_digest,
        "goal_plan_reference": packet.goal_plan_reference,
        "human_confirmation_required": packet.human_confirmation_required,
        "job_profile_reference": packet.job_profile_reference,
        "next_action": packet.next_action,
        "performance_cycle_reference": packet.performance_cycle_reference,
        "performance_review_reference": packet.performance_review_reference,
        "person_record_reference": packet.person_record_reference,
        "purpose_code": packet.purpose_code,
        "reason_code": packet.reason_code,
        "review_period_end": packet.review_period_end.isoformat(),
        "review_period_start": packet.review_period_start.isoformat(),
        "review_state": packet.review_state,
        "reviewer_reference": packet.reviewer_reference,
        "scope_verification_state": packet.scope_verification_state,
        "tenant_record_id": packet.tenant_record_id,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def build_performance_review_packet(
    *,
    tenant_record_id: str,
    performance_review_reference: str,
    person_record_reference: str,
    employment_record_reference: str,
    job_profile_reference: str,
    performance_cycle_reference: str,
    criterion_set_reference: str,
    criterion_set_digest: str,
    goal_plan_reference: str,
    goal_plan_digest: str,
    criterion_observation_snapshot_reference: str,
    criterion_observation_snapshot_digest: str,
    development_plan_reference: str | None,
    development_plan_digest: str | None,
    reviewer_reference: str,
    purpose_code: str,
    reason_code: str,
    review_period_start: date,
    review_period_end: date,
    generated_at: datetime,
    evidence_version: int = 1,
) -> PerformanceReviewPacket:
    """Build value-minimized performance-review evidence pending authoritative resolution."""
    return PerformanceReviewPacket(
        tenant_record_id=tenant_record_id,
        performance_review_reference=performance_review_reference,
        person_record_reference=person_record_reference,
        employment_record_reference=employment_record_reference,
        job_profile_reference=job_profile_reference,
        performance_cycle_reference=performance_cycle_reference,
        criterion_set_reference=criterion_set_reference,
        criterion_set_digest=criterion_set_digest,
        goal_plan_reference=goal_plan_reference,
        goal_plan_digest=goal_plan_digest,
        criterion_observation_snapshot_reference=criterion_observation_snapshot_reference,
        criterion_observation_snapshot_digest=criterion_observation_snapshot_digest,
        development_plan_reference=development_plan_reference,
        development_plan_digest=development_plan_digest,
        reviewer_reference=reviewer_reference,
        purpose_code=purpose_code,
        reason_code=reason_code,
        review_period_start=review_period_start,
        review_period_end=review_period_end,
        generated_at=generated_at,
        evidence_version=evidence_version,
    )
