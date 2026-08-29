"""Value-minimized HR data-rights request evidence.

The packet records request-intake provenance only. It does not determine legal or
policy eligibility and never authorizes disclosure, correction, deletion,
restriction, export, or an employment action. Downstream fulfillment must
re-enter the authoritative identity, purpose, policy, retention/legal-hold,
export, mutation, and immutable audit/outbox boundaries.
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
from weakref import ReferenceType, WeakKeyDictionary, ref

_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_OPAQUE_REFERENCE_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]{1,31}:[A-Za-z0-9](?:[A-Za-z0-9._~-]{0,126}[A-Za-z0-9])?$"
)
_ALLOWED_REQUESTER_ROLES = frozenset({"data_subject", "authorized_representative"})
_ALLOWED_REQUEST_ACTIONS = frozenset(
    {"access_copy", "correct_record", "delete_record", "restrict_processing"}
)
_ALLOWED_SOURCE_CHANNELS = frozenset({"self_service", "hr_service_desk", "privacy_office"})
_PURPOSE_CODE = "hr_data_rights_request_intake"
_REQUEST_STATE = "request_recorded"
_ELIGIBILITY_STATE = "requires_authoritative_policy_review"
_DISCLOSURE_STATE = "not_authorized_to_disclose"
_MUTATION_STATE = "not_authorized_to_modify_hr_data"
_NEXT_ACTION = (
    "Before fulfillment, re-resolve the exact tenant, Person, requester identity and authority, "
    "applicable policy or jurisdiction, retention and legal-hold state, export scope, and any "
    "required human review; then perform disclosure or HR mutation only through the separate "
    "authoritative purpose-bound authorization and immutable audit/outbox boundary."
)
_ISSUANCE_LOCK = RLock()
_ISSUANCE_DIGESTS: WeakKeyDictionary[HrDataRightsRequestPacket, str]
_LIVE_REQUEST_EVIDENCE: dict[
    tuple[str, str], dict[ReferenceType[HrDataRightsRequestPacket], str]
]


def _validate_operational_uuid(value: str, field_name: str) -> None:
    """Require exact canonical non-sentinel UUID text without inventing a UUID version."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be canonical UUID text")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{field_name} must be canonical UUID text") from exc
    if str(parsed) != value or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(f"{field_name} must be a canonical operational UUID")


def _validate_packet_reference(value: str, prefix: str, field_name: str) -> None:
    """Require an exact packet-owned opaque UUIDv4 reference."""
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


def _validate_opaque_reference(value: str, prefix: str, field_name: str) -> None:
    """Require exact bounded namespaced opaque text without imposing foreign identifier syntax."""
    if (
        type(value) is not str
        or len(value) > 160
        or not _OPAQUE_REFERENCE_PATTERN.fullmatch(value)
        or not value.startswith(f"{prefix}:")
    ):
        raise ValueError(f"{field_name} must be a bounded opaque {prefix}: reference")


def _validate_digest(value: str, field_name: str) -> None:
    """Require exact lowercase SHA-256 evidence text."""
    if type(value) is not str or _DIGEST_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _validate_code(value: str, field_name: str) -> None:
    """Require exact bounded descriptive two-or-more-word lower snake_case text."""
    if type(value) is not str or len(value) > 64 or _CODE_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be bounded two-or-more-word lower snake_case")


def _validate_allowed_code(
    value: str,
    field_name: str,
    allowed_values: frozenset[str],
) -> None:
    """Require one reviewed routing code after exact primitive validation."""
    _validate_code(value, field_name)
    if value not in allowed_values:
        raise ValueError(f"{field_name} must use the reviewed request-intake vocabulary")


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


def _payload_digest(payload: dict[str, Any]) -> str:
    """Hash one already-snapshotted canonicalizable payload."""
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _release_live_request_reference(
    request_key: tuple[str, str],
    packet_reference: ReferenceType[HrDataRightsRequestPacket],
) -> None:
    """Forget a dead packet without retaining used request identifiers indefinitely."""
    with _ISSUANCE_LOCK:
        live_evidence = _LIVE_REQUEST_EVIDENCE[request_key]
        live_evidence.pop(packet_reference, None)
        if not live_evidence:
            _LIVE_REQUEST_EVIDENCE.pop(request_key, None)


@dataclass(frozen=True, slots=True, weakref_slot=True, repr=False, eq=False)
class HrDataRightsRequestPacket:
    """Immutable, value-minimized intake evidence for one HR data-rights request."""

    tenant_record_id: str
    data_rights_request_reference: str
    person_record_reference: str
    requester_actor_reference: str
    requester_identity_evidence_digest: str
    submission_evidence_digest: str
    applicable_policy_reference: str
    applicable_policy_digest: str
    requester_role_code: str
    requested_action_code: str
    source_channel_code: str
    submitted_at: datetime
    recorded_at: datetime
    evidence_version: int = 1
    purpose_code: str = _PURPOSE_CODE
    contains_hr_data: bool = False
    contains_credentials: bool = False
    human_review_required: bool = True
    request_state: str = _REQUEST_STATE
    eligibility_state: str = _ELIGIBILITY_STATE
    disclosure_state: str = _DISCLOSURE_STATE
    mutation_state: str = _MUTATION_STATE
    next_action: str = _NEXT_ACTION

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Keep governed request behavior final so subclasses cannot override exports."""
        raise TypeError("HrDataRightsRequestPacket is final")

    def __post_init__(self) -> None:
        """Validate fields and reject conflicting live evidence for one request identity."""
        self._validate()
        payload = self._payload()
        evidence_digest = _payload_digest(payload)
        request_key = (self.tenant_record_id, self.data_rights_request_reference)
        with _ISSUANCE_LOCK:
            live_evidence = _LIVE_REQUEST_EVIDENCE.get(request_key)
            if live_evidence is not None:
                for live_digest in live_evidence.values():
                    if not hmac.compare_digest(live_digest, evidence_digest):
                        raise ValueError(
                            "data-rights request reference is already live with different evidence"
                        )
            else:
                live_evidence = {}
                _LIVE_REQUEST_EVIDENCE[request_key] = live_evidence
            _ISSUANCE_DIGESTS[self] = evidence_digest
            packet_reference = ref(
                self,
                lambda dead_reference, key=request_key: _release_live_request_reference(
                    key, dead_reference
                ),
            )
            live_evidence[packet_reference] = evidence_digest

    def __repr__(self) -> str:
        """Avoid disclosing tenant, Person, actor, policy, or evidence correlations in logs."""
        return "HrDataRightsRequestPacket(<redacted>)"

    def _validate(self) -> None:
        """Fail closed when live fields drift from the request-only privacy contract."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_packet_reference(
            self.data_rights_request_reference,
            "data_rights_request",
            "data_rights_request_reference",
        )
        _validate_opaque_reference(
            self.person_record_reference,
            "person_record",
            "person_record_reference",
        )
        _validate_packet_reference(
            self.requester_actor_reference,
            "actor",
            "requester_actor_reference",
        )
        _validate_digest(
            self.requester_identity_evidence_digest,
            "requester_identity_evidence_digest",
        )
        _validate_digest(self.submission_evidence_digest, "submission_evidence_digest")
        _validate_opaque_reference(
            self.applicable_policy_reference,
            "data_rights_policy",
            "applicable_policy_reference",
        )
        _validate_digest(self.applicable_policy_digest, "applicable_policy_digest")
        _validate_allowed_code(
            self.requester_role_code,
            "requester_role_code",
            _ALLOWED_REQUESTER_ROLES,
        )
        _validate_allowed_code(
            self.requested_action_code,
            "requested_action_code",
            _ALLOWED_REQUEST_ACTIONS,
        )
        _validate_allowed_code(
            self.source_channel_code,
            "source_channel_code",
            _ALLOWED_SOURCE_CHANNELS,
        )
        _validate_utc_timestamp(self.submitted_at, "submitted_at")
        _validate_utc_timestamp(self.recorded_at, "recorded_at")
        if self.recorded_at < self.submitted_at:
            raise ValueError("recorded_at must be at or after submitted_at")
        _validate_evidence_version(self.evidence_version)
        _require_fixed_text(self.purpose_code, _PURPOSE_CODE, "purpose_code")
        _require_fixed_bool(self.contains_hr_data, False, "contains_hr_data")
        _require_fixed_bool(self.contains_credentials, False, "contains_credentials")
        _require_fixed_bool(self.human_review_required, True, "human_review_required")
        _require_fixed_text(self.request_state, _REQUEST_STATE, "request_state")
        _require_fixed_text(self.eligibility_state, _ELIGIBILITY_STATE, "eligibility_state")
        _require_fixed_text(self.disclosure_state, _DISCLOSURE_STATE, "disclosure_state")
        _require_fixed_text(self.mutation_state, _MUTATION_STATE, "mutation_state")
        _require_fixed_text(self.next_action, _NEXT_ACTION, "next_action")

    def _payload(self) -> dict[str, Any]:
        """Snapshot the exact value-minimized fields in canonicalizable form."""
        return {
            "applicable_policy_digest": self.applicable_policy_digest,
            "applicable_policy_reference": self.applicable_policy_reference,
            "contains_credentials": self.contains_credentials,
            "contains_hr_data": self.contains_hr_data,
            "data_rights_request_reference": self.data_rights_request_reference,
            "disclosure_state": self.disclosure_state,
            "eligibility_state": self.eligibility_state,
            "evidence_version": self.evidence_version,
            "human_review_required": self.human_review_required,
            "mutation_state": self.mutation_state,
            "next_action": self.next_action,
            "person_record_reference": self.person_record_reference,
            "purpose_code": self.purpose_code,
            "recorded_at": self.recorded_at.isoformat().replace("+00:00", "Z"),
            "request_state": self.request_state,
            "requested_action_code": self.requested_action_code,
            "requester_actor_reference": self.requester_actor_reference,
            "requester_identity_evidence_digest": self.requester_identity_evidence_digest,
            "requester_role_code": self.requester_role_code,
            "source_channel_code": self.source_channel_code,
            "submission_evidence_digest": self.submission_evidence_digest,
            "submitted_at": self.submitted_at.isoformat().replace("+00:00", "Z"),
            "tenant_record_id": self.tenant_record_id,
        }

    def _verified_payload(self) -> dict[str, Any]:
        """Validate once, verify the same snapshot, and return exactly that checked payload."""
        self._validate()
        payload = self._payload()
        actual_digest = _payload_digest(payload)
        with _ISSUANCE_LOCK:
            expected_digest = _ISSUANCE_DIGESTS.get(self)
        if expected_digest is None:
            raise ValueError("data-rights request evidence is not registered as constructed")
        if not hmac.compare_digest(expected_digest, actual_digest):
            raise ValueError("data-rights request evidence changed after construction")
        return payload

    def canonical_document(self) -> dict[str, Any]:
        """Return one verified value-minimized document for immutable audit correlation."""
        return self._verified_payload()

    def canonical_json(self) -> str:
        """Return deterministic JSON over the exact verified payload snapshot."""
        payload = self._verified_payload()
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact verified canonical UTF-8 evidence."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


_ISSUANCE_DIGESTS = WeakKeyDictionary()
_LIVE_REQUEST_EVIDENCE = {}


def build_hr_data_rights_request_packet(
    *,
    tenant_record_id: str,
    data_rights_request_reference: str,
    person_record_reference: str,
    requester_actor_reference: str,
    requester_identity_evidence_digest: str,
    submission_evidence_digest: str,
    applicable_policy_reference: str,
    applicable_policy_digest: str,
    requester_role_code: str,
    requested_action_code: str,
    source_channel_code: str,
    submitted_at: datetime,
    recorded_at: datetime,
    evidence_version: int = 1,
) -> HrDataRightsRequestPacket:
    """Build non-authorizing request evidence for authoritative downstream review."""
    return HrDataRightsRequestPacket(
        tenant_record_id=tenant_record_id,
        data_rights_request_reference=data_rights_request_reference,
        person_record_reference=person_record_reference,
        requester_actor_reference=requester_actor_reference,
        requester_identity_evidence_digest=requester_identity_evidence_digest,
        submission_evidence_digest=submission_evidence_digest,
        applicable_policy_reference=applicable_policy_reference,
        applicable_policy_digest=applicable_policy_digest,
        requester_role_code=requester_role_code,
        requested_action_code=requested_action_code,
        source_channel_code=source_channel_code,
        submitted_at=submitted_at,
        recorded_at=recorded_at,
        evidence_version=evidence_version,
    )
