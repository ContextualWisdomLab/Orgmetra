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
from weakref import WeakKeyDictionary, WeakSet, WeakValueDictionary

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


def _validate_operational_uuid_text(
    value: object,
    field_name: str,
    *,
    _uuid_type: type[UUID] = UUID,
    _max_uuid_int: int = _MAX_UUID_INT,
) -> None:
    """Require exact canonical non-sentinel UUID text owned by the HRIS boundary."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be canonical UUID text")
    try:
        parsed = _uuid_type(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{field_name} must be canonical UUID text") from exc
    if str(parsed) != value or parsed.int in (0, _max_uuid_int):
        raise ValueError(f"{field_name} must be a canonical operational UUID")


def _validate_reference(
    value: object,
    prefix: str,
    field_name: str,
    *,
    require_uuid4: bool,
    _uuid_type: type[UUID] = UUID,
    _max_uuid_int: int = _MAX_UUID_INT,
) -> None:
    """Require one bounded namespaced canonical UUID reference."""
    error = f"{field_name} must be a canonical {prefix}: reference"
    if type(value) is not str or len(value) > 160 or not value.startswith(f"{prefix}:"):
        raise ValueError(error)
    suffix = value[len(prefix) + 1 :]
    try:
        parsed = _uuid_type(suffix)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(error) from exc
    if str(parsed) != suffix or parsed.int in (0, _max_uuid_int):
        raise ValueError(error)
    if require_uuid4 and parsed.version != 4:
        raise ValueError(error)


def _validate_optional_organization_reference(
    value: object,
    field_name: str,
    *,
    _validate_reference_once: object = _validate_reference,
) -> None:
    """Accept absence or one authoritative Organization Unit reference."""
    if value is None:
        return
    _validate_reference_once(value, "organization_unit", field_name, require_uuid4=False)


def _validate_digest(
    value: object,
    field_name: str,
    *,
    _digest_pattern: object = _DIGEST_PATTERN,
) -> None:
    """Require exact built-in lowercase SHA-256 hexadecimal evidence."""
    if type(value) is not str or not _digest_pattern.fullmatch(value):
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _validate_code(
    value: object,
    field_name: str,
    *,
    _code_pattern: object = _CODE_PATTERN,
) -> None:
    """Require exact bounded two-or-more-word lower snake_case governance text."""
    if type(value) is not str or len(value) > 64 or not _code_pattern.fullmatch(value):
        raise ValueError(f"{field_name} must be bounded lower snake_case governance text")


def _validate_positive_int(value: object, field_name: str) -> None:
    """Require one exact positive bounded built-in integer."""
    if type(value) is not int or value < 1 or value > 2_147_483_647:
        raise ValueError(f"{field_name} must be a positive 32-bit integer")


def _canonical_date(value: object, *, _date_type: type[date] = date) -> str:
    """Render one exact built-in business date."""
    if type(value) is not _date_type:
        raise ValueError("effective_on must be an exact date")
    return value.isoformat()


def _canonical_timestamp(
    value: object,
    *,
    _datetime_type: type[datetime] = datetime,
    _timezone_type: type[timezone] = _TIMEZONE_TYPE,
    _utc_timezone: timezone = timezone.utc,
) -> str:
    """Render one exact datetime with a built-in fixed offset as UTC RFC 3339 text."""
    if type(value) is not _datetime_type or type(value.tzinfo) is not _timezone_type:
        raise ValueError("recorded_at must use a built-in fixed-offset timezone")
    try:
        return value.astimezone(_utc_timezone).isoformat().replace("+00:00", "Z")
    except (OverflowError, ValueError) as exc:
        raise ValueError("recorded_at must be representable as a UTC datetime") from exc


def _validate_issuance_timestamp(
    value: object,
    *,
    _canonical_timestamp_once: object = _canonical_timestamp,
    _datetime_type: type[datetime] = datetime,
    _utc_timezone: timezone = timezone.utc,
) -> None:
    """Require a canonical review-evidence timestamp that has already occurred."""
    _canonical_timestamp_once(value)
    if value > _datetime_type.now(_utc_timezone):
        raise ValueError("recorded_at must not be in the future")


def _snapshot(packet: OrganizationHierarchyChangeReviewPacket) -> dict[str, object]:
    """Capture each trust-bearing packet field once for one validation or export operation."""
    return {
        "contains_employment_decision": packet.contains_employment_decision,
        "contains_person_identifier": packet.contains_person_identifier,
        "contains_worker_value": packet.contains_worker_value,
        "current_parent_organization_unit_reference": packet.current_parent_organization_unit_reference,
        "decision_authority": packet.decision_authority,
        "effective_on": packet.effective_on,
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
        "recorded_at": packet.recorded_at,
        "requester_reference": packet.requester_reference,
        "review_state": packet.review_state,
        "reviewer_reference": packet.reviewer_reference,
        "scope_verification_state": packet.scope_verification_state,
        "tenant_record_id": packet.tenant_record_id,
    }


def _validate_payload_runtime_types(
    snapshot: dict[str, object],
    *,
    _date_type: type[date] = date,
    _datetime_type: type[datetime] = datetime,
) -> None:
    """Reject caller-owned scalar behavior in the exact snapshot chosen for export."""
    current_parent = snapshot["current_parent_organization_unit_reference"]
    proposed_parent = snapshot["proposed_parent_organization_unit_reference"]
    if not (
        type(snapshot["tenant_record_id"]) is str
        and type(snapshot["organization_hierarchy_change_reference"]) is str
        and type(snapshot["organization_unit_reference"]) is str
        and (current_parent is None or type(current_parent) is str)
        and (proposed_parent is None or type(proposed_parent) is str)
        and type(snapshot["effective_on"]) is _date_type
        and type(snapshot["organization_unit_snapshot_digest"]) is str
        and type(snapshot["hierarchy_snapshot_digest"]) is str
        and type(snapshot["requester_reference"]) is str
        and type(snapshot["reviewer_reference"]) is str
        and type(snapshot["purpose_code"]) is str
        and type(snapshot["reason_code"]) is str
        and type(snapshot["recorded_at"]) is _datetime_type
        and type(snapshot["evidence_version"]) is int
        and type(snapshot["contains_person_identifier"]) is bool
        and type(snapshot["contains_worker_value"]) is bool
        and type(snapshot["contains_employment_decision"]) is bool
        and type(snapshot["human_review_required"]) is bool
        and type(snapshot["review_state"]) is str
        and type(snapshot["scope_verification_state"]) is str
        and type(snapshot["mutation_state"]) is str
        and type(snapshot["decision_authority"]) is str
        and type(snapshot["next_action"]) is str
    ):
        raise ValueError("organization hierarchy-change evidence runtime types changed after issuance")


_ISSUANCE_VALIDATION_AUTHORITY = (
    _validate_operational_uuid_text,
    _validate_reference,
    _validate_optional_organization_reference,
    _canonical_date,
    _validate_digest,
    _validate_code,
    _validate_issuance_timestamp,
    _validate_positive_int,
    _PURPOSE_CODE,
    _ALLOWED_REASON_CODES,
    _REVIEW_STATE,
    _SCOPE_STATE,
    _MUTATION_STATE,
    _DECISION_AUTHORITY,
    _NEXT_ACTION,
)


def _validate_issuance_snapshot(
    snapshot: dict[str, object],
    *,
    _authority: tuple[object, ...] = _ISSUANCE_VALIDATION_AUTHORITY,
) -> None:
    """Validate exactly the snapshot that will be sealed as creation evidence."""
    tenant_record_id = snapshot["tenant_record_id"]
    change_reference = snapshot["organization_hierarchy_change_reference"]
    organization_unit_reference = snapshot["organization_unit_reference"]
    current_parent = snapshot["current_parent_organization_unit_reference"]
    proposed_parent = snapshot["proposed_parent_organization_unit_reference"]
    requester_reference = snapshot["requester_reference"]
    reviewer_reference = snapshot["reviewer_reference"]
    purpose_code = snapshot["purpose_code"]
    reason_code = snapshot["reason_code"]
    review_state = snapshot["review_state"]
    scope_verification_state = snapshot["scope_verification_state"]
    mutation_state = snapshot["mutation_state"]
    decision_authority = snapshot["decision_authority"]
    (
        validate_operational_uuid_text,
        validate_reference,
        validate_optional_organization_reference,
        canonical_date,
        validate_digest,
        validate_code,
        validate_issuance_timestamp,
        validate_positive_int,
        purpose_code_required,
        allowed_reason_codes,
        review_state_required,
        scope_state_required,
        mutation_state_required,
        decision_authority_required,
        next_action_required,
    ) = _authority

    validate_operational_uuid_text(tenant_record_id, "tenant_record_id")
    validate_reference(
        change_reference,
        "organization_hierarchy_change",
        "organization_hierarchy_change_reference",
        require_uuid4=True,
    )
    validate_reference(
        organization_unit_reference,
        "organization_unit",
        "organization_unit_reference",
        require_uuid4=False,
    )
    validate_optional_organization_reference(
        current_parent,
        "current_parent_organization_unit_reference",
    )
    validate_optional_organization_reference(
        proposed_parent,
        "proposed_parent_organization_unit_reference",
    )
    if current_parent == proposed_parent:
        raise ValueError("proposed parent must differ from the current parent")
    if current_parent == organization_unit_reference:
        raise ValueError("organization unit cannot be its own current parent")
    if proposed_parent == organization_unit_reference:
        raise ValueError("organization unit cannot be its own proposed parent")
    canonical_date(snapshot["effective_on"])
    validate_digest(snapshot["organization_unit_snapshot_digest"], "organization_unit_snapshot_digest")
    validate_digest(snapshot["hierarchy_snapshot_digest"], "hierarchy_snapshot_digest")
    validate_reference(requester_reference, "actor", "requester_reference", require_uuid4=True)
    validate_reference(reviewer_reference, "actor", "reviewer_reference", require_uuid4=True)
    if requester_reference == reviewer_reference:
        raise ValueError("reviewer_reference must identify a different accountable actor")
    validate_code(purpose_code, "purpose_code")
    if purpose_code != purpose_code_required:
        raise ValueError("purpose_code must remain organization_hierarchy_change_review")
    validate_code(reason_code, "reason_code")
    if reason_code not in allowed_reason_codes:
        raise ValueError("reason_code must use the reviewed hierarchy-change vocabulary")
    validate_issuance_timestamp(snapshot["recorded_at"])
    validate_positive_int(snapshot["evidence_version"], "evidence_version")
    if snapshot["contains_person_identifier"] is not False:
        raise ValueError("hierarchy-change evidence must not contain a person identifier")
    if snapshot["contains_worker_value"] is not False:
        raise ValueError("hierarchy-change evidence must not contain worker values")
    if snapshot["contains_employment_decision"] is not False:
        raise ValueError("hierarchy-change evidence must not contain an employment decision")
    if snapshot["human_review_required"] is not True:
        raise ValueError("human review is mandatory before organization-hierarchy mutation")
    validate_code(review_state, "review_state")
    if review_state != review_state_required:
        raise ValueError("review_state must remain requires_human_review")
    validate_code(scope_verification_state, "scope_verification_state")
    if scope_verification_state != scope_state_required:
        raise ValueError("scope_verification_state must remain requires_authoritative_resolution")
    validate_code(mutation_state, "mutation_state")
    if mutation_state != mutation_state_required:
        raise ValueError("mutation_state must remain not_authorized_to_apply")
    validate_code(decision_authority, "decision_authority")
    if decision_authority != decision_authority_required:
        raise ValueError("decision_authority must remain human_review_only")
    if type(snapshot["next_action"]) is not str or snapshot["next_action"] != next_action_required:
        raise ValueError("next_action must remain the governed hierarchy-change instruction")


_PAYLOAD_AUTHORITY = (
    _validate_payload_runtime_types,
    _canonical_date,
    _canonical_timestamp,
)


def _payload_from_snapshot(
    snapshot: dict[str, object],
    *,
    _authority: tuple[object, ...] = _PAYLOAD_AUTHORITY,
) -> dict[str, object]:
    """Validate runtime representation and canonicalize only the supplied snapshot."""
    validate_payload_runtime_types, canonical_date, canonical_timestamp = _authority
    validate_payload_runtime_types(snapshot)
    return {
        "contains_employment_decision": snapshot["contains_employment_decision"],
        "contains_person_identifier": snapshot["contains_person_identifier"],
        "contains_worker_value": snapshot["contains_worker_value"],
        "current_parent_organization_unit_reference": snapshot[
            "current_parent_organization_unit_reference"
        ],
        "decision_authority": snapshot["decision_authority"],
        "effective_on": canonical_date(snapshot["effective_on"]),
        "evidence_version": snapshot["evidence_version"],
        "hierarchy_snapshot_digest": snapshot["hierarchy_snapshot_digest"],
        "human_review_required": snapshot["human_review_required"],
        "mutation_state": snapshot["mutation_state"],
        "next_action": snapshot["next_action"],
        "organization_hierarchy_change_reference": snapshot[
            "organization_hierarchy_change_reference"
        ],
        "organization_unit_reference": snapshot["organization_unit_reference"],
        "organization_unit_snapshot_digest": snapshot["organization_unit_snapshot_digest"],
        "proposed_parent_organization_unit_reference": snapshot[
            "proposed_parent_organization_unit_reference"
        ],
        "purpose_code": snapshot["purpose_code"],
        "reason_code": snapshot["reason_code"],
        "recorded_at": canonical_timestamp(snapshot["recorded_at"]),
        "requester_reference": snapshot["requester_reference"],
        "review_state": snapshot["review_state"],
        "reviewer_reference": snapshot["reviewer_reference"],
        "scope_verification_state": snapshot["scope_verification_state"],
        "tenant_record_id": snapshot["tenant_record_id"],
    }


def _payload(packet: OrganizationHierarchyChangeReviewPacket) -> dict[str, object]:
    """Capture and emit one exact runtime-validated export snapshot."""
    return _payload_from_snapshot(_snapshot(packet))


def _canonical_payload_json(
    payload: dict[str, object],
    *,
    _dumps: object = json.dumps,
) -> str:
    """Serialize one already-snapshotted payload deterministically."""
    return _dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _build_packet_runtime() -> tuple[object, object, object]:
    """Build packet methods around private process-local issuance and evidence state."""
    trusted_canonical_payload_json = _canonical_payload_json
    trusted_getattribute = object.__getattribute__
    trusted_live_reference_binding = _LiveReferenceBinding
    trusted_payload_from_snapshot = _payload_from_snapshot
    trusted_sha256 = sha256
    trusted_snapshot = _snapshot
    trusted_validate_issuance_snapshot = _validate_issuance_snapshot
    trusted_type = type
    trusted_zip = zip
    field_names = (
        "contains_employment_decision",
        "contains_person_identifier",
        "contains_worker_value",
        "current_parent_organization_unit_reference",
        "decision_authority",
        "effective_on",
        "evidence_version",
        "hierarchy_snapshot_digest",
        "human_review_required",
        "mutation_state",
        "next_action",
        "organization_hierarchy_change_reference",
        "organization_unit_reference",
        "organization_unit_snapshot_digest",
        "proposed_parent_organization_unit_reference",
        "purpose_code",
        "reason_code",
        "recorded_at",
        "requester_reference",
        "review_state",
        "reviewer_reference",
        "scope_verification_state",
        "tenant_record_id",
    )
    registry_lock = RLock()
    creation_digests: WeakKeyDictionary[object, str] = WeakKeyDictionary()
    creation_payload_jsons: WeakKeyDictionary[object, str] = WeakKeyDictionary()
    creation_states: WeakKeyDictionary[object, tuple[object, ...]] = WeakKeyDictionary()
    issuance_in_progress: WeakSet[object] = WeakSet()
    live_reference_bindings: WeakValueDictionary[
        tuple[str, str], _LiveReferenceBinding
    ] = WeakValueDictionary()
    packet_bindings: WeakKeyDictionary[object, _LiveReferenceBinding] = WeakKeyDictionary()

    def digest_text(value: str) -> str:
        """Hash canonical UTF-8 evidence with the import-time SHA-256 implementation."""
        return trusted_sha256(value.encode("utf-8")).hexdigest()

    def capture_state(packet: OrganizationHierarchyChangeReviewPacket) -> tuple[object, ...]:
        """Capture direct slot values without selecting a mutable module export helper."""
        return tuple(trusted_getattribute(packet, name) for name in field_names)

    def state_matches_issuance(
        current_state: tuple[object, ...],
        issuance_state: tuple[object, ...],
    ) -> bool:
        """Compare exact built-in issuance values without invoking subtype behavior."""
        for current_value, issuance_value in trusted_zip(current_state, issuance_state, strict=True):
            if (
                trusted_type(current_value) is not trusted_type(issuance_value)
                or current_value != issuance_value
            ):
                return False
        return True

    def post_init(self: OrganizationHierarchyChangeReviewPacket) -> None:
        """Validate and seal one creation snapshot; reject all reissuance of this object."""
        with registry_lock:
            if self in creation_digests or self in issuance_in_progress:
                raise ValueError("organization hierarchy-change packet may be issued only once")
            issuance_in_progress.add(self)
        try:
            snapshot = trusted_snapshot(self)
            trusted_validate_issuance_snapshot(snapshot)
            payload_json = trusted_canonical_payload_json(trusted_payload_from_snapshot(snapshot))
            creation_digest = digest_text(payload_json)
            issuance_state = tuple(snapshot[name] for name in field_names)
            live_key = (
                snapshot["tenant_record_id"],
                snapshot["organization_hierarchy_change_reference"],
            )
            with registry_lock:
                binding = live_reference_bindings.get(live_key)
                if binding is None:
                    binding = trusted_live_reference_binding(creation_digest)
                    live_reference_bindings[live_key] = binding
                elif binding.evidence_digest != creation_digest:
                    raise ValueError(
                        "organization_hierarchy_change_reference is already bound to different live evidence"
                    )
                creation_digests[self] = creation_digest
                creation_payload_jsons[self] = payload_json
                creation_states[self] = issuance_state
                packet_bindings[self] = binding
        finally:
            with registry_lock:
                issuance_in_progress.discard(self)

    def canonical_json(self: OrganizationHierarchyChangeReviewPacket) -> str:
        """Return issued canonical evidence only while one direct export snapshot still matches."""
        current_state = capture_state(self)
        with registry_lock:
            creation_digest = creation_digests.get(self)
            payload_json = creation_payload_jsons.get(self)
            issuance_state = creation_states.get(self)
        if (
            creation_digest is None
            or payload_json is None
            or issuance_state is None
            or not state_matches_issuance(current_state, issuance_state)
            or digest_text(payload_json) != creation_digest
        ):
            raise ValueError("organization hierarchy-change evidence changed after issuance")
        return payload_json

    def sha256_digest(self: OrganizationHierarchyChangeReviewPacket) -> str:
        """Return SHA-256 over the exact verified canonical UTF-8 evidence."""
        return digest_text(canonical_json(self))

    return post_init, canonical_json, sha256_digest


_PACKET_POST_INIT, _PACKET_CANONICAL_JSON, _PACKET_SHA256_DIGEST = _build_packet_runtime()


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

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Reject caller-defined packet classes before they can replace validation hooks."""
        raise TypeError(
            "OrganizationHierarchyChangeReviewPacket does not support caller-defined subclasses"
        )

    def __repr__(self) -> str:
        """Return a representation that never emits hierarchy correlations."""
        return "OrganizationHierarchyChangeReviewPacket(<redacted>)"

    __post_init__ = _PACKET_POST_INIT
    canonical_json = _PACKET_CANONICAL_JSON
    sha256_digest = _PACKET_SHA256_DIGEST


del _PACKET_POST_INIT, _PACKET_CANONICAL_JSON, _PACKET_SHA256_DIGEST, _build_packet_runtime
