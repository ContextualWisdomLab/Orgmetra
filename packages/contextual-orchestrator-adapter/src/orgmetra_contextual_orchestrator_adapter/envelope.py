"""Governed, value-minimized evidence for Contextual Orchestrator draft output."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import re
import secrets
from typing import ClassVar
from uuid import UUID, uuid4


_CONTEXTUAL_ORCHESTRATOR_REVISION = "e226e1197bdfc890c9d8e5b9b648c78857d7e465"
_PROCESS_SEAL_KEY = secrets.token_bytes(32)
_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")
_MODEL_PATTERN = re.compile(r"[A-Za-z0-9._:/-]{1,128}")
_ALLOWED_DRAFT_USES = frozenset(
    {
        "candidate_evidence_summary_draft",
        "job_analysis_draft",
        "workforce_summary_draft",
    }
)
_ALLOWED_TARGET_PREFIXES = frozenset(
    {
        "candidate",
        "job_analysis",
        "job_profile",
        "person",
        "requisition",
        "workforce_snapshot",
    }
)


def _require_text(value: object, field_name: str) -> str:
    """Return exact built-in non-empty text or fail before caller-defined behavior runs."""
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


def _validate_reference(value: object, field_name: str, allowed_prefixes: frozenset[str]) -> str:
    """Require a bounded namespaced reference with a canonical UUIDv4 suffix."""
    text = _require_text(value, field_name)
    if len(text) > 180 or ":" not in text:
        raise ValueError(f"{field_name} must be a bounded namespaced UUIDv4 reference")
    prefix, suffix = text.split(":", 1)
    if prefix not in allowed_prefixes:
        raise ValueError(f"{field_name} uses an unsupported namespace")
    try:
        parsed = UUID(suffix)
    except (ValueError, AttributeError, TypeError) as error:
        raise ValueError(f"{field_name} must end in a canonical UUIDv4") from error
    if str(parsed) != suffix or parsed.version != 4:
        raise ValueError(f"{field_name} must end in a canonical UUIDv4")
    return text


def _validate_actor_reference(value: object, field_name: str) -> str:
    """Require one opaque tenant-scoped actor correlation with a canonical UUIDv4 suffix."""
    return _validate_reference(value, field_name, frozenset({"actor"}))


def _validate_digest(value: object, field_name: str) -> str:
    """Require one lowercase SHA-256 evidence digest."""
    text = _require_text(value, field_name)
    if _DIGEST_PATTERN.fullmatch(text) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return text


def _validate_model(value: object) -> str:
    """Require one bounded model or orchestration alias without prompt-like whitespace."""
    text = _require_text(value, "requested_model")
    if _MODEL_PATTERN.fullmatch(text) is None:
        raise ValueError("requested_model must be a bounded model identifier")
    return text


def _system_recorded_at() -> datetime:
    """Return the trusted issuance boundary's current built-in UTC instant."""
    return datetime.now(timezone.utc)


def _new_draft_evidence_reference() -> str:
    """Return a fresh opaque correlation for one system-recorded draft-evidence issuance."""
    return f"draft_evidence:{uuid4()}"


def _validate_recorded_at(value: object) -> datetime:
    """Require exact built-in UTC system-recorded time for immutable evidence."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError("recorded_at must be an exact built-in UTC datetime")
    return value


def _canonical_timestamp(value: datetime) -> str:
    """Render the already-governed UTC timestamp in deterministic RFC 3339 form."""
    return value.isoformat().replace("+00:00", "Z")


def _seal(payload_json: str) -> str:
    """Detect accidental in-process changes to one exact issuance payload."""
    return hmac.new(_PROCESS_SEAL_KEY, payload_json.encode("utf-8"), "sha256").hexdigest()


@dataclass(frozen=True, slots=True, repr=False)
class DraftEvidenceEnvelope:
    """Bind model-derived draft provenance while withholding employment-decision authority."""

    tenant_record_id: str
    orchestration_request_reference: str
    evidence_target_reference: str
    requesting_actor_reference: str
    reviewing_actor_reference: str
    draft_use_code: str
    requested_model: str
    input_evidence_digest: str
    response_evidence_digest: str
    provenance_evidence_digest: str
    contextual_orchestrator_revision: str
    api_operation: str
    evidence_version: int
    draft_evidence_reference: str = field(init=False)
    recorded_at: datetime = field(init=False)
    _creation_seal: str = field(init=False, repr=False, compare=False)

    API_CONTRACT_ID: ClassVar[str] = "contextual-orchestrator.openapi.v0.1.0"
    OUTPUT_TRUST_STATE: ClassVar[str] = "untrusted_draft"
    REVIEW_STATE: ClassVar[str] = "requires_human_review"
    DECISION_AUTHORITY_STATE: ClassVar[str] = "not_authorized_for_employment_decision"

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Keep the trust-bearing runtime type final."""
        raise TypeError("DraftEvidenceEnvelope is final")

    def __post_init__(self) -> None:
        """Generate issuance identity/time, validate scope, and snapshot accidental-change evidence."""
        object.__setattr__(self, "draft_evidence_reference", _new_draft_evidence_reference())
        object.__setattr__(self, "recorded_at", _system_recorded_at())
        self._validate_fields()
        object.__setattr__(self, "_creation_seal", _seal(self._canonical_payload_json()))

    def _validate_fields(self) -> None:
        """Fail closed on scope, provenance, actor-separation, and immutable-state evidence."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.orchestration_request_reference,
            "orchestration_request_reference",
            frozenset({"orchestration_request"}),
        )
        _validate_reference(
            self.evidence_target_reference,
            "evidence_target_reference",
            _ALLOWED_TARGET_PREFIXES,
        )
        _validate_reference(
            self.draft_evidence_reference,
            "draft_evidence_reference",
            frozenset({"draft_evidence"}),
        )
        requester = _validate_actor_reference(self.requesting_actor_reference, "requesting_actor_reference")
        reviewer = _validate_actor_reference(self.reviewing_actor_reference, "reviewing_actor_reference")
        if requester == reviewer:
            raise ValueError("reviewing_actor_reference must differ from requesting_actor_reference")
        draft_use = _require_text(self.draft_use_code, "draft_use_code")
        if draft_use not in _ALLOWED_DRAFT_USES:
            raise ValueError("draft_use_code is not an approved non-decision draft use")
        _validate_model(self.requested_model)
        _validate_digest(self.input_evidence_digest, "input_evidence_digest")
        _validate_digest(self.response_evidence_digest, "response_evidence_digest")
        _validate_digest(self.provenance_evidence_digest, "provenance_evidence_digest")
        revision = _require_text(self.contextual_orchestrator_revision, "contextual_orchestrator_revision")
        if revision != _CONTEXTUAL_ORCHESTRATOR_REVISION:
            raise ValueError("contextual_orchestrator_revision must match the reviewed dependency revision")
        operation = _require_text(self.api_operation, "api_operation")
        if operation != "POST /v1/responses":
            raise ValueError("api_operation must use the reviewed Responses API contract")
        if type(self.evidence_version) is not int or not 1 <= self.evidence_version <= 1_000_000:
            raise ValueError("evidence_version must be an exact positive bounded integer")
        _validate_recorded_at(self.recorded_at)

    def _payload(self) -> dict[str, object]:
        """Return the value-minimized canonical evidence document without raw model content."""
        return {
            "api_contract_id": self.API_CONTRACT_ID,
            "api_operation": self.api_operation,
            "contextual_orchestrator_revision": self.contextual_orchestrator_revision,
            "decision_authority_state": self.DECISION_AUTHORITY_STATE,
            "draft_evidence_reference": self.draft_evidence_reference,
            "draft_use_code": self.draft_use_code,
            "evidence_target_reference": self.evidence_target_reference,
            "evidence_version": self.evidence_version,
            "input_evidence_digest": self.input_evidence_digest,
            "orchestration_request_reference": self.orchestration_request_reference,
            "output_trust_state": self.OUTPUT_TRUST_STATE,
            "provenance_evidence_digest": self.provenance_evidence_digest,
            "recorded_at": _canonical_timestamp(self.recorded_at),
            "requested_model": self.requested_model,
            "requesting_actor_reference": self.requesting_actor_reference,
            "response_evidence_digest": self.response_evidence_digest,
            "review_state": self.REVIEW_STATE,
            "reviewing_actor_reference": self.reviewing_actor_reference,
            "tenant_record_id": self.tenant_record_id,
        }

    def _canonical_payload_json(self) -> str:
        """Serialize the live payload deterministically without consulting the creation snapshot."""
        return json.dumps(self._payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def _assert_integrity(self) -> tuple[dict[str, object], str]:
        """Validate and return the exact snapshot whose bytes match the creation-time seal."""
        self._validate_fields()
        payload = self._payload()
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        seal = self._creation_seal
        if type(seal) is not str or not hmac.compare_digest(seal, _seal(payload_json)):
            raise ValueError("draft evidence changed after construction")
        return payload, payload_json

    def canonical_document(self) -> dict[str, object]:
        """Return a detached copy of the exact canonical snapshot that passed integrity validation."""
        payload, _ = self._assert_integrity()
        return dict(payload)

    def canonical_json(self) -> str:
        """Return the exact deterministic canonical bytes that passed integrity validation."""
        _, payload_json = self._assert_integrity()
        return payload_json

    def evidence_digest(self) -> str:
        """Return the SHA-256 digest of the exact canonical evidence bytes."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        """Avoid leaking tenant, actor, target, model, or evidence correlation into logs."""
        return "DraftEvidenceEnvelope(<redacted>)"
