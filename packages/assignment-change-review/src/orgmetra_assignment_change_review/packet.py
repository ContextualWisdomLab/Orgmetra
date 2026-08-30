"""Governed, value-free pre-mutation assignment-change review evidence.

The packet correlates one proposed internal assignment change to authoritative Person,
Employment, current Assignment/Job/Position scope, proposed Job/Position scope, an exact
current-scope snapshot, a reviewed workforce-allocation plan and policy, worker-impact
evidence, and a communication plan. Opaque Person references remain sensitive correlating
metadata. Person PII, compensation values, allocation values, and free-form model output
stay outside this envelope. Final relationship resolution, approval, and mutation remain
at the authoritative Orgmetra HRIS/People boundary.
"""
from __future__ import annotations

from contextvars import ContextVar
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
_PURPOSE_CODE = "assignment_change_review"
_ALLOWED_REASON_CODES = frozenset(
    {
        "internal_reassignment",
        "workforce_reallocation",
        "temporary_detail",
        "position_reclassification",
        "organizational_realignment",
    }
)
_DECISION_AUTHORITY = "human_review_only"
_REVIEW_STATE = "requires_human_review"
_SCOPE_VERIFICATION_STATE = "requires_authoritative_resolution"
_MUTATION_STATE = "not_authorized_to_apply"
_NEXT_ACTION = (
    "Before approval, re-resolve every packet reference within tenant_record_id; specifically "
    "re-resolve requester_reference and reviewer_reference through the authoritative actor "
    "boundary and verify their resolved actor identities are distinct, then verify the "
    "Person-to-Employment-to-current-Assignment binding and current Assignment/Job/Position "
    "worker scope; then verify proposed Position-to-Job binding and capacity, requested "
    "effective date, workforce-allocation policy, worker-impact evidence, and communication-"
    "plan provenance. Record accountable human approval and apply the change only through "
    "the authoritative People mutation boundary."
)
_PROCESS_PACKET_SEAL_KEY = secrets.token_bytes(32)
_PACKET_SEALS: dict[int, str] = {}
_CONSTRUCTING_PACKET_IDENTITIES: WeakValueDictionary[int, object] = WeakValueDictionary()
_ISSUED_PACKET_IDENTITIES: WeakValueDictionary[int, object] = WeakValueDictionary()
_ACTIVE_PACKET_CONSTRUCTOR = ContextVar("_ACTIVE_PACKET_CONSTRUCTOR", default=None)
_PACKET_SEALS_LOCK = RLock()


def _discard_packet_seal(packet_id: int) -> None:
    """Discard process-local issuance evidence after its review packet is collected."""
    with _PACKET_SEALS_LOCK:
        _PACKET_SEALS.pop(packet_id, None)


def _register_packet_seal(packet: object, seal: str) -> None:
    """Bind one live review-packet identity to exactly one issuance seal."""
    packet_id = id(packet)
    with _PACKET_SEALS_LOCK:
        if packet_id in _PACKET_SEALS:
            raise ValueError("assignment change review packet has already been issued")
        _PACKET_SEALS[packet_id] = seal
    finalize(packet, _discard_packet_seal, packet_id)


def _authoritative_packet_seal(packet: object) -> str | None:
    """Return process-local issuance evidence without trusting packet-owned state."""
    with _PACKET_SEALS_LOCK:
        return _PACKET_SEALS.get(id(packet))


def _seal_packet(payload_json: str) -> str:
    """Bind one process-local issuance to exact canonical assignment-change bytes."""
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


def _validate_evidence_version(value: int) -> None:
    """Require a bounded positive integer version for high-impact review evidence."""
    if type(value) is not int or value < 1 or value > 2_147_483_647:
        raise ValueError("evidence_version must be an integer from 1 through 2147483647")


class _AssignmentChangeReviewPacketMeta(type):
    """Grant one constructor ticket only to a normal full packet construction."""

    def __call__(cls, *args: object, **kwargs: object) -> object:
        """Arm one allocator ticket that the exact packet allocator must consume."""
        token = _ACTIVE_PACKET_CONSTRUCTOR.set(cls)
        try:
            return super().__call__(*args, **kwargs)
        finally:
            _ACTIVE_PACKET_CONSTRUCTOR.reset(token)


@dataclass(frozen=True, slots=True, repr=False, weakref_slot=True)
class AssignmentChangeReviewPacket(metaclass=_AssignmentChangeReviewPacketMeta):
    """Immutable assignment-change evidence that cannot itself authorize a mutation."""

    tenant_record_id: str
    assignment_change_review_reference: str
    person_record_reference: str
    employment_record_reference: str
    current_assignment_reference: str
    current_job_profile_reference: str
    current_position_record_reference: str
    proposed_job_profile_reference: str
    proposed_position_record_reference: str
    current_scope_snapshot_reference: str
    current_scope_snapshot_digest: str
    allocation_plan_reference: str
    allocation_plan_digest: str
    allocation_policy_reference: str
    allocation_policy_digest: str
    worker_impact_assessment_reference: str
    worker_impact_assessment_digest: str
    communication_plan_reference: str
    communication_plan_digest: str
    requester_reference: str
    reviewer_reference: str
    purpose_code: str
    reason_code: str
    requested_effective_on: date
    generated_at: datetime
    evidence_version: int = 1
    contains_person_pii: bool = False
    contains_compensation_values: bool = False
    contains_free_form_model_output: bool = False
    human_confirmation_required: bool = True
    decision_authority: str = _DECISION_AUTHORITY
    review_state: str = _REVIEW_STATE
    scope_verification_state: str = _SCOPE_VERIFICATION_STATE
    mutation_state: str = _MUTATION_STATE
    next_action: str = _NEXT_ACTION

    def __new__(cls, *_args: object, **_kwargs: object) -> AssignmentChangeReviewPacket:
        """Consume constructor provenance before validation invokes caller-owned code."""
        instance = object.__new__(cls)
        if _ACTIVE_PACKET_CONSTRUCTOR.get() is cls:
            _ACTIVE_PACKET_CONSTRUCTOR.set(None)
            with _PACKET_SEALS_LOCK:
                _CONSTRUCTING_PACKET_IDENTITIES[id(instance)] = instance
        return instance

    def __repr__(self) -> str:
        """Return a representation that never emits worker/assignment correlation evidence."""
        return "AssignmentChangeReviewPacket(<redacted>)"

    def __post_init__(self) -> None:
        """Fail closed when direct construction drifts from the governed contract."""
        with _PACKET_SEALS_LOCK:
            if _ISSUED_PACKET_IDENTITIES.get(id(self)) is self:
                raise ValueError("assignment change review packet has already been issued")
            if _CONSTRUCTING_PACKET_IDENTITIES.get(id(self)) is not self:
                raise ValueError("assignment change review constructor provenance is unavailable")
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.assignment_change_review_reference,
            "assignment_change_review",
            "assignment_change_review_reference",
        )
        _validate_reference(self.person_record_reference, "person_record", "person_record_reference")
        _validate_reference(
            self.employment_record_reference,
            "employment_record",
            "employment_record_reference",
        )
        _validate_reference(
            self.current_assignment_reference,
            "assignment_record",
            "current_assignment_reference",
        )
        _validate_reference(
            self.current_job_profile_reference,
            "job_profile",
            "current_job_profile_reference",
        )
        _validate_reference(
            self.current_position_record_reference,
            "position_record",
            "current_position_record_reference",
        )
        _validate_reference(
            self.proposed_job_profile_reference,
            "job_profile",
            "proposed_job_profile_reference",
        )
        _validate_reference(
            self.proposed_position_record_reference,
            "position_record",
            "proposed_position_record_reference",
        )
        _validate_reference(
            self.current_scope_snapshot_reference,
            "assignment_scope_snapshot",
            "current_scope_snapshot_reference",
        )
        _validate_digest(self.current_scope_snapshot_digest, "current_scope_snapshot_digest")
        _validate_reference(
            self.allocation_plan_reference,
            "workforce_allocation_plan",
            "allocation_plan_reference",
        )
        _validate_digest(self.allocation_plan_digest, "allocation_plan_digest")
        _validate_reference(
            self.allocation_policy_reference,
            "workforce_allocation_policy",
            "allocation_policy_reference",
        )
        _validate_digest(self.allocation_policy_digest, "allocation_policy_digest")
        _validate_reference(
            self.worker_impact_assessment_reference,
            "worker_impact_assessment",
            "worker_impact_assessment_reference",
        )
        _validate_digest(
            self.worker_impact_assessment_digest,
            "worker_impact_assessment_digest",
        )
        _validate_reference(
            self.communication_plan_reference,
            "assignment_communication_plan",
            "communication_plan_reference",
        )
        _validate_digest(self.communication_plan_digest, "communication_plan_digest")
        _validate_reference(self.requester_reference, "actor", "requester_reference")
        _validate_reference(self.reviewer_reference, "actor", "reviewer_reference")
        if self.requester_reference == self.reviewer_reference:
            raise ValueError("requester and reviewer must be different actors")
        if type(self.purpose_code) is not str or self.purpose_code != _PURPOSE_CODE:
            raise ValueError("purpose_code must remain assignment_change_review")
        _validate_code(self.reason_code, "reason_code")
        if self.reason_code not in _ALLOWED_REASON_CODES:
            raise ValueError("reason_code must be an approved assignment-change reason")
        _validate_business_date(self.requested_effective_on, "requested_effective_on")
        object.__setattr__(self, "generated_at", _freeze_timestamp(self.generated_at))
        _validate_evidence_version(self.evidence_version)
        if self.contains_person_pii is not False:
            raise ValueError("assignment change review packet must not contain person PII")
        if self.contains_compensation_values is not False:
            raise ValueError("assignment change review packet must not contain compensation values")
        if self.contains_free_form_model_output is not False:
            raise ValueError("assignment change review packet must not contain free-form model output")
        if self.human_confirmation_required is not True:
            raise ValueError("human confirmation is mandatory before assignment change")
        if type(self.decision_authority) is not str or self.decision_authority != _DECISION_AUTHORITY:
            raise ValueError("decision_authority must remain human_review_only")
        if type(self.review_state) is not str or self.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain requires_human_review")
        if type(self.scope_verification_state) is not str or self.scope_verification_state != _SCOPE_VERIFICATION_STATE:
            raise ValueError(
                "scope_verification_state must remain requires_authoritative_resolution"
            )
        if type(self.mutation_state) is not str or self.mutation_state != _MUTATION_STATE:
            raise ValueError("mutation_state must remain not_authorized_to_apply")
        if type(self.next_action) is not str or self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed assignment-change instruction")
        _register_packet_seal(self, _seal_packet(_canonical_packet_json_unchecked(self)))
        with _PACKET_SEALS_LOCK:
            _ISSUED_PACKET_IDENTITIES[id(self)] = self
            _CONSTRUCTING_PACKET_IDENTITIES.pop(id(self), None)

    def canonical_json(self) -> str:
        """Return issuance-verified deterministic JSON for immutable audit correlation."""
        with _PACKET_SEALS_LOCK:
            if _ISSUED_PACKET_IDENTITIES.get(id(self)) is not self:
                raise ValueError("assignment change review issuance evidence is unavailable")
        payload_json = _canonical_packet_json_unchecked(self)
        authoritative_seal = _authoritative_packet_seal(self)
        if authoritative_seal is None:
            raise ValueError("assignment change review issuance evidence is unavailable")
        if not hmac.compare_digest(authoritative_seal, _seal_packet(payload_json)):
            raise ValueError("assignment change review evidence changed after issuance")
        return payload_json

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact issuance-verified UTF-8 assignment-change packet."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _canonical_packet_json_unchecked(packet: AssignmentChangeReviewPacket) -> str:
    """Render canonical bytes without consulting process-local issuance state."""
    payload = {
        "allocation_plan_digest": packet.allocation_plan_digest,
        "allocation_plan_reference": packet.allocation_plan_reference,
        "allocation_policy_digest": packet.allocation_policy_digest,
        "allocation_policy_reference": packet.allocation_policy_reference,
        "assignment_change_review_reference": packet.assignment_change_review_reference,
        "communication_plan_digest": packet.communication_plan_digest,
        "communication_plan_reference": packet.communication_plan_reference,
        "contains_compensation_values": packet.contains_compensation_values,
        "contains_free_form_model_output": packet.contains_free_form_model_output,
        "contains_person_pii": packet.contains_person_pii,
        "current_assignment_reference": packet.current_assignment_reference,
        "current_job_profile_reference": packet.current_job_profile_reference,
        "current_position_record_reference": packet.current_position_record_reference,
        "current_scope_snapshot_digest": packet.current_scope_snapshot_digest,
        "current_scope_snapshot_reference": packet.current_scope_snapshot_reference,
        "decision_authority": packet.decision_authority,
        "employment_record_reference": packet.employment_record_reference,
        "evidence_version": packet.evidence_version,
        "generated_at": _canonical_timestamp(packet.generated_at),
        "human_confirmation_required": packet.human_confirmation_required,
        "mutation_state": packet.mutation_state,
        "next_action": packet.next_action,
        "person_record_reference": packet.person_record_reference,
        "proposed_job_profile_reference": packet.proposed_job_profile_reference,
        "proposed_position_record_reference": packet.proposed_position_record_reference,
        "purpose_code": packet.purpose_code,
        "reason_code": packet.reason_code,
        "requested_effective_on": packet.requested_effective_on.isoformat(),
        "requester_reference": packet.requester_reference,
        "review_state": packet.review_state,
        "reviewer_reference": packet.reviewer_reference,
        "scope_verification_state": packet.scope_verification_state,
        "tenant_record_id": packet.tenant_record_id,
        "worker_impact_assessment_digest": packet.worker_impact_assessment_digest,
        "worker_impact_assessment_reference": packet.worker_impact_assessment_reference,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def build_assignment_change_review_packet(
    *,
    tenant_record_id: str,
    assignment_change_review_reference: str,
    person_record_reference: str,
    employment_record_reference: str,
    current_assignment_reference: str,
    current_job_profile_reference: str,
    current_position_record_reference: str,
    proposed_job_profile_reference: str,
    proposed_position_record_reference: str,
    current_scope_snapshot_reference: str,
    current_scope_snapshot_digest: str,
    allocation_plan_reference: str,
    allocation_plan_digest: str,
    allocation_policy_reference: str,
    allocation_policy_digest: str,
    worker_impact_assessment_reference: str,
    worker_impact_assessment_digest: str,
    communication_plan_reference: str,
    communication_plan_digest: str,
    requester_reference: str,
    reviewer_reference: str,
    purpose_code: str,
    reason_code: str,
    requested_effective_on: date,
    generated_at: datetime,
    evidence_version: int = 1,
) -> AssignmentChangeReviewPacket:
    """Build a value-free assignment-change packet pending authoritative approval."""
    return AssignmentChangeReviewPacket(
        tenant_record_id=tenant_record_id,
        assignment_change_review_reference=assignment_change_review_reference,
        person_record_reference=person_record_reference,
        employment_record_reference=employment_record_reference,
        current_assignment_reference=current_assignment_reference,
        current_job_profile_reference=current_job_profile_reference,
        current_position_record_reference=current_position_record_reference,
        proposed_job_profile_reference=proposed_job_profile_reference,
        proposed_position_record_reference=proposed_position_record_reference,
        current_scope_snapshot_reference=current_scope_snapshot_reference,
        current_scope_snapshot_digest=current_scope_snapshot_digest,
        allocation_plan_reference=allocation_plan_reference,
        allocation_plan_digest=allocation_plan_digest,
        allocation_policy_reference=allocation_policy_reference,
        allocation_policy_digest=allocation_policy_digest,
        worker_impact_assessment_reference=worker_impact_assessment_reference,
        worker_impact_assessment_digest=worker_impact_assessment_digest,
        communication_plan_reference=communication_plan_reference,
        communication_plan_digest=communication_plan_digest,
        requester_reference=requester_reference,
        reviewer_reference=reviewer_reference,
        purpose_code=purpose_code,
        reason_code=reason_code,
        requested_effective_on=requested_effective_on,
        generated_at=generated_at,
        evidence_version=evidence_version,
    )