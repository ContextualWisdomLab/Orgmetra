"""Governed, value-free human offer-approval evidence.

The packet binds one selected candidate to an authoritative requisition and Job, an
optional exact Position, the reviewed selection decision, compensation-package
provenance, offer-terms provenance, and accountable human actors. The opaque candidate
reference remains sensitive correlating metadata. Candidate PII, compensation values,
assessment scores, and free-form model output remain outside this envelope.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from uuid import UUID

_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]{1,31}:[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$"
)
_PURPOSE_CODE = "offer_approval_review"
_ALLOWED_REASON_CODES = frozenset({"selected_candidate_offer_review"})
_DECISION_AUTHORITY = "human_approval_only"
_REVIEW_STATE = "requires_human_approval"
_DELIVERY_STATE = "not_authorized_to_send"
_NEXT_ACTION = (
    "Within tenant_record_id, re-resolve every packet reference through its authoritative "
    "boundary; specifically re-resolve requester_reference and approver_reference and verify "
    "their resolved actor identities are distinct; then verify authoritative Job/Position "
    "scope, selected-candidate evidence, compensation-package provenance, and offer-terms "
    "provenance before recording accountable human approval through the authoritative offer "
    "workflow and before communicating or executing the offer."
)


def _validate_operational_uuid(value: str, field_name: str) -> None:
    """Require canonical non-sentinel UUID text for a governance identity."""
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


def _validate_evidence_version(value: int) -> None:
    """Require a bounded positive integer version for high-impact offer-review evidence."""
    if type(value) is not int or value < 1 or value > 2_147_483_647:
        raise ValueError("evidence_version must be an integer from 1 through 2147483647")


@dataclass(frozen=True, slots=True, repr=False)
class OfferApprovalPacket:
    """Immutable value-free offer review packet awaiting accountable approval."""

    tenant_record_id: str
    offer_approval_reference: str
    candidate_profile_reference: str
    requisition_reference: str
    job_profile_reference: str
    position_record_reference: str | None
    selection_decision_reference: str
    selection_decision_digest: str
    compensation_package_reference: str
    compensation_package_digest: str
    offer_terms_reference: str
    offer_terms_digest: str
    requester_reference: str
    approver_reference: str
    purpose_code: str
    reason_code: str
    generated_at: datetime
    evidence_version: int = 1
    contains_candidate_pii: bool = False
    contains_compensation_values: bool = False
    human_confirmation_required: bool = True
    decision_authority: str = _DECISION_AUTHORITY
    review_state: str = _REVIEW_STATE
    delivery_state: str = _DELIVERY_STATE
    next_action: str = _NEXT_ACTION

    def __repr__(self) -> str:
        """Return a representation that never emits candidate or compensation evidence."""
        return "OfferApprovalPacket(<redacted>)"

    def __post_init__(self) -> None:
        """Fail closed when direct construction drifts from the governed contract."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.offer_approval_reference,
            "offer_approval",
            "offer_approval_reference",
        )
        _validate_reference(
            self.candidate_profile_reference,
            "candidate_profile",
            "candidate_profile_reference",
        )
        _validate_reference(self.requisition_reference, "requisition", "requisition_reference")
        _validate_reference(self.job_profile_reference, "job_profile", "job_profile_reference")
        if self.position_record_reference is not None:
            _validate_reference(
                self.position_record_reference,
                "position_record",
                "position_record_reference",
            )
        _validate_reference(
            self.selection_decision_reference,
            "selection_decision",
            "selection_decision_reference",
        )
        _validate_digest(self.selection_decision_digest, "selection_decision_digest")
        _validate_reference(
            self.compensation_package_reference,
            "compensation_package",
            "compensation_package_reference",
        )
        _validate_digest(self.compensation_package_digest, "compensation_package_digest")
        _validate_reference(self.offer_terms_reference, "offer_terms", "offer_terms_reference")
        _validate_digest(self.offer_terms_digest, "offer_terms_digest")
        _validate_reference(self.requester_reference, "actor", "requester_reference")
        _validate_reference(self.approver_reference, "actor", "approver_reference")
        if self.requester_reference == self.approver_reference:
            raise ValueError("approver_reference must identify a different accountable actor")
        _validate_code(self.purpose_code, "purpose_code")
        if self.purpose_code != _PURPOSE_CODE:
            raise ValueError("purpose_code must remain offer_approval_review")
        _validate_code(self.reason_code, "reason_code")
        if self.reason_code not in _ALLOWED_REASON_CODES:
            raise ValueError("reason_code must use a reviewed non-sensitive offer reason")
        _canonical_timestamp(self.generated_at)
        _validate_evidence_version(self.evidence_version)
        if self.contains_candidate_pii is not False:
            raise ValueError("offer approval packet must not contain candidate PII")
        if self.contains_compensation_values is not False:
            raise ValueError("offer approval packet must not contain compensation values")
        if self.human_confirmation_required is not True:
            raise ValueError("human confirmation is mandatory before offer approval")
        if self.decision_authority != _DECISION_AUTHORITY:
            raise ValueError("decision_authority must remain human_approval_only")
        if self.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain requires_human_approval")
        if self.delivery_state != _DELIVERY_STATE:
            raise ValueError("delivery_state must remain not_authorized_to_send")
        if self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed offer-approval instruction")

    def canonical_json(self) -> str:
        """Return deterministic canonical JSON for immutable audit correlation."""
        payload = {
            "approver_reference": self.approver_reference,
            "candidate_profile_reference": self.candidate_profile_reference,
            "compensation_package_digest": self.compensation_package_digest,
            "compensation_package_reference": self.compensation_package_reference,
            "contains_candidate_pii": self.contains_candidate_pii,
            "contains_compensation_values": self.contains_compensation_values,
            "decision_authority": self.decision_authority,
            "delivery_state": self.delivery_state,
            "evidence_version": self.evidence_version,
            "generated_at": _canonical_timestamp(self.generated_at),
            "human_confirmation_required": self.human_confirmation_required,
            "job_profile_reference": self.job_profile_reference,
            "next_action": self.next_action,
            "offer_approval_reference": self.offer_approval_reference,
            "offer_terms_digest": self.offer_terms_digest,
            "offer_terms_reference": self.offer_terms_reference,
            "position_record_reference": self.position_record_reference,
            "purpose_code": self.purpose_code,
            "reason_code": self.reason_code,
            "requester_reference": self.requester_reference,
            "requisition_reference": self.requisition_reference,
            "review_state": self.review_state,
            "selection_decision_digest": self.selection_decision_digest,
            "selection_decision_reference": self.selection_decision_reference,
            "tenant_record_id": self.tenant_record_id,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical UTF-8 offer-approval packet."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_offer_approval_packet(
    *,
    tenant_record_id: str,
    offer_approval_reference: str,
    candidate_profile_reference: str,
    requisition_reference: str,
    job_profile_reference: str,
    position_record_reference: str | None,
    selection_decision_reference: str,
    selection_decision_digest: str,
    compensation_package_reference: str,
    compensation_package_digest: str,
    offer_terms_reference: str,
    offer_terms_digest: str,
    requester_reference: str,
    approver_reference: str,
    purpose_code: str,
    reason_code: str,
    generated_at: datetime,
    evidence_version: int = 1,
) -> OfferApprovalPacket:
    """Build value-free offer-approval evidence pending accountable human approval."""
    return OfferApprovalPacket(
        tenant_record_id=tenant_record_id,
        offer_approval_reference=offer_approval_reference,
        candidate_profile_reference=candidate_profile_reference,
        requisition_reference=requisition_reference,
        job_profile_reference=job_profile_reference,
        position_record_reference=position_record_reference,
        selection_decision_reference=selection_decision_reference,
        selection_decision_digest=selection_decision_digest,
        compensation_package_reference=compensation_package_reference,
        compensation_package_digest=compensation_package_digest,
        offer_terms_reference=offer_terms_reference,
        offer_terms_digest=offer_terms_digest,
        requester_reference=requester_reference,
        approver_reference=approver_reference,
        purpose_code=purpose_code,
        reason_code=reason_code,
        generated_at=generated_at,
        evidence_version=evidence_version,
    )
