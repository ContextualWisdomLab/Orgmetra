"""Governed, value-minimized pre-mutation compensation-change review evidence.

The packet correlates one proposed compensation change to authoritative worker scope and
exact reviewed policy/evidence artifacts without copying pay amounts, protected-attribute
values, narrative case material, credentials, or model output into the review envelope.
Opaque worker and evidence references remain sensitive correlating metadata. Authoritative
scope resolution, human approval, HRIS mutation, and payroll execution remain outside this
package and must occur through their published owner boundaries.
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
_PURPOSE_CODE = "compensation_change_review"
_ALLOWED_REASON_CODES = frozenset(
    {
        "annual_compensation_review",
        "promotion_compensation_review",
        "market_adjustment_review",
        "retention_adjustment_review",
        "role_change_compensation_review",
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
    "and active Assignment/Job/Position scope represented by the snapshot, then verify the "
    "current compensation snapshot, proposed compensation plan, exact compensation policy, "
    "pay-equity review, budget authorization, proposed effective date, and payroll-handoff "
    "provenance without copying compensation or protected-attribute values into this packet; "
    "then record accountable human approval, apply any authorized HRIS change only through "
    "the authoritative Orgmetra People boundary, and execute payroll only through its "
    "published owner contract."
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
    """Require lowercase SHA-256 hexadecimal evidence."""
    if type(value) is not str or not _DIGEST_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _freeze_recorded_timestamp(value: datetime) -> datetime:
    """Detach one recorded-time instant from caller-owned timezone state."""
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware exact datetime")
    offset = value.utcoffset()
    if offset is None:
        raise ValueError("generated_at must be timezone-aware exact datetime")
    utc_naive = value.replace(tzinfo=None) - offset
    return utc_naive.replace(tzinfo=timezone.utc)


def _canonical_timestamp(value: datetime) -> str:
    """Render an aware instant as precision-preserving UTC RFC 3339 text."""
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware exact datetime")
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
    """Serialize one already-snapshotted evidence payload deterministically."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _seal_issuance(packet: object, canonical: str) -> None:
    """Bind one live packet identity to its creation-time canonical evidence digest."""
    digest = sha256(canonical.encode("utf-8")).hexdigest()
    packet_id = id(packet)

    def release_issuance(_packet_reference: object) -> None:
        """Release the process-local seal when its packet is collected."""
        with _ISSUANCE_LOCK:
            _ISSUANCE_DIGESTS.pop(packet_id, None)

    packet_reference = ref(packet, release_issuance)
    with _ISSUANCE_LOCK:
        _ISSUANCE_DIGESTS[packet_id] = (packet_reference, digest)


def _assert_issuance_integrity(packet: object, canonical: str) -> None:
    """Fail closed when a live or copied packet differs from issued evidence."""
    digest = sha256(canonical.encode("utf-8")).hexdigest()
    with _ISSUANCE_LOCK:
        sealed = _ISSUANCE_DIGESTS.get(id(packet))
    if sealed is None:
        raise ValueError("compensation review evidence integrity check failed")
    if sealed[1] != digest:
        raise ValueError("compensation review evidence integrity check failed")


@dataclass(frozen=True, slots=True, repr=False, weakref_slot=True)
class CompensationChangeReviewPacket:
    """Immutable compensation-review evidence that cannot authorize mutation or payroll."""

    tenant_record_id: str
    compensation_review_reference: str
    person_record_reference: str
    employment_record_reference: str
    active_assignment_snapshot_reference: str
    active_assignment_snapshot_digest: str
    current_compensation_snapshot_reference: str
    current_compensation_snapshot_digest: str
    proposed_compensation_plan_reference: str
    proposed_compensation_plan_digest: str
    compensation_policy_reference: str
    compensation_policy_digest: str
    pay_equity_review_reference: str
    pay_equity_review_digest: str
    budget_authorization_reference: str
    budget_authorization_digest: str
    payroll_handoff_plan_reference: str
    payroll_handoff_plan_digest: str
    requester_reference: str
    reviewer_reference: str
    purpose_code: str
    reason_code: str
    proposed_effective_on: date
    generated_at: datetime
    evidence_version: int = 1
    contains_personal_data: bool = True
    contains_compensation_values: bool = False
    contains_protected_attribute_values: bool = False
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
        return "CompensationChangeReviewPacket(<redacted>)"

    def __post_init__(self) -> None:
        """Fail closed when direct construction drifts from the governed contract."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.compensation_review_reference,
            "compensation_change_review",
            "compensation_review_reference",
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
        _validate_reference(
            self.current_compensation_snapshot_reference,
            "compensation_snapshot",
            "current_compensation_snapshot_reference",
        )
        _validate_digest(
            self.current_compensation_snapshot_digest,
            "current_compensation_snapshot_digest",
        )
        _validate_reference(
            self.proposed_compensation_plan_reference,
            "compensation_plan",
            "proposed_compensation_plan_reference",
        )
        _validate_digest(
            self.proposed_compensation_plan_digest,
            "proposed_compensation_plan_digest",
        )
        _validate_reference(
            self.compensation_policy_reference,
            "compensation_policy",
            "compensation_policy_reference",
        )
        _validate_digest(self.compensation_policy_digest, "compensation_policy_digest")
        _validate_reference(
            self.pay_equity_review_reference,
            "pay_equity_review",
            "pay_equity_review_reference",
        )
        _validate_digest(self.pay_equity_review_digest, "pay_equity_review_digest")
        _validate_reference(
            self.budget_authorization_reference,
            "budget_authorization",
            "budget_authorization_reference",
        )
        _validate_digest(self.budget_authorization_digest, "budget_authorization_digest")
        _validate_reference(
            self.payroll_handoff_plan_reference,
            "payroll_handoff_plan",
            "payroll_handoff_plan_reference",
        )
        _validate_digest(self.payroll_handoff_plan_digest, "payroll_handoff_plan_digest")
        _validate_reference(self.requester_reference, "actor", "requester_reference")
        _validate_reference(self.reviewer_reference, "actor", "reviewer_reference")
        if self.requester_reference == self.reviewer_reference:
            raise ValueError("requester and reviewer must be different actor references")
        if type(self.purpose_code) is not str or self.purpose_code != _PURPOSE_CODE:
            raise ValueError("purpose_code must remain compensation_change_review")
        if type(self.reason_code) is not str or self.reason_code not in _ALLOWED_REASON_CODES:
            raise ValueError("reason_code must be an approved non-sensitive compensation-review category")
        _validate_business_date(self.proposed_effective_on, "proposed_effective_on")
        object.__setattr__(self, "generated_at", _freeze_recorded_timestamp(self.generated_at))
        _canonical_timestamp(self.generated_at)
        _validate_evidence_version(self.evidence_version)
        if self.contains_personal_data is not True:
            raise ValueError("compensation review packet must acknowledge sensitive personal-data correlation")
        if self.contains_compensation_values is not False:
            raise ValueError("compensation review packet must not contain compensation values")
        if self.contains_protected_attribute_values is not False:
            raise ValueError("compensation review packet must not contain protected-attribute values")
        if self.contains_free_form_case_narrative is not False:
            raise ValueError("compensation review packet must not contain free-form case narrative")
        if self.contains_free_form_model_output is not False:
            raise ValueError("compensation review packet must not contain free-form model output")
        if self.human_confirmation_required is not True:
            raise ValueError("human confirmation is mandatory before a compensation change")
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
            raise ValueError("next_action must remain the governed compensation-change instruction")
        _seal_issuance(self, _canonical_json(self._canonical_payload()))

    def _canonical_payload(self) -> dict[str, object]:
        """Snapshot every trust-bearing field once for integrity verification and export."""
        return {
            "active_assignment_snapshot_digest": self.active_assignment_snapshot_digest,
            "active_assignment_snapshot_reference": self.active_assignment_snapshot_reference,
            "budget_authorization_digest": self.budget_authorization_digest,
            "budget_authorization_reference": self.budget_authorization_reference,
            "compensation_policy_digest": self.compensation_policy_digest,
            "compensation_policy_reference": self.compensation_policy_reference,
            "compensation_review_reference": self.compensation_review_reference,
            "contains_compensation_values": self.contains_compensation_values,
            "contains_free_form_case_narrative": self.contains_free_form_case_narrative,
            "contains_free_form_model_output": self.contains_free_form_model_output,
            "contains_personal_data": self.contains_personal_data,
            "contains_protected_attribute_values": self.contains_protected_attribute_values,
            "current_compensation_snapshot_digest": self.current_compensation_snapshot_digest,
            "current_compensation_snapshot_reference": self.current_compensation_snapshot_reference,
            "decision_authority": self.decision_authority,
            "employment_record_reference": self.employment_record_reference,
            "evidence_version": self.evidence_version,
            "external_execution_state": self.external_execution_state,
            "generated_at": _canonical_timestamp(self.generated_at),
            "human_confirmation_required": self.human_confirmation_required,
            "mutation_state": self.mutation_state,
            "next_action": self.next_action,
            "pay_equity_review_digest": self.pay_equity_review_digest,
            "pay_equity_review_reference": self.pay_equity_review_reference,
            "payroll_handoff_plan_digest": self.payroll_handoff_plan_digest,
            "payroll_handoff_plan_reference": self.payroll_handoff_plan_reference,
            "person_record_reference": self.person_record_reference,
            "proposed_compensation_plan_digest": self.proposed_compensation_plan_digest,
            "proposed_compensation_plan_reference": self.proposed_compensation_plan_reference,
            "proposed_effective_on": self.proposed_effective_on.isoformat(),
            "purpose_code": self.purpose_code,
            "reason_code": self.reason_code,
            "requester_reference": self.requester_reference,
            "review_state": self.review_state,
            "reviewer_reference": self.reviewer_reference,
            "scope_verification_state": self.scope_verification_state,
            "tenant_record_id": self.tenant_record_id,
        }

    def canonical_json(self) -> str:
        """Return creation-bound deterministic canonical JSON for immutable audit correlation."""
        canonical = _canonical_json(self._canonical_payload())
        _assert_issuance_integrity(self, canonical)
        return canonical

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical UTF-8 compensation-review packet."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_compensation_change_review_packet(
    *,
    tenant_record_id: str,
    compensation_review_reference: str,
    person_record_reference: str,
    employment_record_reference: str,
    active_assignment_snapshot_reference: str,
    active_assignment_snapshot_digest: str,
    current_compensation_snapshot_reference: str,
    current_compensation_snapshot_digest: str,
    proposed_compensation_plan_reference: str,
    proposed_compensation_plan_digest: str,
    compensation_policy_reference: str,
    compensation_policy_digest: str,
    pay_equity_review_reference: str,
    pay_equity_review_digest: str,
    budget_authorization_reference: str,
    budget_authorization_digest: str,
    payroll_handoff_plan_reference: str,
    payroll_handoff_plan_digest: str,
    requester_reference: str,
    reviewer_reference: str,
    purpose_code: str,
    reason_code: str,
    proposed_effective_on: date,
    generated_at: datetime,
    evidence_version: int = 1,
) -> CompensationChangeReviewPacket:
    """Build a value-minimized compensation packet pending authoritative human approval."""
    return CompensationChangeReviewPacket(
        tenant_record_id=tenant_record_id,
        compensation_review_reference=compensation_review_reference,
        person_record_reference=person_record_reference,
        employment_record_reference=employment_record_reference,
        active_assignment_snapshot_reference=active_assignment_snapshot_reference,
        active_assignment_snapshot_digest=active_assignment_snapshot_digest,
        current_compensation_snapshot_reference=current_compensation_snapshot_reference,
        current_compensation_snapshot_digest=current_compensation_snapshot_digest,
        proposed_compensation_plan_reference=proposed_compensation_plan_reference,
        proposed_compensation_plan_digest=proposed_compensation_plan_digest,
        compensation_policy_reference=compensation_policy_reference,
        compensation_policy_digest=compensation_policy_digest,
        pay_equity_review_reference=pay_equity_review_reference,
        pay_equity_review_digest=pay_equity_review_digest,
        budget_authorization_reference=budget_authorization_reference,
        budget_authorization_digest=budget_authorization_digest,
        payroll_handoff_plan_reference=payroll_handoff_plan_reference,
        payroll_handoff_plan_digest=payroll_handoff_plan_digest,
        requester_reference=requester_reference,
        reviewer_reference=reviewer_reference,
        purpose_code=purpose_code,
        reason_code=reason_code,
        proposed_effective_on=proposed_effective_on,
        generated_at=generated_at,
        evidence_version=evidence_version,
    )
