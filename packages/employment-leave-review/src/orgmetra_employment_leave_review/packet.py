"""Governed, value-minimized pre-mutation employment-leave review evidence.

The packet correlates one proposed leave/status transition to authoritative Person and
Employment scope plus reviewed policy, leave-case, continuity, benefits-continuity,
return-to-work, personal-data handling, and retention-policy evidence. The opaque worker
correlation and exact leave dates remain personal data, so the packet is deliberately
purpose-bound rather than falsely labeled PII-free. It excludes direct identifiers,
leave reason narrative, medical or family values, compensation/benefit values,
credentials, and free-form model output. Authoritative eligibility, scope resolution,
approval, HRIS mutation, and downstream execution remain outside this package.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import re
from threading import RLock
from uuid import UUID
from weakref import ref

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]{1,31}:[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$"
)
_PURPOSE_CODE = "employment_leave_review"
_ALLOWED_REASON_CODES = frozenset(
    {
        "policy_entitlement_review",
        "temporary_status_change_review",
        "operational_continuity_review",
        "return_to_work_review",
    }
)
_DECISION_AUTHORITY = "human_review_only"
_REVIEW_STATE = "requires_human_review"
_SCOPE_VERIFICATION_STATE = "requires_authoritative_resolution"
_MUTATION_STATE = "not_authorized_to_apply"
_EXTERNAL_EXECUTION_STATE = "not_authorized_to_execute"
_NEXT_ACTION = (
    "Re-resolve every packet reference within tenant_record_id; specifically re-resolve "
    "requester_reference and reviewer_reference and prove their resolved actor identities "
    "are distinct, prove the Person-to-Employment binding and active Assignment/Job/Position "
    "scope represented by the snapshot, verify the authoritative leave case, applicable "
    "leave policy version, exact personal-data handling/retention policy versions, requested "
    "effective dates, work-continuity, benefits-continuity, and return-to-work provenance "
    "without copying medical/family evidence into this packet, then record accountable human "
    "approval and apply any Employment/Assignment status mutation only through the authoritative "
    "People boundary; downstream actions must use published owner contracts."
)
_ISSUANCE_LOCK = RLock()
_ISSUANCE_DIGESTS: dict[int, tuple[object, str]] = {}


def _validate_operational_uuid(value: str, field_name: str) -> None:
    """Require canonical non-sentinel UUID text owned by the authoritative HRIS."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be canonical UUID text")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{field_name} must be canonical UUID text") from exc
    if str(parsed) != value or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(f"{field_name} must be a canonical operational UUID")


def _validate_reference(value: str, prefix: str, field_name: str) -> None:
    """Require the expected namespace plus a canonical opaque UUIDv4 suffix."""
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
    """Require exact built-in lowercase SHA-256 hexadecimal evidence."""
    if type(value) is not str or not _DIGEST_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _canonical_timestamp(value: datetime) -> str:
    """Render an aware instant as precision-preserving UTC RFC 3339 text."""
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("generated_at must be an exact timezone-aware datetime")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_business_date(value: date, field_name: str) -> None:
    """Require a business date rather than a datetime or textual date."""
    if type(value) is not date:
        raise ValueError(f"{field_name} must be a date")


def _validate_evidence_version(value: int) -> None:
    """Require a bounded positive integer version for high-impact review evidence."""
    if type(value) is not int or value < 1 or value > 2_147_483_647:
        raise ValueError("evidence_version must be an integer from 1 through 2147483647")


def _canonical_json(payload: dict[str, object]) -> str:
    """Serialize one already-snapshotted payload deterministically."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _seal_issuance(packet: object, canonical: str) -> None:
    """Bind one live packet identity exactly once to its creation-time evidence digest."""
    digest = sha256(canonical.encode("utf-8")).hexdigest()
    packet_id = id(packet)

    def release_issuance(_packet_reference: object) -> None:
        """Release the process-local seal as soon as its packet is collected."""
        with _ISSUANCE_LOCK:
            _ISSUANCE_DIGESTS.pop(packet_id, None)

    packet_reference = ref(packet, release_issuance)
    with _ISSUANCE_LOCK:
        if packet_id in _ISSUANCE_DIGESTS:
            raise ValueError("employment leave review evidence integrity check failed")
        _ISSUANCE_DIGESTS[packet_id] = (packet_reference, digest)


def _assert_issuance_integrity(packet: object, canonical: str) -> None:
    """Fail closed when a live or copied packet no longer matches issued evidence."""
    digest = sha256(canonical.encode("utf-8")).hexdigest()
    with _ISSUANCE_LOCK:
        sealed = _ISSUANCE_DIGESTS.get(id(packet))
    if sealed is None:
        raise ValueError("employment leave review evidence integrity check failed")
    if sealed[1] != digest:
        raise ValueError("employment leave review evidence integrity check failed")


@dataclass(frozen=True, slots=True, repr=False, weakref_slot=True)
class EmploymentLeaveReviewPacket:
    """Immutable leave-review evidence that cannot authorize mutation or execution."""

    tenant_record_id: str
    leave_review_reference: str
    person_record_reference: str
    employment_record_reference: str
    active_assignment_snapshot_reference: str
    active_assignment_snapshot_digest: str
    leave_case_reference: str
    leave_case_digest: str
    leave_policy_reference: str
    leave_policy_digest: str
    work_continuity_plan_reference: str
    work_continuity_plan_digest: str
    benefits_continuity_plan_reference: str
    benefits_continuity_plan_digest: str
    return_to_work_plan_reference: str
    return_to_work_plan_digest: str
    handling_policy_reference: str
    handling_policy_digest: str
    retention_policy_reference: str
    retention_policy_digest: str
    requester_reference: str
    reviewer_reference: str
    purpose_code: str
    reason_code: str
    requested_leave_start_on: date
    requested_leave_end_on: date
    generated_at: datetime
    evidence_version: int = 1
    contains_person_pii: bool = True
    contains_medical_or_family_values: bool = False
    contains_compensation_or_benefit_values: bool = False
    contains_free_form_case_narrative: bool = False
    contains_free_form_model_output: bool = False
    human_confirmation_required: bool = True
    decision_authority: str = _DECISION_AUTHORITY
    review_state: str = _REVIEW_STATE
    scope_verification_state: str = _SCOPE_VERIFICATION_STATE
    mutation_state: str = _MUTATION_STATE
    external_execution_state: str = _EXTERNAL_EXECUTION_STATE
    next_action: str = _NEXT_ACTION

    def __repr__(self) -> str:
        """Return a representation that never emits personal-data correlation evidence."""
        return "EmploymentLeaveReviewPacket(<redacted>)"

    def __post_init__(self) -> None:
        """Fail closed when direct construction drifts from the governed contract."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.leave_review_reference,
            "employment_leave_review",
            "leave_review_reference",
        )
        _validate_reference(self.person_record_reference, "person_record", "person_record_reference")
        _validate_reference(
            self.employment_record_reference,
            "employment_record",
            "employment_record_reference",
        )
        _validate_reference(
            self.active_assignment_snapshot_reference,
            "active_assignment_snapshot",
            "active_assignment_snapshot_reference",
        )
        _validate_digest(self.active_assignment_snapshot_digest, "active_assignment_snapshot_digest")
        _validate_reference(self.leave_case_reference, "leave_case", "leave_case_reference")
        _validate_digest(self.leave_case_digest, "leave_case_digest")
        _validate_reference(self.leave_policy_reference, "leave_policy", "leave_policy_reference")
        _validate_digest(self.leave_policy_digest, "leave_policy_digest")
        _validate_reference(
            self.work_continuity_plan_reference,
            "work_continuity_plan",
            "work_continuity_plan_reference",
        )
        _validate_digest(self.work_continuity_plan_digest, "work_continuity_plan_digest")
        _validate_reference(
            self.benefits_continuity_plan_reference,
            "benefits_continuity_plan",
            "benefits_continuity_plan_reference",
        )
        _validate_digest(self.benefits_continuity_plan_digest, "benefits_continuity_plan_digest")
        _validate_reference(
            self.return_to_work_plan_reference,
            "return_to_work_plan",
            "return_to_work_plan_reference",
        )
        _validate_digest(self.return_to_work_plan_digest, "return_to_work_plan_digest")
        _validate_reference(
            self.handling_policy_reference,
            "personal_data_handling_policy",
            "handling_policy_reference",
        )
        _validate_digest(self.handling_policy_digest, "handling_policy_digest")
        _validate_reference(
            self.retention_policy_reference,
            "retention_policy",
            "retention_policy_reference",
        )
        _validate_digest(self.retention_policy_digest, "retention_policy_digest")
        _validate_reference(self.requester_reference, "actor", "requester_reference")
        _validate_reference(self.reviewer_reference, "actor", "reviewer_reference")
        if self.requester_reference == self.reviewer_reference:
            raise ValueError("requester and reviewer must be different actor references")
        if type(self.purpose_code) is not str or self.purpose_code != _PURPOSE_CODE:
            raise ValueError("purpose_code must remain employment_leave_review")
        if type(self.reason_code) is not str or self.reason_code not in _ALLOWED_REASON_CODES:
            raise ValueError("reason_code must be an approved non-sensitive leave-review category")
        _validate_business_date(self.requested_leave_start_on, "requested_leave_start_on")
        _validate_business_date(self.requested_leave_end_on, "requested_leave_end_on")
        if self.requested_leave_end_on < self.requested_leave_start_on:
            raise ValueError("requested_leave_end_on must not precede requested_leave_start_on")
        _canonical_timestamp(self.generated_at)
        _validate_evidence_version(self.evidence_version)
        if self.contains_person_pii is not True:
            raise ValueError(
                "employment leave review packet must acknowledge minimum-necessary personal data"
            )
        if self.contains_medical_or_family_values is not False:
            raise ValueError("employment leave review packet must not contain medical or family values")
        if self.contains_compensation_or_benefit_values is not False:
            raise ValueError(
                "employment leave review packet must not contain compensation or benefit values"
            )
        if self.contains_free_form_case_narrative is not False:
            raise ValueError("employment leave review packet must not contain free-form case narrative")
        if self.contains_free_form_model_output is not False:
            raise ValueError("employment leave review packet must not contain free-form model output")
        if self.human_confirmation_required is not True:
            raise ValueError("human confirmation is mandatory before an employment leave mutation")
        if type(self.decision_authority) is not str or self.decision_authority != _DECISION_AUTHORITY:
            raise ValueError("decision_authority must remain human_review_only")
        if type(self.review_state) is not str or self.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain requires_human_review")
        if type(self.scope_verification_state) is not str or self.scope_verification_state != _SCOPE_VERIFICATION_STATE:
            raise ValueError("scope_verification_state must remain requires_authoritative_resolution")
        if type(self.mutation_state) is not str or self.mutation_state != _MUTATION_STATE:
            raise ValueError("mutation_state must remain not_authorized_to_apply")
        if type(self.external_execution_state) is not str or self.external_execution_state != _EXTERNAL_EXECUTION_STATE:
            raise ValueError("external_execution_state must remain not_authorized_to_execute")
        if type(self.next_action) is not str or self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed employment-leave instruction")
        _seal_issuance(self, _canonical_json(self._canonical_payload()))

    def _canonical_payload(self) -> dict[str, object]:
        """Snapshot every trust-bearing field once for integrity verification and export."""
        return {
            "active_assignment_snapshot_digest": self.active_assignment_snapshot_digest,
            "active_assignment_snapshot_reference": self.active_assignment_snapshot_reference,
            "benefits_continuity_plan_digest": self.benefits_continuity_plan_digest,
            "benefits_continuity_plan_reference": self.benefits_continuity_plan_reference,
            "contains_compensation_or_benefit_values": self.contains_compensation_or_benefit_values,
            "contains_free_form_case_narrative": self.contains_free_form_case_narrative,
            "contains_free_form_model_output": self.contains_free_form_model_output,
            "contains_medical_or_family_values": self.contains_medical_or_family_values,
            "contains_person_pii": self.contains_person_pii,
            "decision_authority": self.decision_authority,
            "employment_record_reference": self.employment_record_reference,
            "evidence_version": self.evidence_version,
            "external_execution_state": self.external_execution_state,
            "generated_at": _canonical_timestamp(self.generated_at),
            "handling_policy_digest": self.handling_policy_digest,
            "handling_policy_reference": self.handling_policy_reference,
            "human_confirmation_required": self.human_confirmation_required,
            "leave_case_digest": self.leave_case_digest,
            "leave_case_reference": self.leave_case_reference,
            "leave_policy_digest": self.leave_policy_digest,
            "leave_policy_reference": self.leave_policy_reference,
            "leave_review_reference": self.leave_review_reference,
            "mutation_state": self.mutation_state,
            "next_action": self.next_action,
            "person_record_reference": self.person_record_reference,
            "purpose_code": self.purpose_code,
            "reason_code": self.reason_code,
            "requested_leave_end_on": self.requested_leave_end_on.isoformat(),
            "requested_leave_start_on": self.requested_leave_start_on.isoformat(),
            "requester_reference": self.requester_reference,
            "retention_policy_digest": self.retention_policy_digest,
            "retention_policy_reference": self.retention_policy_reference,
            "return_to_work_plan_digest": self.return_to_work_plan_digest,
            "return_to_work_plan_reference": self.return_to_work_plan_reference,
            "review_state": self.review_state,
            "reviewer_reference": self.reviewer_reference,
            "scope_verification_state": self.scope_verification_state,
            "tenant_record_id": self.tenant_record_id,
            "work_continuity_plan_digest": self.work_continuity_plan_digest,
            "work_continuity_plan_reference": self.work_continuity_plan_reference,
        }

    def canonical_json(self) -> str:
        """Return creation-bound deterministic canonical JSON for immutable audit correlation."""
        canonical = _canonical_json(self._canonical_payload())
        _assert_issuance_integrity(self, canonical)
        return canonical

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact verified canonical UTF-8 leave-review packet."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_employment_leave_review_packet(
    *,
    tenant_record_id: str,
    leave_review_reference: str,
    person_record_reference: str,
    employment_record_reference: str,
    active_assignment_snapshot_reference: str,
    active_assignment_snapshot_digest: str,
    leave_case_reference: str,
    leave_case_digest: str,
    leave_policy_reference: str,
    leave_policy_digest: str,
    work_continuity_plan_reference: str,
    work_continuity_plan_digest: str,
    benefits_continuity_plan_reference: str,
    benefits_continuity_plan_digest: str,
    return_to_work_plan_reference: str,
    return_to_work_plan_digest: str,
    handling_policy_reference: str,
    handling_policy_digest: str,
    retention_policy_reference: str,
    retention_policy_digest: str,
    requester_reference: str,
    reviewer_reference: str,
    purpose_code: str,
    reason_code: str,
    requested_leave_start_on: date,
    requested_leave_end_on: date,
    generated_at: datetime,
    evidence_version: int = 1,
) -> EmploymentLeaveReviewPacket:
    """Build a value-minimized leave packet pending authoritative human approval."""
    return EmploymentLeaveReviewPacket(
        tenant_record_id=tenant_record_id,
        leave_review_reference=leave_review_reference,
        person_record_reference=person_record_reference,
        employment_record_reference=employment_record_reference,
        active_assignment_snapshot_reference=active_assignment_snapshot_reference,
        active_assignment_snapshot_digest=active_assignment_snapshot_digest,
        leave_case_reference=leave_case_reference,
        leave_case_digest=leave_case_digest,
        leave_policy_reference=leave_policy_reference,
        leave_policy_digest=leave_policy_digest,
        work_continuity_plan_reference=work_continuity_plan_reference,
        work_continuity_plan_digest=work_continuity_plan_digest,
        benefits_continuity_plan_reference=benefits_continuity_plan_reference,
        benefits_continuity_plan_digest=benefits_continuity_plan_digest,
        return_to_work_plan_reference=return_to_work_plan_reference,
        return_to_work_plan_digest=return_to_work_plan_digest,
        handling_policy_reference=handling_policy_reference,
        handling_policy_digest=handling_policy_digest,
        retention_policy_reference=retention_policy_reference,
        retention_policy_digest=retention_policy_digest,
        requester_reference=requester_reference,
        reviewer_reference=reviewer_reference,
        purpose_code=purpose_code,
        reason_code=reason_code,
        requested_leave_start_on=requested_leave_start_on,
        requested_leave_end_on=requested_leave_end_on,
        generated_at=generated_at,
        evidence_version=evidence_version,
    )