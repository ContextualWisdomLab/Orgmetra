"""Governed, value-free pre-mutation employment-separation review evidence.

The packet correlates one proposed employment separation to authoritative Person and
Employment scope, an exact active-assignment snapshot, reviewed separation policy and
process evidence, value-free final-pay and benefits handoffs, access-deprovisioning,
asset-return, knowledge-transfer, and communication plans. Opaque Person and Employment
references remain sensitive correlating metadata. Person PII, compensation or benefit
values, case narrative, credentials, and free-form model output stay outside this
envelope. Final scope resolution, approval, HRIS mutation, and external owner execution
remain at their authoritative boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import hmac
import json
import re
import secrets
from threading import RLock
from uuid import UUID
from weakref import finalize

_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]{1,31}:[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$"
)
_PURPOSE_CODE = "employment_separation_review"
_ALLOWED_REASON_CODES = frozenset(
    {
        "voluntary_resignation",
        "retirement_transition",
        "fixed_term_completion",
        "position_elimination",
        "employer_initiated_separation",
    }
)
_DECISION_AUTHORITY = "human_review_only"
_REVIEW_STATE = "requires_human_review"
_SCOPE_VERIFICATION_STATE = "requires_authoritative_resolution"
_MUTATION_STATE = "not_authorized_to_apply"
_EXTERNAL_EXECUTION_STATE = "not_authorized_to_execute"
_NEXT_ACTION = (
    "Re-resolve every packet reference within tenant_record_id; specifically re-resolve "
    "requester_reference and reviewer_reference within tenant_record_id and verify their "
    "resolved actor identities are distinct, then prove the Person-to-Employment binding "
    "and every active Assignment/Job/Position in the bound snapshot, then verify the "
    "proposed separation date, reviewed separation policy and process, value-free final-pay "
    "and benefits handoffs, access-deprovisioning, asset-return, knowledge-transfer, and "
    "communication-plan provenance; then record accountable human approval, apply the "
    "employment change only through the authoritative People mutation boundary, and execute "
    "downstream actions only through their published owner boundaries."
)
_PROCESS_REVIEW_SEAL_KEY = secrets.token_bytes(32)
_REVIEW_SEALS: dict[int, str] = {}
_REVIEW_SEALS_LOCK = RLock()


def _discard_review_seal(packet_id: int) -> None:
    """Discard process-local review issuance evidence after its packet is collected."""
    with _REVIEW_SEALS_LOCK:
        _REVIEW_SEALS.pop(packet_id, None)


def _register_review_seal(packet: object, seal: str) -> None:
    """Bind one live packet identity to evidence outside packet-writable slots."""
    packet_id = id(packet)
    with _REVIEW_SEALS_LOCK:
        _REVIEW_SEALS[packet_id] = seal
    finalize(packet, _discard_review_seal, packet_id)


def _authoritative_review_seal(packet: object) -> str | None:
    """Return process-local issuance evidence without trusting packet-owned state."""
    with _REVIEW_SEALS_LOCK:
        return _REVIEW_SEALS.get(id(packet))


def _seal_review(payload_json: str) -> str:
    """Bind one process-local review issuance to its exact canonical payload bytes."""
    return hmac.new(_PROCESS_REVIEW_SEAL_KEY, payload_json.encode("utf-8"), "sha256").hexdigest()


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


def _validate_code(value: str, field_name: str) -> None:
    """Require exact bounded descriptive lower snake_case governance text."""
    if type(value) is not str or len(value) > 64 or not _CODE_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be bounded two-or-more-word lower snake_case")


def _validate_reference(value: str, prefix: str, field_name: str) -> None:
    """Require an expected namespace plus a canonical opaque UUIDv4 suffix."""
    error_message = f"{field_name} must be an opaque {prefix}: reference"
    if (
        type(value) is not str
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


def _validate_digest(value: str, field_name: str = "digest") -> None:
    """Require exact built-in lowercase SHA-256 hexadecimal evidence."""
    if type(value) is not str or not _DIGEST_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _freeze_timestamp(value: datetime) -> datetime:
    """Resolve caller timezone behavior once and store one immutable UTC instant."""
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError("generated_at must be an exact timezone-aware datetime")
    try:
        offset = value.utcoffset()
    except Exception as exc:
        raise ValueError("generated_at must be an exact timezone-aware datetime") from exc
    if type(offset) is not timedelta:
        raise ValueError("generated_at must be an exact timezone-aware datetime")
    try:
        frozen = (value.replace(tzinfo=None) - offset).replace(tzinfo=timezone.utc)
    except (OverflowError, ValueError) as exc:
        raise ValueError("generated_at must be an exact timezone-aware datetime") from exc
    if frozen > datetime.now(timezone.utc):
        raise ValueError("generated_at must not be in the future")
    return frozen


def _canonical_timestamp(value: datetime) -> str:
    """Render one already-frozen UTC instant as precision-preserving RFC 3339 text."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError("generated_at must be an exact timezone-aware datetime")
    return value.isoformat().replace("+00:00", "Z")


def _validate_business_date(value: date, field_name: str) -> None:
    """Require a business date rather than a datetime or textual date."""
    if type(value) is not date:
        raise ValueError(f"{field_name} must be a date")


def _validate_evidence_version(value: int) -> None:
    """Require a bounded positive integer version for high-impact review evidence."""
    if type(value) is not int or value < 1 or value > 2_147_483_647:
        raise ValueError("evidence_version must be an integer from 1 through 2147483647")


@dataclass(frozen=True, slots=True, repr=False, weakref_slot=True)
class EmploymentSeparationReviewPacket:
    """Immutable separation evidence that cannot authorize mutation or owner execution."""

    tenant_record_id: str
    separation_review_reference: str
    person_record_reference: str
    employment_record_reference: str
    active_assignment_snapshot_reference: str
    active_assignment_snapshot_digest: str
    separation_policy_reference: str
    separation_policy_digest: str
    separation_process_reference: str
    separation_process_digest: str
    final_pay_handoff_reference: str
    final_pay_handoff_digest: str
    benefits_handoff_reference: str
    benefits_handoff_digest: str
    access_deprovisioning_plan_reference: str
    access_deprovisioning_plan_digest: str
    asset_return_plan_reference: str
    asset_return_plan_digest: str
    knowledge_transfer_plan_reference: str
    knowledge_transfer_plan_digest: str
    communication_plan_reference: str
    communication_plan_digest: str
    requester_reference: str
    reviewer_reference: str
    purpose_code: str
    reason_code: str
    proposed_separation_on: date
    generated_at: datetime
    evidence_version: int = 1
    contains_person_pii: bool = False
    contains_compensation_values: bool = False
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
        """Return a representation that never emits sensitive correlation evidence."""
        return "EmploymentSeparationReviewPacket(<redacted>)"

    def __post_init__(self) -> None:
        """Fail closed when direct construction drifts from the governed contract."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.separation_review_reference,
            "employment_separation_review",
            "separation_review_reference",
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
        _validate_digest(
            self.active_assignment_snapshot_digest,
            "active_assignment_snapshot_digest",
        )
        _validate_reference(
            self.separation_policy_reference,
            "employment_separation_policy",
            "separation_policy_reference",
        )
        _validate_digest(self.separation_policy_digest, "separation_policy_digest")
        _validate_reference(
            self.separation_process_reference,
            "employment_separation_process",
            "separation_process_reference",
        )
        _validate_digest(self.separation_process_digest, "separation_process_digest")
        _validate_reference(
            self.final_pay_handoff_reference,
            "final_pay_handoff",
            "final_pay_handoff_reference",
        )
        _validate_digest(self.final_pay_handoff_digest, "final_pay_handoff_digest")
        _validate_reference(
            self.benefits_handoff_reference,
            "benefits_handoff",
            "benefits_handoff_reference",
        )
        _validate_digest(self.benefits_handoff_digest, "benefits_handoff_digest")
        _validate_reference(
            self.access_deprovisioning_plan_reference,
            "access_deprovisioning_plan",
            "access_deprovisioning_plan_reference",
        )
        _validate_digest(
            self.access_deprovisioning_plan_digest,
            "access_deprovisioning_plan_digest",
        )
        _validate_reference(
            self.asset_return_plan_reference,
            "asset_return_plan",
            "asset_return_plan_reference",
        )
        _validate_digest(self.asset_return_plan_digest, "asset_return_plan_digest")
        _validate_reference(
            self.knowledge_transfer_plan_reference,
            "knowledge_transfer_plan",
            "knowledge_transfer_plan_reference",
        )
        _validate_digest(
            self.knowledge_transfer_plan_digest,
            "knowledge_transfer_plan_digest",
        )
        _validate_reference(
            self.communication_plan_reference,
            "separation_communication_plan",
            "communication_plan_reference",
        )
        _validate_digest(self.communication_plan_digest, "communication_plan_digest")
        _validate_reference(self.requester_reference, "actor", "requester_reference")
        _validate_reference(self.reviewer_reference, "actor", "reviewer_reference")
        if self.requester_reference == self.reviewer_reference:
            raise ValueError("requester and reviewer must be different actors")
        if type(self.purpose_code) is not str or self.purpose_code != _PURPOSE_CODE:
            raise ValueError("purpose_code must remain employment_separation_review")
        _validate_code(self.reason_code, "reason_code")
        if self.reason_code not in _ALLOWED_REASON_CODES:
            raise ValueError("reason_code must be an approved separation reason")
        _validate_business_date(self.proposed_separation_on, "proposed_separation_on")
        object.__setattr__(self, "generated_at", _freeze_timestamp(self.generated_at))
        _validate_evidence_version(self.evidence_version)
        if self.contains_person_pii is not False:
            raise ValueError("employment separation review packet must not contain person PII")
        if self.contains_compensation_values is not False:
            raise ValueError(
                "employment separation review packet must not contain compensation values"
            )
        if self.contains_free_form_case_narrative is not False:
            raise ValueError(
                "employment separation review packet must not contain free-form case narrative"
            )
        if self.contains_free_form_model_output is not False:
            raise ValueError(
                "employment separation review packet must not contain free-form model output"
            )
        if self.human_confirmation_required is not True:
            raise ValueError("human confirmation is mandatory before employment separation")
        if type(self.decision_authority) is not str or self.decision_authority != _DECISION_AUTHORITY:
            raise ValueError("decision_authority must remain human_review_only")
        if type(self.review_state) is not str or self.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain requires_human_review")
        if (
            type(self.scope_verification_state) is not str
            or self.scope_verification_state != _SCOPE_VERIFICATION_STATE
        ):
            raise ValueError(
                "scope_verification_state must remain requires_authoritative_resolution"
            )
        if type(self.mutation_state) is not str or self.mutation_state != _MUTATION_STATE:
            raise ValueError("mutation_state must remain not_authorized_to_apply")
        if (
            type(self.external_execution_state) is not str
            or self.external_execution_state != _EXTERNAL_EXECUTION_STATE
        ):
            raise ValueError(
                "external_execution_state must remain not_authorized_to_execute"
            )
        if type(self.next_action) is not str or self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed employment-separation instruction")
        _register_review_seal(self, _seal_review(self._canonical_json_unchecked()))

    def _canonical_json_unchecked(self) -> str:
        """Render canonical review bytes without consulting process-local issuance state."""
        payload = {
            "access_deprovisioning_plan_digest": self.access_deprovisioning_plan_digest,
            "access_deprovisioning_plan_reference": self.access_deprovisioning_plan_reference,
            "active_assignment_snapshot_digest": self.active_assignment_snapshot_digest,
            "active_assignment_snapshot_reference": self.active_assignment_snapshot_reference,
            "asset_return_plan_digest": self.asset_return_plan_digest,
            "asset_return_plan_reference": self.asset_return_plan_reference,
            "benefits_handoff_digest": self.benefits_handoff_digest,
            "benefits_handoff_reference": self.benefits_handoff_reference,
            "communication_plan_digest": self.communication_plan_digest,
            "communication_plan_reference": self.communication_plan_reference,
            "contains_compensation_values": self.contains_compensation_values,
            "contains_free_form_case_narrative": self.contains_free_form_case_narrative,
            "contains_free_form_model_output": self.contains_free_form_model_output,
            "contains_person_pii": self.contains_person_pii,
            "decision_authority": self.decision_authority,
            "employment_record_reference": self.employment_record_reference,
            "evidence_version": self.evidence_version,
            "external_execution_state": self.external_execution_state,
            "final_pay_handoff_digest": self.final_pay_handoff_digest,
            "final_pay_handoff_reference": self.final_pay_handoff_reference,
            "generated_at": _canonical_timestamp(self.generated_at),
            "human_confirmation_required": self.human_confirmation_required,
            "knowledge_transfer_plan_digest": self.knowledge_transfer_plan_digest,
            "knowledge_transfer_plan_reference": self.knowledge_transfer_plan_reference,
            "mutation_state": self.mutation_state,
            "next_action": self.next_action,
            "person_record_reference": self.person_record_reference,
            "proposed_separation_on": self.proposed_separation_on.isoformat(),
            "purpose_code": self.purpose_code,
            "reason_code": self.reason_code,
            "requester_reference": self.requester_reference,
            "review_state": self.review_state,
            "reviewer_reference": self.reviewer_reference,
            "scope_verification_state": self.scope_verification_state,
            "separation_policy_digest": self.separation_policy_digest,
            "separation_policy_reference": self.separation_policy_reference,
            "separation_process_digest": self.separation_process_digest,
            "separation_process_reference": self.separation_process_reference,
            "separation_review_reference": self.separation_review_reference,
            "tenant_record_id": self.tenant_record_id,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def canonical_json(self) -> str:
        """Return creation-bound canonical JSON for immutable audit correlation."""
        canonical = self._canonical_json_unchecked()
        authoritative_seal = _authoritative_review_seal(self)
        if (
            type(authoritative_seal) is not str
            or not hmac.compare_digest(_seal_review(canonical), authoritative_seal)
        ):
            raise ValueError("employment separation review changed after review issuance")
        return canonical

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical UTF-8 separation-review packet."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_employment_separation_review_packet(
    *,
    tenant_record_id: str,
    separation_review_reference: str,
    person_record_reference: str,
    employment_record_reference: str,
    active_assignment_snapshot_reference: str,
    active_assignment_snapshot_digest: str,
    separation_policy_reference: str,
    separation_policy_digest: str,
    separation_process_reference: str,
    separation_process_digest: str,
    final_pay_handoff_reference: str,
    final_pay_handoff_digest: str,
    benefits_handoff_reference: str,
    benefits_handoff_digest: str,
    access_deprovisioning_plan_reference: str,
    access_deprovisioning_plan_digest: str,
    asset_return_plan_reference: str,
    asset_return_plan_digest: str,
    knowledge_transfer_plan_reference: str,
    knowledge_transfer_plan_digest: str,
    communication_plan_reference: str,
    communication_plan_digest: str,
    requester_reference: str,
    reviewer_reference: str,
    purpose_code: str,
    reason_code: str,
    proposed_separation_on: date,
    generated_at: datetime,
    evidence_version: int = 1,
) -> EmploymentSeparationReviewPacket:
    """Build a value-free separation packet pending authoritative human approval."""
    return EmploymentSeparationReviewPacket(
        tenant_record_id=tenant_record_id,
        separation_review_reference=separation_review_reference,
        person_record_reference=person_record_reference,
        employment_record_reference=employment_record_reference,
        active_assignment_snapshot_reference=active_assignment_snapshot_reference,
        active_assignment_snapshot_digest=active_assignment_snapshot_digest,
        separation_policy_reference=separation_policy_reference,
        separation_policy_digest=separation_policy_digest,
        separation_process_reference=separation_process_reference,
        separation_process_digest=separation_process_digest,
        final_pay_handoff_reference=final_pay_handoff_reference,
        final_pay_handoff_digest=final_pay_handoff_digest,
        benefits_handoff_reference=benefits_handoff_reference,
        benefits_handoff_digest=benefits_handoff_digest,
        access_deprovisioning_plan_reference=access_deprovisioning_plan_reference,
        access_deprovisioning_plan_digest=access_deprovisioning_plan_digest,
        asset_return_plan_reference=asset_return_plan_reference,
        asset_return_plan_digest=asset_return_plan_digest,
        knowledge_transfer_plan_reference=knowledge_transfer_plan_reference,
        knowledge_transfer_plan_digest=knowledge_transfer_plan_digest,
        communication_plan_reference=communication_plan_reference,
        communication_plan_digest=communication_plan_digest,
        requester_reference=requester_reference,
        reviewer_reference=reviewer_reference,
        purpose_code=purpose_code,
        reason_code=reason_code,
        proposed_separation_on=proposed_separation_on,
        generated_at=generated_at,
        evidence_version=evidence_version,
    )