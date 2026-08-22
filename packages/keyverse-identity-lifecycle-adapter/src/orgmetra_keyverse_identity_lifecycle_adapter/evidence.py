"""Governed, non-executing Keyverse identity deprovision review evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from threading import Lock
from uuid import UUID
from weakref import finalize

REVIEWED_KEYVERSE_REVISION = "ce207dfd42975db61c82a5963e206fc1db14ac2b"
REVIEWED_KEYVERSE_OPERATION = "PATCH /scim/v2/Users/{user_id} active=false"
_PURPOSE_CODE = "employment_identity_deprovisioning"
_REQUESTED_ACTION = "deactivate_identity"
_REVIEW_STATE = "requires_human_review"
_SCOPE_STATE = "requires_authoritative_employment_and_identity_resolution"
_EXECUTION_STATE = "not_sent_to_keyverse"
_AUTHORITY_STATE = "not_authorized_to_modify_identity"
_NEXT_ACTION = (
    "Re-resolve current employment and identity binding, then execute only through the "
    "reviewed Keyverse SCIM contract."
)
_REFERENCE_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]*:([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})$"
)
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_MAX_UUID_INT = (1 << 128) - 1
_SEALS: dict[int, str] = {}
_SEAL_LOCK = Lock()


def _validate_reference(field_name: str, value: object, namespace: str) -> None:
    """Require an exact namespaced UUIDv4 correlation reference."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be exact text.")
    match = _REFERENCE_PATTERN.fullmatch(value)
    if match is None or value.partition(":")[0] != namespace:
        raise ValueError(f"{field_name} must be a canonical {namespace}:<UUIDv4> reference.")
    UUID(match.group(1))


def _validate_digest(field_name: str, value: object) -> None:
    """Require one lowercase SHA-256 evidence digest."""
    if type(value) is not str or _DIGEST_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest.")


def _validate_timestamp_shape(field_name: str, value: object) -> None:
    """Require exact built-in UTC timestamp structure without consulting wall-clock time."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError(f"{field_name} must be an exact timezone.utc datetime.")


def _validate_timestamp(field_name: str, value: object) -> None:
    """Require exact UTC issuance time that has already occurred."""
    _validate_timestamp_shape(field_name, value)
    if value > datetime.now(timezone.utc):
        raise ValueError(f"{field_name} must not be in the future.")


def _payload(envelope: "KeyverseIdentityDeprovisionReviewPacket") -> dict[str, object]:
    """Return the complete trust-bearing canonical evidence payload."""
    return {
        "authority_state": _AUTHORITY_STATE,
        "employment_evidence_digest": envelope.employment_evidence_digest,
        "employment_reference": envelope.employment_reference,
        "evidence_version": envelope.evidence_version,
        "execution_state": _EXECUTION_STATE,
        "handoff_reference": envelope.handoff_reference,
        "identity_binding_digest": envelope.identity_binding_digest,
        "identity_binding_reference": envelope.identity_binding_reference,
        "keyverse_operation": REVIEWED_KEYVERSE_OPERATION,
        "keyverse_revision": envelope.keyverse_revision,
        "next_action": _NEXT_ACTION,
        "person_reference": envelope.person_reference,
        "purpose_code": _PURPOSE_CODE,
        "recorded_at": envelope.recorded_at.isoformat().replace("+00:00", "Z"),
        "requested_action": _REQUESTED_ACTION,
        "requester_actor_reference": envelope.requester_actor_reference,
        "review_state": _REVIEW_STATE,
        "scope_state": _SCOPE_STATE,
        "tenant_record_id": str(envelope.tenant_record_id),
    }


def _canonical_json_from_payload(payload: dict[str, object]) -> str:
    """Serialize one already-captured canonical payload deterministically."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _canonical_payload_json(envelope: "KeyverseIdentityDeprovisionReviewPacket") -> str:
    """Capture and serialize the canonical payload deterministically."""
    return _canonical_json_from_payload(_payload(envelope))


@dataclass(frozen=True, slots=True, weakref_slot=True)
class KeyverseIdentityDeprovisionReviewPacket:
    """PII-minimized deprovision review packet that cannot authorize Keyverse mutation."""

    tenant_record_id: UUID
    handoff_reference: str
    person_reference: str
    employment_reference: str
    identity_binding_reference: str
    identity_binding_digest: str
    employment_evidence_digest: str
    requester_actor_reference: str
    keyverse_revision: str
    evidence_version: int
    recorded_at: datetime

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Keep the governed evidence runtime final."""
        raise TypeError("KeyverseIdentityDeprovisionReviewPacket is final.")

    def __post_init__(self) -> None:
        """Validate issuance-time state and seal the exact deprovision review packet."""
        self._validate_fields()
        _validate_timestamp("recorded_at", self.recorded_at)
        digest = sha256(_canonical_payload_json(self).encode("utf-8")).hexdigest()
        object_id = id(self)
        with _SEAL_LOCK:
            _SEALS[object_id] = digest
        finalize(self, _discard_seal, object_id)

    def _validate_fields(self) -> None:
        """Reject ambiguous identity, scope, provenance, actor, or timestamp structure."""
        if type(self.tenant_record_id) is not UUID or self.tenant_record_id.int in (
            0,
            _MAX_UUID_INT,
        ):
            raise ValueError("tenant_record_id must be a non-sentinel UUID.")
        _validate_reference("handoff_reference", self.handoff_reference, "keyverse_deprovision")
        _validate_reference("person_reference", self.person_reference, "person_record")
        _validate_reference("employment_reference", self.employment_reference, "employment_record")
        _validate_reference(
            "identity_binding_reference",
            self.identity_binding_reference,
            "identity_binding",
        )
        _validate_digest("identity_binding_digest", self.identity_binding_digest)
        _validate_digest("employment_evidence_digest", self.employment_evidence_digest)
        _validate_reference(
            "requester_actor_reference",
            self.requester_actor_reference,
            "actor",
        )
        if (
            type(self.keyverse_revision) is not str
            or _REVISION_PATTERN.fullmatch(self.keyverse_revision) is None
        ):
            raise ValueError(
                "keyverse_revision must be a lowercase 40-character Git revision."
            )
        if self.keyverse_revision != REVIEWED_KEYVERSE_REVISION:
            raise ValueError(
                "keyverse_revision must equal the currently reviewed Keyverse revision."
            )
        if (
            type(self.evidence_version) is not int
            or not 1 <= self.evidence_version <= 1_000_000
        ):
            raise ValueError(
                "evidence_version must be an integer from 1 through 1000000."
            )
        _validate_timestamp_shape("recorded_at", self.recorded_at)

    def _assert_integrity(self) -> tuple[dict[str, object], str]:
        """Return the exact verified payload and JSON snapshot or fail closed."""
        self._validate_fields()
        payload = _payload(self)
        canonical_json = _canonical_json_from_payload(payload)
        live_digest = sha256(canonical_json.encode("utf-8")).hexdigest()
        with _SEAL_LOCK:
            issued_digest = _SEALS.get(id(self))
        if issued_digest is None or live_digest != issued_digest:
            raise ValueError(
                "identity deprovision handoff evidence changed after construction."
            )
        return payload, canonical_json

    def canonical_document(self) -> dict[str, object]:
        """Return the exact PII-minimized payload snapshot verified against the issuance seal."""
        payload, _ = self._assert_integrity()
        return payload

    def canonical_json(self) -> str:
        """Return the exact deterministic JSON snapshot verified against the issuance seal."""
        _, canonical_json = self._assert_integrity()
        return canonical_json

    def evidence_digest(self) -> str:
        """Return SHA-256 over the deterministic canonical evidence JSON."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        """Avoid leaking correlation references or evidence digests to routine logs."""
        return "KeyverseIdentityDeprovisionReviewPacket(<redacted>)"


def _discard_seal(object_id: int) -> None:
    """Remove process-local tamper evidence when a packet is collected."""
    with _SEAL_LOCK:
        _SEALS.pop(object_id, None)
