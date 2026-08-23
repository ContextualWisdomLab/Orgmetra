"""Value-minimized evidence for one HR document artifact.

This module records document metadata and provenance only. It deliberately does
not carry document bytes, titles, free-form notes, credentials, HR field values,
or employment-decision authority. Durable immutability and authorization belong
to Orgmetra's authoritative document-records and audit/outbox persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import re
from threading import RLock
from typing import Any
from uuid import UUID, uuid4
from weakref import WeakKeyDictionary

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_DOCUMENT_CATEGORIES = frozenset(
    {"employment_contract", "policy_acknowledgement", "qualification_document"}
)
_CLASSIFICATION_CODE = "restricted_hr"
_CONTENT_STORAGE_STATE = "artifact_reference_only"
_DECISION_AUTHORITY_STATE = "not_authorized_for_employment_decision"
_SCHEMA_VERSION = "orgmetra.document_record_evidence.v1"
_ISSUANCE_LOCK = RLock()
_ISSUANCE_DIGESTS: WeakKeyDictionary[DocumentRecordEvidence, str]


def _validate_operational_uuid(value: str, field_name: str) -> None:
    """Require exact canonical non-sentinel UUID text without fixing its version."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be canonical UUID text")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{field_name} must be canonical UUID text") from exc
    if str(parsed) != value or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(f"{field_name} must be a canonical operational UUID")


def _validate_uuid4_reference(value: str, prefix: str, field_name: str) -> None:
    """Require one bounded namespaced UUIDv4 correlation reference."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be an opaque {prefix}: UUIDv4 reference")
    if len(value) > 160 or not value.startswith(f"{prefix}:"):
        raise ValueError(f"{field_name} must be an opaque {prefix}: UUIDv4 reference")
    suffix = value.split(":", 1)[1]
    try:
        parsed = UUID(suffix)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{field_name} must be an opaque {prefix}: UUIDv4 reference") from exc
    if str(parsed) != suffix or parsed.version != 4:
        raise ValueError(f"{field_name} must be an opaque {prefix}: UUIDv4 reference")


def _validate_digest(value: str, field_name: str) -> None:
    """Require exact lowercase SHA-256 evidence text."""
    if type(value) is not str or _DIGEST_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _validate_received_at(value: datetime, recorded_at: datetime) -> None:
    """Require detached UTC event time no later than system-recorded issuance."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError("received_at must be an exact built-in UTC datetime")
    if value > recorded_at:
        raise ValueError("received_at cannot be in the future relative to recorded_at")


def _new_reference() -> str:
    """Return a packet-owned opaque document-record correlation reference."""
    return f"document_record:{uuid4()}"


def _now_utc() -> datetime:
    """Return one built-in UTC system-recorded issuance instant."""
    return datetime.now(timezone.utc)


def _canonical_json(payload: dict[str, Any]) -> str:
    """Serialize one already-snapshotted evidence payload deterministically."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _payload_digest(payload: dict[str, Any]) -> str:
    """Return SHA-256 over one exact canonical payload snapshot."""
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True, weakref_slot=True, repr=False, eq=False)
class DocumentRecordEvidence:
    """Governed metadata evidence for one HR document artifact.

    The object is a transport-neutral evidence value. It is not document content,
    a storage credential, a legal retention decision, or authority for any
    employment action.
    """

    tenant_record_id: str
    person_record_reference: str
    employment_record_reference: str
    uploader_actor_reference: str
    document_category_code: str
    artifact_reference: str
    artifact_digest: str
    source_provenance_digest: str
    retention_policy_reference: str
    retention_policy_digest: str
    received_at: datetime
    document_record_reference: str = field(default_factory=_new_reference, init=False)
    recorded_at: datetime = field(default_factory=_now_utc, init=False)
    classification_code: str = field(default=_CLASSIFICATION_CODE, init=False)
    content_storage_state: str = field(default=_CONTENT_STORAGE_STATE, init=False)
    decision_authority_state: str = field(default=_DECISION_AUTHORITY_STATE, init=False)
    schema_version: str = field(default=_SCHEMA_VERSION, init=False)

    def __post_init__(self) -> None:
        """Validate caller evidence and seal the exact issuance payload outside writable slots."""
        self._validate()
        payload = self._payload()
        with _ISSUANCE_LOCK:
            _ISSUANCE_DIGESTS[self] = _payload_digest(payload)

    def __repr__(self) -> str:
        """Avoid exposing HR document correlations in routine logs."""
        return "DocumentRecordEvidence(<redacted>)"

    def _validate(self) -> None:
        """Fail closed when caller-controlled fields violate the reviewed evidence contract."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_uuid4_reference(
            self.person_record_reference, "person_record", "person_record_reference"
        )
        _validate_uuid4_reference(
            self.employment_record_reference,
            "employment_record",
            "employment_record_reference",
        )
        _validate_uuid4_reference(
            self.uploader_actor_reference, "actor", "uploader_actor_reference"
        )
        if type(self.document_category_code) is not str:
            raise ValueError("document_category_code must use the reviewed vocabulary")
        if self.document_category_code not in _ALLOWED_DOCUMENT_CATEGORIES:
            raise ValueError("document_category_code must use the reviewed vocabulary")
        _validate_uuid4_reference(
            self.artifact_reference, "document_artifact", "artifact_reference"
        )
        _validate_digest(self.artifact_digest, "artifact_digest")
        _validate_digest(self.source_provenance_digest, "source_provenance_digest")
        _validate_uuid4_reference(
            self.retention_policy_reference,
            "retention_policy",
            "retention_policy_reference",
        )
        _validate_digest(self.retention_policy_digest, "retention_policy_digest")
        _validate_received_at(self.received_at, self.recorded_at)

    def _payload(self) -> dict[str, Any]:
        """Snapshot the exact value-minimized evidence fields once."""
        return {
            "artifact_digest": self.artifact_digest,
            "artifact_reference": self.artifact_reference,
            "classification_code": self.classification_code,
            "content_storage_state": self.content_storage_state,
            "decision_authority_state": self.decision_authority_state,
            "document_category_code": self.document_category_code,
            "document_record_reference": self.document_record_reference,
            "employment_record_reference": self.employment_record_reference,
            "person_record_reference": self.person_record_reference,
            "received_at": self.received_at.isoformat().replace("+00:00", "Z"),
            "recorded_at": self.recorded_at.isoformat().replace("+00:00", "Z"),
            "retention_policy_digest": self.retention_policy_digest,
            "retention_policy_reference": self.retention_policy_reference,
            "schema_version": self.schema_version,
            "source_provenance_digest": self.source_provenance_digest,
            "tenant_record_id": self.tenant_record_id,
            "uploader_actor_reference": self.uploader_actor_reference,
        }

    def _verified_payload(self) -> dict[str, Any]:
        """Validate and return the same payload snapshot whose issuance seal was verified."""
        self._validate()
        payload = self._payload()
        actual_digest = _payload_digest(payload)
        with _ISSUANCE_LOCK:
            expected_digest = _ISSUANCE_DIGESTS.get(self, f"missing:{actual_digest}")
        if not hmac.compare_digest(expected_digest, actual_digest):
            raise ValueError("document record evidence changed after construction")
        return payload

    def canonical_document(self) -> dict[str, Any]:
        """Return deterministic, value-minimized document metadata evidence."""
        return self._verified_payload()

    def canonical_json(self) -> str:
        """Return deterministic JSON over the exact verified payload snapshot."""
        return _canonical_json(self._verified_payload())

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact verified canonical JSON bytes."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


_ISSUANCE_DIGESTS = WeakKeyDictionary()


def build_document_record_evidence(
    *,
    tenant_record_id: str,
    person_record_reference: str,
    employment_record_reference: str,
    uploader_actor_reference: str,
    document_category_code: str,
    artifact_reference: str,
    artifact_digest: str,
    source_provenance_digest: str,
    retention_policy_reference: str,
    retention_policy_digest: str,
    received_at: datetime,
) -> DocumentRecordEvidence:
    """Build one non-authorizing HR document metadata evidence value."""
    return DocumentRecordEvidence(
        tenant_record_id=tenant_record_id,
        person_record_reference=person_record_reference,
        employment_record_reference=employment_record_reference,
        uploader_actor_reference=uploader_actor_reference,
        document_category_code=document_category_code,
        artifact_reference=artifact_reference,
        artifact_digest=artifact_digest,
        source_provenance_digest=source_provenance_digest,
        retention_policy_reference=retention_policy_reference,
        retention_policy_digest=retention_policy_digest,
        received_at=received_at,
    )
