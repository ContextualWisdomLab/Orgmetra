"""Governed position-reporting change review evidence.

This package defines a value-minimized pre-mutation review packet for changing
one Position-to-Position solid-line reporting relationship. It does not mutate
HRIS truth or authorize an employment decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import re
from threading import RLock
from uuid import UUID
from weakref import WeakKeyDictionary

_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_MAX_UUID_INT = (1 << 128) - 1
_TIMEZONE_TYPE = type(timezone.utc)
_PURPOSE_CODE = "position_reporting_change_review"
_ALLOWED_REASON_CODES = frozenset(
    {
        "manager_vacancy",
        "operating_model_change",
        "organizational_realignment",
        "span_of_control_adjustment",
    }
)
_REVIEW_STATE = "requires_human_review"
_SCOPE_STATE = "requires_authoritative_resolution"
_MUTATION_STATE = "not_authorized_to_apply"
_DECISION_AUTHORITY = "human_review_only"
_NEXT_ACTION = (
    "Within tenant_record_id, re-resolve the subordinate, current-manager, and proposed-manager "
    "Position records and the current solid-line reporting relationship through authoritative "
    "Orgmetra HRIS boundaries at effective_on and the current system-recorded cutoff; prove all "
    "positions are same-tenant, valid and staffable, prove requester/reviewer authoritative actor "
    "separation, reject cycles or multiple visible solid-line managers, verify the reviewed scope "
    "digests and reason, then invoke the authoritative reporting-line mutation boundary with "
    "immutable audit/outbox evidence. This packet is review evidence only and is not authorization "
    "to mutate HRIS truth or make an employment decision."
)

_REGISTRY_LOCK = RLock()
_CREATION_DIGESTS: WeakKeyDictionary[PositionReportingChangeReviewPacket, str] = WeakKeyDictionary()


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
    """Require one bounded namespaced canonical UUID reference."""
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
    if type(value) is not str or len(value) > 64 or not _CODE_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be bounded lower snake_case governance text")


def _validate_positive_int(value: object, field_name: str) -> None:
    """Require one exact positive bounded built-in integer."""
    if type(value) is not int or value < 1 or value > 2_147_483_647:
        raise ValueError(f"{field_name} must be a positive 32-bit integer")


def _canonical_date(value: object) -> str:
    """Render one exact built-in business date."""
    if type(value) is not date:
        raise ValueError("effective_on must be an exact date")
    return value.isoformat()


def _canonical_timestamp(value: object) -> str:
    """Render one exact datetime with a built-in fixed offset as UTC RFC 3339 text."""
    if type(value) is not datetime or type(value.tzinfo) is not _TIMEZONE_TYPE:
        raise ValueError("recorded_at must use a built-in fixed-offset timezone")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _payload(packet: PositionReportingChangeReviewPacket) -> dict[str, object]:
    """Snapshot all trust-bearing fields once for validation and canonical emission."""
    return {
        "contains_employment_decision": packet.contains_employment_decision,
        "contains_person_identifier": packet.contains_person_identifier,
        "contains_worker_value": packet.contains_worker_value,
        "decision_authority": packet.decision_authority,
        "effective_on": _canonical_date(packet.effective_on),
        "evidence_version": packet.evidence_version,
        "human_review_required": packet.human_review_required,
        "mutation_state": packet.mutation_state,
        "next_action": packet.next_action,
        "organization_scope_snapshot_digest": packet.organization_scope_snapshot_digest,
        "position_reporting_change_reference": packet.position_reporting_change_reference,
        "position_scope_snapshot_digest": packet.position_scope_snapshot_digest,
        "proposed_manager_position_reference": packet.proposed_manager_position_reference,
        "purpose_code": packet.purpose_code,
        "reason_code": packet.reason_code,
        "recorded_at": _canonical_timestamp(packet.recorded_at),
        "requester_reference": packet.requester_reference,
        "review_state": packet.review_state,
        "reviewer_reference": packet.reviewer_reference,
        "scope_verification_state": packet.scope_verification_state,
        "subordinate_position_reference": packet.subordinate_position_reference,
        "current_manager_position_reference": packet.current_manager_position_reference,
        "tenant_record_id": packet.tenant_record_id,
    }


def _canonical_payload_json(payload: dict[str, object]) -> str:
    """Serialize one already-snapshotted payload deterministically."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True, slots=True, repr=False, eq=False, weakref_slot=True)
class PositionReportingChangeReviewPacket:
    """PII-minimized human-review evidence for one reporting-line reassignment."""

    tenant_record_id: str
    position_reporting_change_reference: str
    subordinate_position_reference: str
    current_manager_position_reference: str
    proposed_manager_position_reference: str
    effective_on: date
    position_scope_snapshot_digest: str
    organization_scope_snapshot_digest: str
    requester_reference: str
    reviewer_reference: str
    purpose_code: str
    reason_code: str
    recorded_at: datetime
    evidence_version: int = 1
    contains_person_identifier: bool = False
    contains_worker_value: bool = False
    contains_employment_decision: bool = False
    human_review_required: bool = True
    review_state: str = _REVIEW_STATE
    scope_verification_state: str = _SCOPE_STATE
    mutation_state: str = _MUTATION_STATE
    decision_authority: str = _DECISION_AUTHORITY
    next_action: str = _NEXT_ACTION

    def __repr__(self) -> str:
        """Return a representation that never emits reporting correlations."""
        return "PositionReportingChangeReviewPacket(<redacted>)"

    def __post_init__(self) -> None:
        """Validate the review contract and seal its creation-time evidence."""
        _validate_operational_uuid_text(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.position_reporting_change_reference,
            "position_reporting_change",
            "position_reporting_change_reference",
            require_uuid4=True,
        )
        _validate_reference(
            self.subordinate_position_reference,
            "position_record",
            "subordinate_position_reference",
            require_uuid4=False,
        )
        _validate_reference(
            self.current_manager_position_reference,
            "position_record",
            "current_manager_position_reference",
            require_uuid4=False,
        )
        _validate_reference(
            self.proposed_manager_position_reference,
            "position_record",
            "proposed_manager_position_reference",
            require_uuid4=False,
        )
        if self.subordinate_position_reference == self.current_manager_position_reference:
            raise ValueError("subordinate position must differ from the current manager position")
        if self.subordinate_position_reference == self.proposed_manager_position_reference:
            raise ValueError("subordinate position must differ from the proposed manager position")
        if self.current_manager_position_reference == self.proposed_manager_position_reference:
            raise ValueError("proposed manager position must differ from the current manager position")
        _canonical_date(self.effective_on)
        _validate_digest(self.position_scope_snapshot_digest, "position_scope_snapshot_digest")
        _validate_digest(
            self.organization_scope_snapshot_digest,
            "organization_scope_snapshot_digest",
        )
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
            raise ValueError("purpose_code must remain position_reporting_change_review")
        _validate_code(self.reason_code, "reason_code")
        if self.reason_code not in _ALLOWED_REASON_CODES:
            raise ValueError("reason_code must use the reviewed reporting-change vocabulary")
        _canonical_timestamp(self.recorded_at)
        _validate_positive_int(self.evidence_version, "evidence_version")
        if self.contains_person_identifier is not False:
            raise ValueError("reporting-change evidence must not contain a person identifier")
        if self.contains_worker_value is not False:
            raise ValueError("reporting-change evidence must not contain worker values")
        if self.contains_employment_decision is not False:
            raise ValueError("reporting-change evidence must not contain an employment decision")
        if self.human_review_required is not True:
            raise ValueError("human review is mandatory before reporting-line mutation")
        _validate_code(self.review_state, "review_state")
        if self.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain requires_human_review")
        _validate_code(self.scope_verification_state, "scope_verification_state")
        if self.scope_verification_state != _SCOPE_STATE:
            raise ValueError("scope_verification_state must remain requires_authoritative_resolution")
        _validate_code(self.mutation_state, "mutation_state")
        if self.mutation_state != _MUTATION_STATE:
            raise ValueError("mutation_state must remain not_authorized_to_apply")
        _validate_code(self.decision_authority, "decision_authority")
        if self.decision_authority != _DECISION_AUTHORITY:
            raise ValueError("decision_authority must remain human_review_only")
        if type(self.next_action) is not str or self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed reporting-change instruction")

        payload_json = _canonical_payload_json(_payload(self))
        creation_digest = sha256(payload_json.encode("utf-8")).hexdigest()
        with _REGISTRY_LOCK:
            _CREATION_DIGESTS[self] = creation_digest

    def canonical_json(self) -> str:
        """Return one verified snapshot of deterministic canonical audit evidence."""
        payload = _payload(self)
        payload_json = _canonical_payload_json(payload)
        current_digest = sha256(payload_json.encode("utf-8")).hexdigest()
        with _REGISTRY_LOCK:
            creation_digest = _CREATION_DIGESTS.get(self)
        if current_digest != creation_digest:
            raise ValueError("position reporting-change evidence changed after issuance")
        return payload_json

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact verified canonical UTF-8 evidence."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_position_reporting_change_review_packet(
    *,
    tenant_record_id: str,
    position_reporting_change_reference: str,
    subordinate_position_reference: str,
    current_manager_position_reference: str,
    proposed_manager_position_reference: str,
    effective_on: date,
    position_scope_snapshot_digest: str,
    organization_scope_snapshot_digest: str,
    requester_reference: str,
    reviewer_reference: str,
    purpose_code: str,
    reason_code: str,
    recorded_at: datetime,
    evidence_version: int = 1,
) -> PositionReportingChangeReviewPacket:
    """Build value-minimized reporting-change evidence pending authoritative mutation."""
    return PositionReportingChangeReviewPacket(
        tenant_record_id=tenant_record_id,
        position_reporting_change_reference=position_reporting_change_reference,
        subordinate_position_reference=subordinate_position_reference,
        current_manager_position_reference=current_manager_position_reference,
        proposed_manager_position_reference=proposed_manager_position_reference,
        effective_on=effective_on,
        position_scope_snapshot_digest=position_scope_snapshot_digest,
        organization_scope_snapshot_digest=organization_scope_snapshot_digest,
        requester_reference=requester_reference,
        reviewer_reference=reviewer_reference,
        purpose_code=purpose_code,
        reason_code=reason_code,
        recorded_at=recorded_at,
        evidence_version=evidence_version,
    )
