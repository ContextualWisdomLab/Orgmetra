"""Governed, PII-minimized candidate-evidence intake correlation.

The contract binds candidate evidence intake to an authoritative candidate, requisition,
Job, job requirements, evidence-set identity, handling/retention policy, and accountable
actor. It carries no raw candidate evidence values; UUID-backed opaque references remain
sensitive correlating metadata and are redacted from the ordinary object representation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import re
from uuid import UUID

_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]{1,31}:[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$"
)
_PURPOSE_CODE = "candidate_evidence_intake"
_REVIEW_STATE = "requires_human_review"
_ALLOWED_REASON_CODES = frozenset({"requisition_candidate_review"})
_NEXT_ACTION = (
    "Re-resolve every packet reference within tenant_record_id through its authoritative "
    "boundary; verify candidate, requisition, and Job correlation; then verify job relevance, "
    "source provenance, permitted handling, retention, and evidence completeness before "
    "requesting authoritative evidence sealing and accountable human review."
)


def _validate_operational_uuid(value: str, field_name: str) -> None:
    """Require exact canonical non-sentinel UUID text owned by the authoritative HRIS."""
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
    """Require exact text with the expected namespace and opaque UUIDv4 suffix."""
    message = f"{field_name} must be an opaque {prefix}: reference"
    if (
        type(value) is not str
        or len(value) > 160
        or not _REFERENCE_PATTERN.fullmatch(value)
        or not value.startswith(f"{prefix}:")
    ):
        raise ValueError(message)
    suffix = value.split(":", 1)[1]
    try:
        parsed = UUID(suffix)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(message) from exc
    if str(parsed) != suffix or parsed.version != 4 or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(message)


def _validate_digest(value: str, field_name: str) -> None:
    """Require lowercase SHA-256 hexadecimal evidence."""
    if type(value) is not str or not _DIGEST_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _freeze_timestamp(value: datetime) -> datetime:
    """Detach caller-controlled timezone behavior and store one immutable UTC instant."""
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError("collected_at must be an exact timezone-aware datetime")
    try:
        offset = value.utcoffset()
    except Exception as exc:  # noqa: BLE001 - normalize provider behavior at trust boundary.
        raise ValueError("collected_at must be an exact timezone-aware datetime") from exc
    if type(offset) is not timedelta:
        raise ValueError("collected_at must be an exact timezone-aware datetime")
    return (value.replace(tzinfo=None) - offset).replace(tzinfo=timezone.utc)


def _canonical_timestamp(value: datetime) -> str:
    """Render only a previously detached built-in UTC instant as RFC 3339 text."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError("collected_at must be an exact timezone-aware datetime")
    return value.isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True, repr=False)
class CandidateEvidenceIntakePacket:
    """Immutable reference-only candidate-evidence intake awaiting human review."""

    tenant_record_id: str
    intake_reference: str
    candidate_profile_reference: str
    requisition_reference: str
    job_profile_reference: str
    job_requirements_reference: str
    job_requirements_digest: str
    evidence_set_reference: str
    evidence_set_digest: str
    source_provenance_reference: str
    source_provenance_digest: str
    handling_policy_reference: str
    handling_policy_digest: str
    retention_policy_reference: str
    retention_policy_digest: str
    actor_reference: str
    evidence_item_count: int
    purpose_code: str
    reason_code: str
    collected_at: datetime
    human_confirmation_required: bool = True
    review_state: str = _REVIEW_STATE
    next_action: str = _NEXT_ACTION
    evidence_version: int = 1

    def __repr__(self) -> str:
        """Return a representation that never emits candidate correlation evidence."""
        return "CandidateEvidenceIntakePacket(<redacted>)"

    def __post_init__(self) -> None:
        """Fail closed when direct construction drifts from the governed contract."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(self.intake_reference, "candidate_evidence_intake", "intake_reference")
        _validate_reference(self.candidate_profile_reference, "candidate_profile", "candidate_profile_reference")
        _validate_reference(self.requisition_reference, "requisition", "requisition_reference")
        _validate_reference(self.job_profile_reference, "job_profile", "job_profile_reference")
        _validate_reference(self.job_requirements_reference, "job_requirements", "job_requirements_reference")
        _validate_digest(self.job_requirements_digest, "job_requirements_digest")
        _validate_reference(self.evidence_set_reference, "evidence_set", "evidence_set_reference")
        _validate_digest(self.evidence_set_digest, "evidence_set_digest")
        _validate_reference(self.source_provenance_reference, "source_provenance", "source_provenance_reference")
        _validate_digest(self.source_provenance_digest, "source_provenance_digest")
        _validate_reference(self.handling_policy_reference, "handling_policy", "handling_policy_reference")
        _validate_digest(self.handling_policy_digest, "handling_policy_digest")
        _validate_reference(self.retention_policy_reference, "retention_policy", "retention_policy_reference")
        _validate_digest(self.retention_policy_digest, "retention_policy_digest")
        _validate_reference(self.actor_reference, "actor", "actor_reference")
        if type(self.evidence_item_count) is not int or not 1 <= self.evidence_item_count <= 100:
            raise ValueError("evidence_item_count must be an integer from 1 through 100")
        _validate_code(self.purpose_code, "purpose_code")
        if self.purpose_code != _PURPOSE_CODE:
            raise ValueError("purpose_code must remain candidate_evidence_intake")
        _validate_code(self.reason_code, "reason_code")
        if self.reason_code not in _ALLOWED_REASON_CODES:
            raise ValueError("reason_code must use a reviewed non-sensitive candidate-evidence reason")
        object.__setattr__(self, "collected_at", _freeze_timestamp(self.collected_at))
        if type(self.evidence_version) is not int or not 1 <= self.evidence_version <= 2_147_483_647:
            raise ValueError("evidence_version must be an integer from 1 through 2147483647")
        if self.human_confirmation_required is not True:
            raise ValueError("human confirmation is mandatory before sealing candidate evidence")
        if type(self.review_state) is not str or self.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain requires_human_review")
        if type(self.next_action) is not str or self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed candidate-evidence instruction")

    def canonical_json(self) -> str:
        """Return deterministic canonical JSON for immutable audit correlation."""
        payload = {
            "actor_reference": self.actor_reference,
            "candidate_profile_reference": self.candidate_profile_reference,
            "collected_at": _canonical_timestamp(self.collected_at),
            "evidence_item_count": self.evidence_item_count,
            "evidence_set_digest": self.evidence_set_digest,
            "evidence_set_reference": self.evidence_set_reference,
            "evidence_version": self.evidence_version,
            "handling_policy_digest": self.handling_policy_digest,
            "handling_policy_reference": self.handling_policy_reference,
            "human_confirmation_required": self.human_confirmation_required,
            "intake_reference": self.intake_reference,
            "job_profile_reference": self.job_profile_reference,
            "job_requirements_digest": self.job_requirements_digest,
            "job_requirements_reference": self.job_requirements_reference,
            "next_action": self.next_action,
            "purpose_code": self.purpose_code,
            "reason_code": self.reason_code,
            "requisition_reference": self.requisition_reference,
            "retention_policy_digest": self.retention_policy_digest,
            "retention_policy_reference": self.retention_policy_reference,
            "review_state": self.review_state,
            "source_provenance_digest": self.source_provenance_digest,
            "source_provenance_reference": self.source_provenance_reference,
            "tenant_record_id": self.tenant_record_id,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical UTF-8 intake packet."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_candidate_evidence_intake_packet(
    *,
    tenant_record_id: str,
    intake_reference: str,
    candidate_profile_reference: str,
    requisition_reference: str,
    job_profile_reference: str,
    job_requirements_reference: str,
    job_requirements_digest: str,
    evidence_set_reference: str,
    evidence_set_digest: str,
    source_provenance_reference: str,
    source_provenance_digest: str,
    handling_policy_reference: str,
    handling_policy_digest: str,
    retention_policy_reference: str,
    retention_policy_digest: str,
    actor_reference: str,
    evidence_item_count: int,
    purpose_code: str,
    reason_code: str,
    collected_at: datetime,
    evidence_version: int = 1,
) -> CandidateEvidenceIntakePacket:
    """Build a reference-only candidate-evidence packet pending accountable review."""
    return CandidateEvidenceIntakePacket(
        tenant_record_id=tenant_record_id,
        intake_reference=intake_reference,
        candidate_profile_reference=candidate_profile_reference,
        requisition_reference=requisition_reference,
        job_profile_reference=job_profile_reference,
        job_requirements_reference=job_requirements_reference,
        job_requirements_digest=job_requirements_digest,
        evidence_set_reference=evidence_set_reference,
        evidence_set_digest=evidence_set_digest,
        source_provenance_reference=source_provenance_reference,
        source_provenance_digest=source_provenance_digest,
        handling_policy_reference=handling_policy_reference,
        handling_policy_digest=handling_policy_digest,
        retention_policy_reference=retention_policy_reference,
        retention_policy_digest=retention_policy_digest,
        actor_reference=actor_reference,
        evidence_item_count=evidence_item_count,
        purpose_code=purpose_code,
        reason_code=reason_code,
        collected_at=collected_at,
        evidence_version=evidence_version,
    )
