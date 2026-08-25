"""Governed work-context evidence for performance and validation interpretation.

This boundary records provenance for opportunity-to-perform and other reviewed
work context without persisting performance ratings, manager identity, or raw
HR values. It is evidence for accountable analysis, never authority to change
an individual rating or employment decision.
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
_PURPOSE_CODE = "performance_context_review"
_REASON_CODE = "criterion_context_evidence_review"
_ANALYSIS_USE_STATE = "context_covariate_evidence_only"
_REVIEW_STATE = "requires_human_review"
_DECISION_AUTHORITY = "not_authorized_for_performance_rating"
_EMPLOYMENT_DECISION_AUTHORITY = "not_authorized_for_employment_decision"
_NEXT_ACTION = (
    "Within tenant_record_id, re-resolve the Employment, Job, performance cycle, assignment "
    "and organization memberships through authoritative Orgmetra boundaries; verify the "
    "reviewed business-time window and opportunity-to-perform, work-context, manager-context, "
    "and membership-weight digests; then link the evidence to criterion and validity analysis "
    "only as reviewed context-covariate provenance. Do not adjust an individual performance "
    "rating or employment decision from this packet."
)


class _LiveReferenceBinding:
    """Keep one reviewed digest alive while any idempotent packet instance remains live."""

    __slots__ = ("creation_digest", "__weakref__")

    def __init__(self, creation_digest: str) -> None:
        """Bind one tenant-qualified packet reference to its reviewed creation digest."""
        self.creation_digest = creation_digest


_REGISTRY_LOCK = RLock()
_CREATION_DIGESTS: WeakKeyDictionary[PerformanceContextEvidencePacket, str] = WeakKeyDictionary()
_PACKET_BINDINGS: WeakKeyDictionary[
    PerformanceContextEvidencePacket, _LiveReferenceBinding
] = WeakKeyDictionary()
_LIVE_REFERENCES: WeakValueDictionary[
    tuple[str, str], _LiveReferenceBinding
] = WeakValueDictionary()


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
    """Require one namespaced canonical UUID reference under an ownership-aware rule."""
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


def _validate_reference_tuple(
    value: object,
    prefix: str,
    field_name: str,
) -> None:
    """Require a bounded, deterministic, nonempty tuple of operational references."""
    if type(value) is not tuple or not 1 <= len(value) <= 16:
        raise ValueError(f"{field_name} must contain 1 through 16 references")
    for reference in value:
        _validate_reference(reference, prefix, field_name, require_uuid4=False)
    if value != tuple(sorted(set(value))):
        raise ValueError(f"{field_name} must be sorted and unique")


def _validate_digest(value: object, field_name: str) -> None:
    """Require exact built-in lowercase SHA-256 hexadecimal evidence."""
    if type(value) is not str or not _DIGEST_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _validate_code(value: object, field_name: str) -> None:
    """Require exact bounded lower snake_case governance text."""
    if type(value) is not str or len(value) > 64 or not _CODE_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be bounded lower snake_case governance text")


def _validate_business_date(value: object, field_name: str) -> None:
    """Require an exact built-in date so caller code cannot override chronology."""
    if type(value) is not date:
        raise ValueError(f"{field_name} must be an exact business date")


def _canonical_timestamp(value: object) -> str:
    """Render one exact datetime with a built-in fixed offset as UTC RFC 3339 text."""
    if type(value) is not datetime or type(value.tzinfo) is not _TIMEZONE_TYPE:
        raise ValueError("generated_at must use a built-in fixed-offset timezone")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_positive_int(value: object, field_name: str) -> None:
    """Require one exact positive bounded built-in integer."""
    if type(value) is not int or value < 1 or value > 2_147_483_647:
        raise ValueError(f"{field_name} must be a positive 32-bit integer")


def _payload(packet: PerformanceContextEvidencePacket) -> dict[str, object]:
    """Snapshot all trust-bearing fields once for integrity checks and emission."""
    return {
        "analysis_use_state": packet.analysis_use_state,
        "assignment_record_references": packet.assignment_record_references,
        "contains_hr_values": packet.contains_hr_values,
        "contains_manager_identity": packet.contains_manager_identity,
        "contains_performance_rating": packet.contains_performance_rating,
        "context_effective_from": packet.context_effective_from.isoformat(),
        "context_effective_to": packet.context_effective_to.isoformat(),
        "decision_authority": packet.decision_authority,
        "employment_decision_authority": packet.employment_decision_authority,
        "employment_record_reference": packet.employment_record_reference,
        "evidence_version": packet.evidence_version,
        "generated_at": _canonical_timestamp(packet.generated_at),
        "human_review_required": packet.human_review_required,
        "job_profile_reference": packet.job_profile_reference,
        "manager_context_digest": packet.manager_context_digest,
        "membership_weight_digest": packet.membership_weight_digest,
        "next_action": packet.next_action,
        "opportunity_to_perform_digest": packet.opportunity_to_perform_digest,
        "organization_unit_references": packet.organization_unit_references,
        "performance_context_evidence_reference": packet.performance_context_evidence_reference,
        "performance_cycle_reference": packet.performance_cycle_reference,
        "purpose_code": packet.purpose_code,
        "reason_code": packet.reason_code,
        "requester_reference": packet.requester_reference,
        "review_state": packet.review_state,
        "reviewer_reference": packet.reviewer_reference,
        "tenant_record_id": packet.tenant_record_id,
        "work_context_digest": packet.work_context_digest,
    }


def _canonical_payload_json(payload: dict[str, object]) -> str:
    """Serialize one already-snapshotted payload deterministically."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True, slots=True, repr=False, eq=False, weakref_slot=True)
class PerformanceContextEvidencePacket:
    """Value-minimized reviewed evidence about context surrounding performance outcomes."""

    tenant_record_id: str
    performance_context_evidence_reference: str
    employment_record_reference: str
    job_profile_reference: str
    performance_cycle_reference: str
    assignment_record_references: tuple[str, ...]
    organization_unit_references: tuple[str, ...]
    context_effective_from: date
    context_effective_to: date
    opportunity_to_perform_digest: str
    work_context_digest: str
    manager_context_digest: str
    membership_weight_digest: str
    requester_reference: str
    reviewer_reference: str
    purpose_code: str
    reason_code: str
    generated_at: datetime
    evidence_version: int = 1
    contains_performance_rating: bool = False
    contains_manager_identity: bool = False
    contains_hr_values: bool = False
    human_review_required: bool = True
    analysis_use_state: str = _ANALYSIS_USE_STATE
    review_state: str = _REVIEW_STATE
    decision_authority: str = _DECISION_AUTHORITY
    employment_decision_authority: str = _EMPLOYMENT_DECISION_AUTHORITY
    next_action: str = _NEXT_ACTION

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Keep the governed runtime type final so behavior cannot be overridden."""
        raise TypeError("PerformanceContextEvidencePacket is final")

    def __repr__(self) -> str:
        """Return a representation that never emits worker or context correlation evidence."""
        return "PerformanceContextEvidencePacket(<redacted>)"

    def __post_init__(self) -> None:
        """Validate the contract and bind one live packet reference to its reviewed evidence."""
        _validate_operational_uuid_text(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.performance_context_evidence_reference,
            "performance_context_evidence",
            "performance_context_evidence_reference",
            require_uuid4=True,
        )
        _validate_reference(
            self.employment_record_reference,
            "employment_record",
            "employment_record_reference",
            require_uuid4=False,
        )
        _validate_reference(
            self.job_profile_reference,
            "job_profile",
            "job_profile_reference",
            require_uuid4=False,
        )
        _validate_reference(
            self.performance_cycle_reference,
            "performance_cycle",
            "performance_cycle_reference",
            require_uuid4=False,
        )
        _validate_reference_tuple(
            self.assignment_record_references,
            "assignment_record",
            "assignment_record_references",
        )
        _validate_reference_tuple(
            self.organization_unit_references,
            "organization_unit",
            "organization_unit_references",
        )
        _validate_business_date(self.context_effective_from, "context_effective_from")
        _validate_business_date(self.context_effective_to, "context_effective_to")
        if self.context_effective_to <= self.context_effective_from:
            raise ValueError("context effective interval must be nonempty and half-open")
        _validate_digest(self.opportunity_to_perform_digest, "opportunity_to_perform_digest")
        _validate_digest(self.work_context_digest, "work_context_digest")
        _validate_digest(self.manager_context_digest, "manager_context_digest")
        _validate_digest(self.membership_weight_digest, "membership_weight_digest")
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
            raise ValueError("purpose_code must remain performance_context_review")
        _validate_code(self.reason_code, "reason_code")
        if self.reason_code != _REASON_CODE:
            raise ValueError("reason_code must remain criterion_context_evidence_review")
        _canonical_timestamp(self.generated_at)
        _validate_positive_int(self.evidence_version, "evidence_version")
        if self.contains_performance_rating is not False:
            raise ValueError("context evidence must not contain a performance rating")
        if self.contains_manager_identity is not False:
            raise ValueError("context evidence must not contain manager identity")
        if self.contains_hr_values is not False:
            raise ValueError("context evidence must not contain raw HR values")
        if self.human_review_required is not True:
            raise ValueError("human review is mandatory before context evidence is used")
        _validate_code(self.analysis_use_state, "analysis_use_state")
        if self.analysis_use_state != _ANALYSIS_USE_STATE:
            raise ValueError("analysis_use_state must remain context_covariate_evidence_only")
        _validate_code(self.review_state, "review_state")
        if self.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain requires_human_review")
        _validate_code(self.decision_authority, "decision_authority")
        if self.decision_authority != _DECISION_AUTHORITY:
            raise ValueError("decision_authority must remain not_authorized_for_performance_rating")
        _validate_code(self.employment_decision_authority, "employment_decision_authority")
        if self.employment_decision_authority != _EMPLOYMENT_DECISION_AUTHORITY:
            raise ValueError(
                "employment_decision_authority must remain not_authorized_for_employment_decision"
            )
        if type(self.next_action) is not str or self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed context-evidence instruction")

        payload_json = _canonical_payload_json(_payload(self))
        creation_digest = sha256(payload_json.encode("utf-8")).hexdigest()
        key = (self.tenant_record_id, self.performance_context_evidence_reference)
        with _REGISTRY_LOCK:
            binding = _LIVE_REFERENCES.get(key)
            if binding is not None and binding.creation_digest != creation_digest:
                raise ValueError("performance context evidence reference is bound to different live evidence")
            if binding is None:
                binding = _LiveReferenceBinding(creation_digest)
                _LIVE_REFERENCES[key] = binding
            _CREATION_DIGESTS[self] = creation_digest
            _PACKET_BINDINGS[self] = binding

    def canonical_json(self) -> str:
        """Return one verified deterministic snapshot of the reviewed audit evidence."""
        payload_json = _canonical_payload_json(_payload(self))
        current_digest = sha256(payload_json.encode("utf-8")).hexdigest()
        with _REGISTRY_LOCK:
            creation_digest = _CREATION_DIGESTS.get(self)
        if creation_digest is None:
            raise ValueError(
                "performance context evidence was not issued through the governed constructor"
            )
        if current_digest != creation_digest:
            raise ValueError("performance context evidence changed after issuance")
        return payload_json

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact verified canonical UTF-8 evidence."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_performance_context_evidence(
    *,
    tenant_record_id: str,
    performance_context_evidence_reference: str,
    employment_record_reference: str,
    job_profile_reference: str,
    performance_cycle_reference: str,
    assignment_record_references: tuple[str, ...],
    organization_unit_references: tuple[str, ...],
    context_effective_from: date,
    context_effective_to: date,
    opportunity_to_perform_digest: str,
    work_context_digest: str,
    manager_context_digest: str,
    membership_weight_digest: str,
    requester_reference: str,
    reviewer_reference: str,
    purpose_code: str,
    reason_code: str,
    generated_at: datetime,
    evidence_version: int = 1,
) -> PerformanceContextEvidencePacket:
    """Build reviewed context provenance without granting rating or decision authority."""
    return PerformanceContextEvidencePacket(
        tenant_record_id=tenant_record_id,
        performance_context_evidence_reference=performance_context_evidence_reference,
        employment_record_reference=employment_record_reference,
        job_profile_reference=job_profile_reference,
        performance_cycle_reference=performance_cycle_reference,
        assignment_record_references=assignment_record_references,
        organization_unit_references=organization_unit_references,
        context_effective_from=context_effective_from,
        context_effective_to=context_effective_to,
        opportunity_to_perform_digest=opportunity_to_perform_digest,
        work_context_digest=work_context_digest,
        manager_context_digest=manager_context_digest,
        membership_weight_digest=membership_weight_digest,
        requester_reference=requester_reference,
        reviewer_reference=reviewer_reference,
        purpose_code=purpose_code,
        reason_code=reason_code,
        generated_at=generated_at,
        evidence_version=evidence_version,
    )
