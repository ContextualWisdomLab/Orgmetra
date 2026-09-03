"""Governed organization-hierarchy change review evidence.

This module defines a value-minimized pre-mutation review packet for changing
one Organization Unit parent relationship. It does not mutate HRIS truth or
authorize an employment decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import re
from threading import RLock
from uuid import UUID
from weakref import WeakKeyDictionary, WeakValueDictionary

_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_MAX_UUID_INT = (1 << 128) - 1
_TIMEZONE_TYPE = type(timezone.utc)
_PURPOSE_CODE = "organization_hierarchy_change_review"
_ALLOWED_REASON_CODES = frozenset(
    {
        "administrative_correction",
        "legal_entity_restructure",
        "operating_model_change",
        "organizational_realignment",
    }
)
_REVIEW_STATE = "requires_human_review"
_SCOPE_STATE = "requires_authoritative_resolution"
_MUTATION_STATE = "not_authorized_to_apply"
_DECISION_AUTHORITY = "human_review_only"
_NEXT_ACTION = (
    "Within tenant_record_id, re-resolve the Organization Unit, current parent, proposed parent, "
    "and current hierarchy through authoritative Orgmetra HRIS boundaries at effective_on and the "
    "current system-recorded cutoff; prove every referenced Organization Unit is same-tenant and "
    "valid, verify the reviewed unit and hierarchy snapshot digests plus reason, prove requester/"
    "reviewer authoritative actor separation, reject self-parenting, cycles, multiple visible parents, "
    "or stale current-parent evidence, then invoke the authoritative organization-hierarchy mutation "
    "boundary with immutable audit/outbox evidence. This packet is review evidence only and is not "
    "authorization to mutate HRIS truth or make an employment decision."
)


class _LiveReferenceBinding:
    """Keep one evidence digest alive while any idempotent packet instance is alive."""

    __slots__ = ("evidence_digest", "__weakref__")

    def __init__(self, evidence_digest: str) -> None:
        """Bind one tenant-qualified hierarchy-change reference to one digest."""
        self.evidence_digest = evidence_digest


_REGISTRY_LOCK = RLock()
_CREATION_DIGESTS: WeakKeyDictionary[OrganizationHierarchyChangeReviewPacket, str] = WeakKeyDictionary()
_LIVE_REFERENCE_BINDINGS: WeakValueDictionary[tuple[str, str], _LiveReferenceBinding] = WeakValueDictionary()
_PACKET_BINDINGS: WeakKeyDictionary[
    OrganizationHierarchyChangeReviewPacket, _LiveReferenceBinding
] = WeakKeyDictionary()


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


def _validate_optional_organization_reference(value: object, field_name: str) -> None:
    """Accept absence or one authoritative Organization Unit reference."""
    if value is None:
        return
    _validate_reference(value, "organization_unit", field_name, require_uuid4=False)


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
    try:
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except (OverflowError, ValueError) as exc:
        raise ValueError("recorded_at must be representable as a UTC datetime") from exc


def _validate_issuance_timestamp(value: object) -> None:
    """Require structurally valid system-recorded evidence that has already occurred."""
    _canonical_timestamp(value)
    if value > datetime.now(timezone.utc):
        raise ValueError("recorded_at must not be in the future")


def _payload(packet: OrganizationHierarchyChangeReviewPacket) -> dict[str, object]:
    """Snapshot all trust-bearing fields once for validation and canonical emission."""
    return {
        "contains_employment_decision": packet.contains_employment_decision,
        "contains_person_identifier": packet.contains_person_identifier,
        "contains_worker_value": packet.contains_worker_value,
        "current_parent_organization_unit_reference": packet.current_parent_organization_unit_reference,
        "decision_authority": packet.decision_authority,
        "effective_on": _canonical_date(packet.effective_on),
        "evidence_version": packet.evidence_version,
        "hierarchy_snapshot_digest": packet.hierarchy_snapshot_digest,
        "human_review_required": packet.human_review_required,
        "mutation_state": packet.mutation_state,
        "next_action": packet.next_action,
        "organization_hierarchy_change_reference": packet.organization_hierarchy_change_reference,
        "organization_unit_reference": packet.organization_unit_reference,
        "organization_unit_snapshot_digest": packet.organization_unit_snapshot_digest,
        "proposed_parent_organization_unit_reference": packet.proposed_parent_organization_unit_reference,
        "purpose_code": packet.purpose_code,
        "reason_code": packet.reason_code,
        "recorded_at": _canonical_timestamp(packet.recorded_at),
        "requester_reference": packet.requester_reference,
        "review_state": packet.review_state,
        "reviewer_reference": packet.reviewer_reference,
        "scope_verification_state": packet.scope_verification_state,
        "tenant_record_id": packet.tenant_record_id,
    }


def _canonical_payload_json(payload: dict[str, object]) -> str:
    """Serialize one already-snapshotted payload deterministically."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True, slots=True, repr=False, eq=False, weakref_slot=True)
class OrganizationHierarchyChangeReviewPacket:
    """PII-minimized human-review evidence for one Organization Unit reparenting."""

    tenant_record_id: str
    organization_hierarchy_change_reference: str
    organization_unit_reference: str
    current_parent_organization_unit_reference: str | None
    proposed_parent_organization_unit_reference: str | None
    effective_on: date
    organization_unit_snapshot_digest: str
    hierarchy_snapshot_digest: str
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
        """Return a representation that never emits hierarchy correlations."""
        return "OrganizationHierarchyChangeReviewPacket(<redacted>)"

    def __post_init__(self) -> None:
        """Validate the review contract and bind its live reference to creation evidence."""
        _validate_operational_uuid_text(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.organization_hierarchy_change_reference,
            "organization_hierarchy_change",
            "organization_hierarchy_change_reference",
            require_uuid4=True,
        )
        _validate_reference(
            self.organization_unit_reference,
            "organization_unit",
            "organization_unit_reference",
            require_uuid4=False,
        )
        _validate_optional_organization_reference(
            self.current_parent_organization_unit_reference,
            "current_parent_organization_unit_reference",
        )
        _validate_optional_organization_reference(
            self.proposed_parent_organization_unit_reference,
            "proposed_parent_organization_unit_reference",
        )
        if self.current_parent_organization_unit_reference == self.proposed_parent_organization_unit_reference:
            raise ValueError("proposed parent must differ from the current parent")
        if self.current_parent_organization_unit_reference == self.organization_unit_reference:
            raise ValueError("organization unit cannot be its own current parent")
        if self.proposed_parent_organization_unit_reference == self.organization_unit_reference:
            raise ValueError("organization unit cannot be its own proposed parent")
        _canonical_date(self.effective_on)
        _validate_digest(self.organization_unit_snapshot_digest, "organization_unit_snapshot_digest")
        _validate_digest(self.hierarchy_snapshot_digest, "hierarchy_snapshot_digest")
        _validate_reference(self.requester_reference, "actor", "requester_reference", require_uuid4=True)
        _validate_reference(self.reviewer_reference, "actor", "reviewer_reference", require_uuid4=True)
        if self.requester_reference == self.reviewer_reference:
            raise ValueError("reviewer_reference must identify a different accountable actor")
        _validate_code(self.purpose_code, "purpose_code")
        if self.purpose_code != _PURPOSE_CODE:
            raise ValueError("purpose_code must remain organization_hierarchy_change_review")
        _validate_code(self.reason_code, "reason_code")
        if self.reason_code not in _ALLOWED_REASON_CODES:
            raise ValueError("reason_code must use the reviewed hierarchy-change vocabulary")
        _validate_issuance_timestamp(self.recorded_at)
        _validate_positive_int(self.evidence_version, "evidence_version")
        if self.contains_person_identifier is not False:
            raise ValueError("hierarchy-change evidence must not contain a person identifier")
        if self.contains_worker_value is not False:
            raise ValueError("hierarchy-change evidence must not contain worker values")
        if self.contains_employment_decision is not False:
            raise ValueError("hierarchy-change evidence must not contain an employment decision")
        if self.human_review_required is not True:
            raise ValueError("human review is mandatory before organization-hierarchy mutation")
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
            raise ValueError("next_action must remain the governed hierarchy-change instruction")

        payload_json = _canonical_payload_json(_payload(self))
        creation_digest = sha256(payload_json.encode("utf-8")).hexdigest()
        live_key = (self.tenant_record_id, self.organization_hierarchy_change_reference)
        with _REGISTRY_LOCK:
            binding = _LIVE_REFERENCE_BINDINGS.get(live_key)
            if binding is None:
                binding = _LiveReferenceBinding(creation_digest)
                _LIVE_REFERENCE_BINDINGS[live_key] = binding
            elif binding.evidence_digest != creation_digest:
                raise ValueError(
                    "organization_hierarchy_change_reference is already bound to different live evidence"
                )
            _CREATION_DIGESTS[self] = creation_digest
            _PACKET_BINDINGS[self] = binding

    def canonical_json(self) -> str:
        """Return one verified snapshot of deterministic canonical audit evidence."""
        payload = _payload(self)
        payload_json = _canonical_payload_json(payload)
        current_digest = sha256(payload_json.encode("utf-8")).hexdigest()
        with _REGISTRY_LOCK:
            creation_digest = _CREATION_DIGESTS.get(self)
        if current_digest != creation_digest:
            raise ValueError("organization hierarchy-change evidence changed after issuance")
        return payload_json

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact verified canonical UTF-8 evidence."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_organization_hierarchy_change_review_packet(
    *,
    tenant_record_id: str,
    organization_hierarchy_change_reference: str,
    organization_unit_reference: str,
    current_parent_organization_unit_reference: str | None,
    proposed_parent_organization_unit_reference: str | None,
    effective_on: date,
    organization_unit_snapshot_digest: str,
    hierarchy_snapshot_digest: str,
    requester_reference: str,
    reviewer_reference: str,
    purpose_code: str,
    reason_code: str,
    recorded_at: datetime,
    evidence_version: int = 1,
) -> OrganizationHierarchyChangeReviewPacket:
    """Build value-minimized hierarchy-change evidence pending authoritative mutation."""
    return OrganizationHierarchyChangeReviewPacket(
        tenant_record_id=tenant_record_id,
        organization_hierarchy_change_reference=organization_hierarchy_change_reference,
        organization_unit_reference=organization_unit_reference,
        current_parent_organization_unit_reference=current_parent_organization_unit_reference,
        proposed_parent_organization_unit_reference=proposed_parent_organization_unit_reference,
        effective_on=effective_on,
        organization_unit_snapshot_digest=organization_unit_snapshot_digest,
        hierarchy_snapshot_digest=hierarchy_snapshot_digest,
        requester_reference=requester_reference,
        reviewer_reference=reviewer_reference,
        purpose_code=purpose_code,
        reason_code=reason_code,
        recorded_at=recorded_at,
        evidence_version=evidence_version,
    )
