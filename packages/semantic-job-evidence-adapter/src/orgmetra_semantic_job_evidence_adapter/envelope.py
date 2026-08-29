"""Governed, value-minimized Semantic Data Portal ontology evidence for job analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import re
import secrets
from threading import RLock
from typing import ClassVar
from uuid import UUID
from weakref import finalize


_SEMANTIC_DATA_PORTAL_REVISION = "e48aa13c4af7a4875d4b53e6a60b50405c265a2f"
_PROCESS_SEAL_KEY = secrets.token_bytes(32)
_NEW_ISSUANCE_MARKER = object()
_USED_ISSUANCE_MARKER = object()
_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")
_ALLOWED_RESOLUTION_USES = frozenset({"job_analysis_source_evidence"})
_CREATION_SEALS: dict[int, str] = {}
_CREATION_SEALS_LOCK = RLock()


def _discard_creation_seal(envelope_id: int) -> None:
    """Discard the process-local authoritative seal when its envelope is collected."""
    with _CREATION_SEALS_LOCK:
        _CREATION_SEALS.pop(envelope_id, None)


def _register_creation_seal(envelope: object, seal: str) -> None:
    """Bind one live envelope identity to creation evidence outside writable slots."""
    envelope_id = id(envelope)
    with _CREATION_SEALS_LOCK:
        _CREATION_SEALS[envelope_id] = seal
    finalize(envelope, _discard_creation_seal, envelope_id)


def _authoritative_creation_seal(envelope: object) -> str | None:
    """Return process-local creation evidence without trusting packet-owned state."""
    with _CREATION_SEALS_LOCK:
        return _CREATION_SEALS.get(id(envelope))


def _require_text(value: object, field_name: str) -> str:
    """Return exact built-in non-empty text before caller-defined behavior can run."""
    if type(value) is not str or not value:
        raise ValueError(f"{field_name} must be exact non-empty text")
    return value


def _validate_operational_uuid(value: object, field_name: str) -> str:
    """Require one canonical non-sentinel operational UUID string."""
    text = _require_text(value, field_name)
    try:
        parsed = UUID(text)
    except (ValueError, AttributeError, TypeError) as error:
        raise ValueError(f"{field_name} must be a canonical operational UUID") from error
    if str(parsed) != text or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(f"{field_name} must be a canonical non-sentinel operational UUID")
    return text


def _validate_reference(value: object, field_name: str, namespace: str) -> str:
    """Require a bounded namespaced reference with a canonical UUIDv4 suffix."""
    text = _require_text(value, field_name)
    prefix = f"{namespace}:"
    if len(text) > 180 or not text.startswith(prefix):
        raise ValueError(f"{field_name} must be a bounded {namespace}: UUIDv4 reference")
    suffix = text[len(prefix) :]
    try:
        parsed = UUID(suffix)
    except (ValueError, AttributeError, TypeError) as error:
        raise ValueError(f"{field_name} must end in a canonical UUIDv4") from error
    if str(parsed) != suffix or parsed.version != 4:
        raise ValueError(f"{field_name} must end in a canonical UUIDv4")
    return text


def _validate_actor_reference(value: object, field_name: str) -> str:
    """Require opaque actor correlation with a canonical UUIDv4 suffix."""
    return _validate_reference(value, field_name, "actor")


def _validate_digest(value: object, field_name: str) -> str:
    """Require one lowercase SHA-256 evidence digest."""
    text = _require_text(value, field_name)
    if _DIGEST_PATTERN.fullmatch(text) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return text


def _validate_recorded_at(value: object) -> datetime:
    """Require exact built-in UTC system-recorded time for immutable evidence."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError("recorded_at must be an exact built-in UTC datetime")
    return value


def _canonical_timestamp(value: datetime) -> str:
    """Render an already-governed UTC timestamp in deterministic RFC 3339 form."""
    return value.isoformat().replace("+00:00", "Z")


def _seal(payload_json: str) -> str:
    """Bind one in-process issuance to its exact creation-time canonical payload."""
    return hmac.new(_PROCESS_SEAL_KEY, payload_json.encode("utf-8"), "sha256").hexdigest()


@dataclass(frozen=True, slots=True, repr=False, weakref_slot=True)
class SemanticJobEvidenceEnvelope:
    """Bind ontology source provenance without granting Job or employment decision authority."""

    tenant_record_id: str
    job_analysis_reference: str
    ontology_request_reference: str
    requesting_actor_reference: str
    reviewing_actor_reference: str
    resolution_use_code: str
    query_term_digest: str
    response_evidence_digest: str
    source_catalog_digest: str
    semantic_data_portal_revision: str
    api_operation: str
    evidence_version: int
    recorded_at: datetime
    _creation_seal: str | None = field(default=None, repr=False, compare=False)
    _issuance_marker: object = field(default=_NEW_ISSUANCE_MARKER, repr=False, compare=False)

    SOURCE_SYSTEM: ClassVar[str] = "semantic-data-portal"
    SOURCE_TRUST_STATE: ClassVar[str] = "external_source_evidence"
    REVIEW_STATE: ClassVar[str] = "requires_human_review"
    DECISION_AUTHORITY_STATE: ClassVar[str] = "not_authorized_for_job_or_employment_decision"

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Keep the trust-bearing runtime type final."""
        raise TypeError("SemanticJobEvidenceEnvelope is final")

    def __post_init__(self) -> None:
        """Validate the reviewed boundary and seal its exact creation-time evidence."""
        if self._issuance_marker is not _NEW_ISSUANCE_MARKER:
            raise ValueError("semantic job evidence changed after construction")
        if self._creation_seal is not None:
            raise ValueError("semantic job evidence changed after construction")
        self._validate_fields()
        seal = _seal(self._canonical_payload_json())
        object.__setattr__(self, "_creation_seal", seal)
        object.__setattr__(self, "_issuance_marker", _USED_ISSUANCE_MARKER)
        _register_creation_seal(self, seal)

    def _validate_fields(self) -> None:
        """Fail closed on scope, source provenance, actor separation, and reviewed state."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(self.job_analysis_reference, "job_analysis_reference", "job_analysis")
        _validate_reference(self.ontology_request_reference, "ontology_request_reference", "ontology_request")
        requester = _validate_actor_reference(self.requesting_actor_reference, "requesting_actor_reference")
        reviewer = _validate_actor_reference(self.reviewing_actor_reference, "reviewing_actor_reference")
        if requester == reviewer:
            raise ValueError("reviewing_actor_reference must differ from requesting_actor_reference")
        resolution_use = _require_text(self.resolution_use_code, "resolution_use_code")
        if resolution_use not in _ALLOWED_RESOLUTION_USES:
            raise ValueError("resolution_use_code is not an approved source-evidence use")
        _validate_digest(self.query_term_digest, "query_term_digest")
        _validate_digest(self.response_evidence_digest, "response_evidence_digest")
        _validate_digest(self.source_catalog_digest, "source_catalog_digest")
        revision = _require_text(self.semantic_data_portal_revision, "semantic_data_portal_revision")
        if revision != _SEMANTIC_DATA_PORTAL_REVISION:
            raise ValueError("semantic_data_portal_revision must match the reviewed dependency revision")
        operation = _require_text(self.api_operation, "api_operation")
        if operation != "POST /ontology/resolve":
            raise ValueError("api_operation must use the reviewed ontology-resolution contract")
        if type(self.evidence_version) is not int or not 1 <= self.evidence_version <= 1_000_000:
            raise ValueError("evidence_version must be an exact positive bounded integer")
        _validate_recorded_at(self.recorded_at)

    def _payload(self) -> dict[str, object]:
        """Return value-minimized canonical evidence without raw ontology or HR content."""
        return {
            "api_operation": self.api_operation,
            "decision_authority_state": self.DECISION_AUTHORITY_STATE,
            "evidence_version": self.evidence_version,
            "job_analysis_reference": self.job_analysis_reference,
            "ontology_request_reference": self.ontology_request_reference,
            "query_term_digest": self.query_term_digest,
            "recorded_at": _canonical_timestamp(self.recorded_at),
            "requesting_actor_reference": self.requesting_actor_reference,
            "resolution_use_code": self.resolution_use_code,
            "response_evidence_digest": self.response_evidence_digest,
            "review_state": self.REVIEW_STATE,
            "reviewing_actor_reference": self.reviewing_actor_reference,
            "semantic_data_portal_revision": self.semantic_data_portal_revision,
            "source_catalog_digest": self.source_catalog_digest,
            "source_system": self.SOURCE_SYSTEM,
            "source_trust_state": self.SOURCE_TRUST_STATE,
            "tenant_record_id": self.tenant_record_id,
        }

    def _canonical_payload_json(self) -> str:
        """Serialize the live evidence deterministically without consulting its creation seal."""
        return json.dumps(self._payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def _assert_integrity(self) -> tuple[dict[str, object], str]:
        """Return the exact checked snapshot while rejecting post-construction rewriting."""
        self._validate_fields()
        if self._issuance_marker is not _USED_ISSUANCE_MARKER:
            raise ValueError("semantic job evidence changed after construction")
        packet_seal = self._creation_seal
        authoritative_seal = _authoritative_creation_seal(self)
        payload = self._payload()
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        live_seal = _seal(payload_json)
        if (
            type(packet_seal) is not str
            or type(authoritative_seal) is not str
            or not hmac.compare_digest(packet_seal, authoritative_seal)
            or not hmac.compare_digest(live_seal, authoritative_seal)
        ):
            raise ValueError("semantic job evidence changed after construction")
        return payload, payload_json

    def canonical_document(self) -> dict[str, object]:
        """Return the exact canonical document snapshot that passed integrity verification."""
        payload, _ = self._assert_integrity()
        return payload

    def canonical_json(self) -> str:
        """Return the exact deterministic JSON snapshot that passed integrity verification."""
        _, payload_json = self._assert_integrity()
        return payload_json

    def evidence_digest(self) -> str:
        """Return SHA-256 of the exact canonical evidence bytes."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        """Avoid leaking tenant, actors, Job-analysis scope, or source correlation into logs."""
        return "SemanticJobEvidenceEnvelope(<redacted>)"
