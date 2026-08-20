"""Fail-closed Orgmetra binding for TEPP analysis-run request contract v1."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Final
from uuid import UUID

TEPP_PROTECTED_REVISION: Final = "7c29e7c971d7940e1fb3def1ed3aae2d1bc8ad4a"
TEPP_ANALYSIS_RUN_CONTRACT_VERSION: Final = 1
_PURPOSE_CODE: Final = "workforce_validation_analysis"
_TRANSPORT_STATE: Final = "requires_published_tepp_service_contract"
_DECISION_AUTHORITY: Final = "human_scientific_review_only"
_LLM_OUTPUT_AUTHORITY: Final = "untrusted_draft_evidence"
_MAX_UUID_INT: Final = (1 << 128) - 1
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GOVERNED_CODE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_NEXT_ACTION: Final = (
    "Within tenant_record_id, re-resolve validation_study_reference, requested_by_actor_reference, "
    "tepp_workspace_id, and tepp_snapshot_id; prove the workspace and immutable snapshot belong to "
    "the authorized workforce-validation scope; verify snapshot_digest and evidence_version; verify "
    f"TEPP protected revision {TEPP_PROTECTED_REVISION} remains compatible with analysis-run contract "
    "version 1 and that an executable TEPP service contract is actually published before transport; "
    "then record accountable human scientific review of any returned analytical evidence before it can "
    "influence a high-impact employment decision."
)


def _validate_uuid4(value: str, field_name: str) -> None:
    """Require one canonical, non-sentinel UUIDv4 string."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a canonical UUIDv4 string")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as error:
        raise ValueError(f"{field_name} must be a canonical UUIDv4 string") from error
    if str(parsed) != value or parsed.version != 4 or parsed.int in {0, _MAX_UUID_INT}:
        raise ValueError(f"{field_name} must be a canonical non-sentinel UUIDv4 string")


def _validate_reference(value: str, namespace: str, field_name: str) -> None:
    """Require one namespaced opaque UUIDv4 reference owned by Orgmetra."""
    if not isinstance(value, str) or not value.startswith(f"{namespace}:"):
        raise ValueError(f"{field_name} must use the {namespace}:<uuidv4> namespace")
    _validate_uuid4(value.removeprefix(f"{namespace}:"), field_name)


def _validate_digest(value: str, field_name: str) -> None:
    """Require one lowercase SHA-256 evidence digest."""
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")


def _validate_evidence_version(value: int) -> None:
    """Require one bounded positive evidence version."""
    if type(value) is not int or not 1 <= value <= 2_147_483_647:
        raise ValueError("evidence_version must be an integer from 1 through 2147483647")


def _validate_aware_datetime(value: datetime, field_name: str) -> None:
    """Require a datetime with a real UTC offset."""
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be a timezone-aware datetime")


def _canonical_rfc3339(value: datetime) -> str:
    """Render an aware instant as deterministic RFC 3339 UTC text."""
    _validate_aware_datetime(value, "knowledge_cutoff")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _validate_opaque_identifier(value: str, field_name: str, maximum_length: int = 256) -> None:
    """Require a bounded printable opaque identifier with no whitespace or control bytes."""
    if not isinstance(value, str) or not 1 <= len(value) <= maximum_length:
        raise ValueError(f"{field_name} must be a bounded opaque identifier")
    if any(ord(character) < 0x21 or ord(character) > 0x7E for character in value):
        raise ValueError(f"{field_name} must contain only visible ASCII without whitespace")


def _validate_idempotency_key(value: str) -> None:
    """Require a durable-correlation-safe idempotency key stronger than TEPP's nonempty minimum."""
    if not isinstance(value, str) or not 16 <= len(value) <= 128:
        raise ValueError("idempotency_key must contain 16 through 128 visible ASCII characters")
    if any(ord(character) < 0x21 or ord(character) > 0x7E for character in value):
        raise ValueError("idempotency_key must contain 16 through 128 visible ASCII characters")


def _validate_governed_code(value: str, field_name: str) -> None:
    """Require a bounded machine code rather than free-form narrative."""
    if not isinstance(value, str) or _GOVERNED_CODE_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a bounded governed machine code")


@dataclass(frozen=True, slots=True, repr=False)
class TeppAnalysisRequestPacket:
    """Immutable pre-transport evidence for one TEPP analysis-run request.

    The packet intentionally does not perform HTTP. It binds Orgmetra governance
    evidence to TEPP's published Rust wire DTO while keeping foreign service
    availability and authorization authoritative at the host boundary.
    """

    tenant_record_id: str
    validation_study_reference: str
    requested_by_actor_reference: str
    tepp_workspace_id: str
    tepp_snapshot_id: str
    snapshot_digest: str
    idempotency_key: str
    knowledge_cutoff: datetime
    model_contract_version: str
    output_profile: str
    generated_at: datetime
    evidence_version: int = 1
    purpose_code: str = _PURPOSE_CODE
    tepp_contract_version: int = TEPP_ANALYSIS_RUN_CONTRACT_VERSION
    tepp_protected_revision: str = TEPP_PROTECTED_REVISION
    transport_state: str = _TRANSPORT_STATE
    decision_authority: str = _DECISION_AUTHORITY
    llm_output_authority: str = _LLM_OUTPUT_AUTHORITY
    contains_personal_data: bool = True
    contains_direct_identity_values: bool = False
    contains_source_text: bool = False
    contains_credentials: bool = False
    human_confirmation_required: bool = True
    next_action: str = _NEXT_ACTION

    def __repr__(self) -> str:
        """Return a representation that never emits tenant or evidence correlation values."""
        return "TeppAnalysisRequestPacket(<redacted>)"

    def __post_init__(self) -> None:
        """Fail closed when direct construction drifts from the governed boundary."""
        _validate_uuid4(self.tenant_record_id, "tenant_record_id")
        _validate_reference(self.validation_study_reference, "validation_study", "validation_study_reference")
        _validate_reference(self.requested_by_actor_reference, "actor", "requested_by_actor_reference")
        _validate_opaque_identifier(self.tepp_workspace_id, "tepp_workspace_id")
        _validate_opaque_identifier(self.tepp_snapshot_id, "tepp_snapshot_id")
        _validate_digest(self.snapshot_digest, "snapshot_digest")
        _validate_idempotency_key(self.idempotency_key)
        _validate_aware_datetime(self.knowledge_cutoff, "knowledge_cutoff")
        _validate_governed_code(self.model_contract_version, "model_contract_version")
        _validate_governed_code(self.output_profile, "output_profile")
        _validate_aware_datetime(self.generated_at, "generated_at")
        _validate_evidence_version(self.evidence_version)
        if self.purpose_code != _PURPOSE_CODE:
            raise ValueError(f"purpose_code must remain {_PURPOSE_CODE}")
        if self.tepp_contract_version != TEPP_ANALYSIS_RUN_CONTRACT_VERSION:
            raise ValueError("tepp_contract_version must remain 1")
        if self.tepp_protected_revision != TEPP_PROTECTED_REVISION:
            raise ValueError("tepp_protected_revision must remain pinned to the reviewed protected revision")
        if self.transport_state != _TRANSPORT_STATE:
            raise ValueError(f"transport_state must remain {_TRANSPORT_STATE}")
        if self.decision_authority != _DECISION_AUTHORITY:
            raise ValueError(f"decision_authority must remain {_DECISION_AUTHORITY}")
        if self.llm_output_authority != _LLM_OUTPUT_AUTHORITY:
            raise ValueError(f"llm_output_authority must remain {_LLM_OUTPUT_AUTHORITY}")
        if self.contains_personal_data is not True:
            raise ValueError("contains_personal_data must remain true because governed correlations are linkable")
        for field_name in ("contains_direct_identity_values", "contains_source_text", "contains_credentials"):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain false")
        if self.human_confirmation_required is not True:
            raise ValueError("human_confirmation_required must remain true")
        if self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed TEPP handoff instruction")

    def tepp_request(self) -> dict[str, object]:
        """Return exactly the fields accepted by TEPP `AnalysisRunRequest` v1."""
        return {
            "contract_version": self.tepp_contract_version,
            "idempotency_key": self.idempotency_key,
            "tenant_workspace_id": self.tepp_workspace_id,
            "snapshot_id": self.tepp_snapshot_id,
            "knowledge_cutoff": _canonical_rfc3339(self.knowledge_cutoff),
            "model_contract_version": self.model_contract_version,
            "output_profile": self.output_profile,
        }

    def canonical_tepp_json(self) -> str:
        """Return deterministic JSON suitable for request-digest and retry comparison."""
        return json.dumps(self.tepp_request(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def request_digest(self) -> str:
        """Return SHA-256 over the exact canonical TEPP request body."""
        return hashlib.sha256(self.canonical_tepp_json().encode("utf-8")).hexdigest()

    def is_idempotent_retry_of(self, other: "TeppAnalysisRequestPacket") -> bool:
        """Return whether another packet is the same exact-key TEPP request retry."""
        return (
            isinstance(other, TeppAnalysisRequestPacket)
            and self.idempotency_key == other.idempotency_key
            and self.request_digest() == other.request_digest()
        )

    def idempotency_conflicts_with(self, other: "TeppAnalysisRequestPacket") -> bool:
        """Return whether one key has been rebound to different TEPP request semantics."""
        return (
            isinstance(other, TeppAnalysisRequestPacket)
            and self.idempotency_key == other.idempotency_key
            and self.request_digest() != other.request_digest()
        )

    def governance_evidence(self) -> dict[str, object]:
        """Return value-minimized Orgmetra evidence for durable audit/outbox correlation."""
        return {
            "tenant_record_id": self.tenant_record_id,
            "validation_study_reference": self.validation_study_reference,
            "requested_by_actor_reference": self.requested_by_actor_reference,
            "snapshot_digest": self.snapshot_digest,
            "evidence_version": self.evidence_version,
            "generated_at": _canonical_rfc3339(self.generated_at),
            "purpose_code": self.purpose_code,
            "tepp_contract_version": self.tepp_contract_version,
            "tepp_protected_revision": self.tepp_protected_revision,
            "tepp_request_digest": self.request_digest(),
            "transport_state": self.transport_state,
            "decision_authority": self.decision_authority,
            "llm_output_authority": self.llm_output_authority,
            "contains_personal_data": self.contains_personal_data,
            "contains_direct_identity_values": self.contains_direct_identity_values,
            "human_confirmation_required": self.human_confirmation_required,
        }


def build_tepp_analysis_request_packet(
    *,
    tenant_record_id: str,
    validation_study_reference: str,
    requested_by_actor_reference: str,
    tepp_workspace_id: str,
    tepp_snapshot_id: str,
    snapshot_digest: str,
    idempotency_key: str,
    knowledge_cutoff: datetime,
    model_contract_version: str,
    output_profile: str,
    generated_at: datetime,
    evidence_version: int = 1,
) -> TeppAnalysisRequestPacket:
    """Build one packet without exposing fixed authority or privacy controls as inputs."""
    return TeppAnalysisRequestPacket(
        tenant_record_id=tenant_record_id,
        validation_study_reference=validation_study_reference,
        requested_by_actor_reference=requested_by_actor_reference,
        tepp_workspace_id=tepp_workspace_id,
        tepp_snapshot_id=tepp_snapshot_id,
        snapshot_digest=snapshot_digest,
        idempotency_key=idempotency_key,
        knowledge_cutoff=knowledge_cutoff,
        model_contract_version=model_contract_version,
        output_profile=output_profile,
        generated_at=generated_at,
        evidence_version=evidence_version,
    )
