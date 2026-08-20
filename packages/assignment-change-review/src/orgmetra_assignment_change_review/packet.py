"""Governed, value-free pre-mutation assignment-change review evidence.

The packet correlates one proposed internal assignment change to authoritative Person,
Employment, current Assignment/Job/Position scope, proposed Job/Position scope, an exact
current-scope snapshot, a reviewed workforce-allocation plan and policy, worker-impact
evidence, and a communication plan. Opaque Person references remain sensitive correlating
metadata. Person PII, compensation values, allocation values, and free-form model output
stay outside this envelope. Final relationship resolution, approval, and mutation remain
at the authoritative Orgmetra HRIS/People boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import re
from uuid import UUID

_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]{1,31}:[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$"
)
_PURPOSE_CODE = "assignment_change_review"
_ALLOWED_REASON_CODES = frozenset(
    {
        "internal_reassignment",
        "workforce_reallocation",
        "temporary_detail",
        "position_reclassification",
        "organizational_realignment",
    }
)
_DECISION_AUTHORITY = "human_review_only"
_REVIEW_STATE = "requires_human_review"
_SCOPE_VERIFICATION_STATE = "requires_authoritative_resolution"
_MUTATION_STATE = "not_authorized_to_apply"
_NEXT_ACTION = (
    "Before approval, re-resolve every packet reference within tenant_record_id; specifically "
    "re-resolve requester_reference and reviewer_reference through the authoritative actor "
    "boundary and verify their resolved actor identities are distinct, then verify the "
    "Person-to-Employment-to-current-Assignment binding and current Assignment/Job/Position "
    "worker scope; then verify proposed Position-to-Job binding and capacity, requested "
    "effective date, workforce-allocation policy, worker-impact evidence, and communication-"
    "plan provenance. Record accountable human approval and apply the change only through "
    "the authoritative People mutation boundary."
)


def _validate_operational_uuid(value: str, field_name: str) -> None:
    """Require canonical non-sentinel UUID text owned by the authoritative HRIS."""
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{field_name} must be canonical UUID text") from exc
    if str(parsed) != value or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(f"{field_name} must be a canonical operational UUID")


def _validate_code(value: str, field_name: str) -> None:
    """Require a bounded descriptive lower snake_case governance code."""
    if not isinstance(value, str) or len(value) > 64 or not _CODE_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be bounded two-or-more-word lower snake_case")


def _validate_reference(value: str, prefix: str, field_name: str) -> None:
    """Require an expected namespace plus a canonical opaque UUIDv4 suffix."""
    error_message = f"{field_name} must be an opaque {prefix}: reference"
    if (
        not isinstance(value, str)
        or len(value) > 160
        or not _REFERENCE_PATTERN.fullmatch(value)
        or not value.startswith(f"{prefix}:")
    ):
        raise ValueError(error_message)
    suffix = value.split(":", 1)[1]
    try:
        parsed = UUID(suffix)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(error_message) from exc
    if str(parsed) != suffix or parsed.version != 4 or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(error_message)


def _validate_digest(value: str, field_name: str) -> None:
    """Require lowercase SHA-256 hexadecimal evidence."""
    if not isinstance(value, str) or not _DIGEST_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _canonical_timestamp(value: datetime) -> str:
    """Render an aware instant as precision-preserving UTC RFC 3339 text."""
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_business_date(value: date, field_name: str) -> None:
    """Require a business date rather than a datetime or textual date."""
    if type(value) is not date:
        raise ValueError(f"{field_name} must be a date")


def _validate_evidence_version(value: int) -> None:
    """Require a bounded positive integer version for high-impact review evidence."""
    if type(value) is not int or value < 1 or value > 2_147_483_647:
        raise ValueError("evidence_version must be an integer from 1 through 2147483647")


@dataclass(frozen=True, slots=True, repr=False)
class AssignmentChangeReviewPacket:
    """Immutable assignment-change evidence that cannot itself authorize a mutation."""

    tenant_record_id: str
    assignment_change_review_reference: str
    person_record_reference: str
    employment_record_reference: str
    current_assignment_reference: str
    current_job_profile_reference: str
    current_position_record_reference: str
    proposed_job_profile_reference: str
    proposed_position_record_reference: str
    current_scope_snapshot_reference: str
    current_scope_snapshot_digest: str
    allocation_plan_reference: str
    allocation_plan_digest: str
    allocation_policy_reference: str
    allocation_policy_digest: str
    worker_impact_assessment_reference: str
    worker_impact_assessment_digest: str
    communication_plan_reference: str
    communication_plan_digest: str
    requester_reference: str
    reviewer_reference: str
    purpose_code: str
    reason_code: str
    requested_effective_on: date
    generated_at: datetime
    evidence_version: int = 1
    contains_person_pii: bool = False
    contains_compensation_values: bool = False
    contains_free_form_model_output: bool = False
    human_confirmation_required: bool = True
    decision_authority: str = _DECISION_AUTHORITY
    review_state: str = _REVIEW_STATE
    scope_verification_state: str = _SCOPE_VERIFICATION_STATE
    mutation_state: str = _MUTATION_STATE
    next_action: str = _NEXT_ACTION

    def __repr__(self) -> str:
        """Return a representation that never emits worker/assignment correlation evidence."""
        return "AssignmentChangeReviewPacket(<redacted>)"

    def __post_init__(self) -> None:
        """Fail closed when direct construction drifts from the governed contract."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.assignment_change_review_reference,
            "assignment_change_review",
            "assignment_change_review_reference",
        )
        _validate_reference(self.person_record_reference, "person_record", "person_record_reference")
        _validate_reference(
            self.employment_record_reference,
            "employment_record",
            "employment_record_reference",
        )
        _validate_reference(
            self.current_assignment_reference,
            "assignment_record",
            "current_assignment_reference",
        )
        _validate_reference(
            self.current_job_profile_reference,
            "job_profile",
            "current_job_profile_reference",
        )
        _validate_reference(
            self.current_position_record_reference,
            "position_record",
            "current_position_record_reference",
        )
        _validate_reference(
            self.proposed_job_profile_reference,
            "job_profile",
            "proposed_job_profile_reference",
        )
        _validate_reference(
            self.proposed_position_record_reference,
            "position_record",
            "proposed_position_record_reference",
        )
        _validate_reference(
            self.current_scope_snapshot_reference,
            "assignment_scope_snapshot",
            "current_scope_snapshot_reference",
        )
        _validate_digest(self.current_scope_snapshot_digest, "current_scope_snapshot_digest")
        _validate_reference(
            self.allocation_plan_reference,
            "workforce_allocation_plan",
            "allocation_plan_reference",
        )
        _validate_digest(self.allocation_plan_digest, "allocation_plan_digest")
        _validate_reference(
            self.allocation_policy_reference,
            "workforce_allocation_policy",
            "allocation_policy_reference",
        )
        _validate_digest(self.allocation_policy_digest, "allocation_policy_digest")
        _validate_reference(
            self.worker_impact_assessment_reference,
            "worker_impact_assessment",
            "worker_impact_assessment_reference",
        )
        _validate_digest(
            self.worker_impact_assessment_digest,
            "worker_impact_assessment_digest",
        )
        _validate_reference(
            self.communication_plan_reference,
            "assignment_communication_plan",
            "communication_plan_reference",
        )
        _validate_digest(self.communication_plan_digest, "communication_plan_digest")
        _validate_reference(self.requester_reference, "actor", "requester_reference")
        _validate_reference(self.reviewer_reference, "actor", "reviewer_reference")
        if self.requester_reference == self.reviewer_reference:
            raise ValueError("requester and reviewer must be different actors")
        if self.purpose_code != _PURPOSE_CODE:
            raise ValueError("purpose_code must remain assignment_change_review")
        _validate_code(self.reason_code, "reason_code")
        if self.reason_code not in _ALLOWED_REASON_CODES:
            raise ValueError("reason_code must be an approved assignment-change reason")
        _validate_business_date(self.requested_effective_on, "requested_effective_on")
        _canonical_timestamp(self.generated_at)
        _validate_evidence_version(self.evidence_version)
        if self.contains_person_pii is not False:
            raise ValueError("assignment change review packet must not contain person PII")
        if self.contains_compensation_values is not False:
            raise ValueError("assignment change review packet must not contain compensation values")
        if self.contains_free_form_model_output is not False:
            raise ValueError("assignment change review packet must not contain free-form model output")
        if self.human_confirmation_required is not True:
            raise ValueError("human confirmation is mandatory before assignment change")
        if self.decision_authority != _DECISION_AUTHORITY:
            raise ValueError("decision_authority must remain human_review_only")
        if self.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain requires_human_review")
        if self.scope_verification_state != _SCOPE_VERIFICATION_STATE:
            raise ValueError(
                "scope_verification_state must remain requires_authoritative_resolution"
            )
        if self.mutation_state != _MUTATION_STATE:
            raise ValueError("mutation_state must remain not_authorized_to_apply")
        if self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed assignment-change instruction")

    def canonical_json(self) -> str:
        """Return deterministic canonical JSON for immutable audit correlation."""
        payload = {
            "allocation_plan_digest": self.allocation_plan_digest,
            "allocation_plan_reference": self.allocation_plan_reference,
            "allocation_policy_digest": self.allocation_policy_digest,
            "allocation_policy_reference": self.allocation_policy_reference,
            "assignment_change_review_reference": self.assignment_change_review_reference,
            "communication_plan_digest": self.communication_plan_digest,
            "communication_plan_reference": self.communication_plan_reference,
            "contains_compensation_values": self.contains_compensation_values,
            "contains_free_form_model_output": self.contains_free_form_model_output,
            "contains_person_pii": self.contains_person_pii,
            "current_assignment_reference": self.current_assignment_reference,
            "current_job_profile_reference": self.current_job_profile_reference,
            "current_position_record_reference": self.current_position_record_reference,
            "current_scope_snapshot_digest": self.current_scope_snapshot_digest,
            "current_scope_snapshot_reference": self.current_scope_snapshot_reference,
            "decision_authority": self.decision_authority,
            "employment_record_reference": self.employment_record_reference,
            "evidence_version": self.evidence_version,
            "generated_at": _canonical_timestamp(self.generated_at),
            "human_confirmation_required": self.human_confirmation_required,
            "mutation_state": self.mutation_state,
            "next_action": self.next_action,
            "person_record_reference": self.person_record_reference,
            "proposed_job_profile_reference": self.proposed_job_profile_reference,
            "proposed_position_record_reference": self.proposed_position_record_reference,
            "purpose_code": self.purpose_code,
            "reason_code": self.reason_code,
            "requested_effective_on": self.requested_effective_on.isoformat(),
            "requester_reference": self.requester_reference,
            "review_state": self.review_state,
            "reviewer_reference": self.reviewer_reference,
            "scope_verification_state": self.scope_verification_state,
            "tenant_record_id": self.tenant_record_id,
            "worker_impact_assessment_digest": self.worker_impact_assessment_digest,
            "worker_impact_assessment_reference": self.worker_impact_assessment_reference,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical UTF-8 assignment-change packet."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_assignment_change_review_packet(
    *,
    tenant_record_id: str,
    assignment_change_review_reference: str,
    person_record_reference: str,
    employment_record_reference: str,
    current_assignment_reference: str,
    current_job_profile_reference: str,
    current_position_record_reference: str,
    proposed_job_profile_reference: str,
    proposed_position_record_reference: str,
    current_scope_snapshot_reference: str,
    current_scope_snapshot_digest: str,
    allocation_plan_reference: str,
    allocation_plan_digest: str,
    allocation_policy_reference: str,
    allocation_policy_digest: str,
    worker_impact_assessment_reference: str,
    worker_impact_assessment_digest: str,
    communication_plan_reference: str,
    communication_plan_digest: str,
    requester_reference: str,
    reviewer_reference: str,
    purpose_code: str,
    reason_code: str,
    requested_effective_on: date,
    generated_at: datetime,
    evidence_version: int = 1,
) -> AssignmentChangeReviewPacket:
    """Build a value-free assignment-change packet pending authoritative approval."""
    return AssignmentChangeReviewPacket(
        tenant_record_id=tenant_record_id,
        assignment_change_review_reference=assignment_change_review_reference,
        person_record_reference=person_record_reference,
        employment_record_reference=employment_record_reference,
        current_assignment_reference=current_assignment_reference,
        current_job_profile_reference=current_job_profile_reference,
        current_position_record_reference=current_position_record_reference,
        proposed_job_profile_reference=proposed_job_profile_reference,
        proposed_position_record_reference=proposed_position_record_reference,
        current_scope_snapshot_reference=current_scope_snapshot_reference,
        current_scope_snapshot_digest=current_scope_snapshot_digest,
        allocation_plan_reference=allocation_plan_reference,
        allocation_plan_digest=allocation_plan_digest,
        allocation_policy_reference=allocation_policy_reference,
        allocation_policy_digest=allocation_policy_digest,
        worker_impact_assessment_reference=worker_impact_assessment_reference,
        worker_impact_assessment_digest=worker_impact_assessment_digest,
        communication_plan_reference=communication_plan_reference,
        communication_plan_digest=communication_plan_digest,
        requester_reference=requester_reference,
        reviewer_reference=reviewer_reference,
        purpose_code=purpose_code,
        reason_code=reason_code,
        requested_effective_on=requested_effective_on,
        generated_at=generated_at,
        evidence_version=evidence_version,
    )
