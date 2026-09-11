import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from uuid import UUID

_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]{1,31}:[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$"
)
_DISPOSITION_PURPOSE = "candidate_document_disposition"
_ALLOWED_REASON_CODES = frozenset({
    "non_selected_applicant_return",
    "talent_pool_consent_withdrawal",
    "talent_pool_expiry",
    "confirmed_hire_materialization",
    "statutory_retention_expiry",
    "legal_hold_release",
})
_ALLOWED_RETURN_ELIGIBILITY_CODES = frozenset({
    "eligible",
    "return_exception_voluntary_submission",
    "return_exception_not_requested_by_employer",
    "waived",
})
_ALLOWED_STATES = frozenset({
    "created",
    "return_claim_window_open",
    "return_requested",
    "return_request_verified",
    "return_dispatched",
    "return_destroyed",
    "talent_pool_retained",
    "confirmed_hire_transitioned",
    "statutory_retained",
    "statutory_retention_expired_destroyed",
    "legal_hold_suspended",
    "destroyed",
})
_ALLOWED_RETENTION_ANCHOR_EVENTS = frozenset({
    "hiring_decision_finalized",
    "confirmed_hire",
    "separation",
    "consent_revoked",
    "talent_pool_expired",
    "statutory_period_start",
})
_REVIEW_STATE = "requires_human_disposition_review"
_NEXT_ACTION = (
    "Within tenant_record_id, verify the disposition event against the authoritative "
    "talent_acquisition or people_core record; confirm no conflicting legal hold, "
    "then request artifact lifecycle disposition from document_records."
)


def _validate_operational_uuid(value: str, field_name: str) -> None:
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{field_name} must be canonical UUID text") from exc
    if str(parsed) != value or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(f"{field_name} must be a canonical operational UUID")


def _validate_code(value: str, field_name: str) -> None:
    if not isinstance(value, str) or len(value) > 64 or not _CODE_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be bounded two-or-more-word lower snake_case")


def _validate_digest(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not _DIGEST_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _validate_reference(value: str, prefix: str, field_name: str) -> None:
    message = f"{field_name} must be an opaque {prefix}: reference"
    if (
        not isinstance(value, str)
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


def _canonical_timestamp(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True, repr=False)
class CandidateDocumentDisposition:
    """Immutable, PII-minimized candidate-document disposition packet.

    Carries the disposition intent for a candidate document across the
    talent_acquisition, people_core, and document_records boundaries.
    """

    tenant_record_id: str
    disposition_reference: str
    document_reference: str
    candidate_reference: str
    hiring_decision_finalized_at: datetime
    return_eligibility: str
    state: str
    retention_policy_version: str
    retention_policy_digest: str
    retention_anchor_event: str
    retain_until: datetime | None
    legal_hold: bool
    purpose_code: str
    reason_code: str
    evidence_version: int
    actor_reference: str
    previous_disposition_reference: str | None = None
    claim_window_end: datetime | None = None
    return_dispatched_at: datetime | None = None
    statutory_retain_until: datetime | None = None
    human_confirmation_required: bool = True
    review_state: str = _REVIEW_STATE
    next_action: str = _NEXT_ACTION

    def __repr__(self) -> str:
        return "CandidateDocumentDisposition(<redacted>)"

    def __post_init__(self) -> None:
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(self.disposition_reference, "candidate_document_disposition", "disposition_reference")
        _validate_reference(self.document_reference, "document", "document_reference")
        _validate_reference(self.candidate_reference, "candidate_profile", "candidate_reference")
        _canonical_timestamp(self.hiring_decision_finalized_at)
        _validate_code(self.return_eligibility, "return_eligibility")
        if self.return_eligibility not in _ALLOWED_RETURN_ELIGIBILITY_CODES:
            raise ValueError("return_eligibility must be an authorized disposition return code")
        _validate_code(self.state, "state")
        if self.state not in _ALLOWED_STATES:
            raise ValueError("state must be an authorized disposition state")
        _validate_code(self.retention_policy_version, "retention_policy_version")
        _validate_digest(self.retention_policy_digest, "retention_policy_digest")
        _validate_code(self.retention_anchor_event, "retention_anchor_event")
        if self.retention_anchor_event not in _ALLOWED_RETENTION_ANCHOR_EVENTS:
            raise ValueError("retention_anchor_event must be an authorized anchor event")
        if self.retain_until is not None:
            _canonical_timestamp(self.retain_until)
        if self.claim_window_end is not None:
            _canonical_timestamp(self.claim_window_end)
        if self.return_dispatched_at is not None:
            _canonical_timestamp(self.return_dispatched_at)
        if self.statutory_retain_until is not None:
            _canonical_timestamp(self.statutory_retain_until)
        _validate_code(self.purpose_code, "purpose_code")
        if self.purpose_code != _DISPOSITION_PURPOSE:
            raise ValueError("purpose_code must remain candidate_document_disposition")
        _validate_code(self.reason_code, "reason_code")
        if self.reason_code not in _ALLOWED_REASON_CODES:
            raise ValueError("reason_code must be an authorized disposition reason")
        if type(self.evidence_version) is not int or not 1 <= self.evidence_version <= 2_147_483_647:
            raise ValueError("evidence_version must be an integer from 1 through 2147483647")
        _validate_reference(self.actor_reference, "actor", "actor_reference")
        if self.previous_disposition_reference is not None:
            _validate_reference(
                self.previous_disposition_reference,
                "candidate_document_disposition",
                "previous_disposition_reference",
            )
        if self.human_confirmation_required is not True:
            raise ValueError("human confirmation is mandatory for document disposition")
        if self.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain requires_human_disposition_review")
        if self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed disposition instruction")
        if self.legal_hold and self.state == "destroyed":
            raise ValueError("a document under legal hold cannot be destroyed")

    def canonical_json(self) -> str:
        payload = {
            "actor_reference": self.actor_reference,
            "candidate_reference": self.candidate_reference,
            "claim_window_end": _canonical_timestamp(self.claim_window_end) if self.claim_window_end is not None else None,
            "disposition_reference": self.disposition_reference,
            "document_reference": self.document_reference,
            "evidence_version": self.evidence_version,
            "hiring_decision_finalized_at": _canonical_timestamp(self.hiring_decision_finalized_at),
            "human_confirmation_required": self.human_confirmation_required,
            "legal_hold": self.legal_hold,
            "next_action": self.next_action,
            "previous_disposition_reference": self.previous_disposition_reference,
            "purpose_code": self.purpose_code,
            "reason_code": self.reason_code,
            "retain_until": _canonical_timestamp(self.retain_until) if self.retain_until is not None else None,
            "retention_anchor_event": self.retention_anchor_event,
            "retention_policy_digest": self.retention_policy_digest,
            "retention_policy_version": self.retention_policy_version,
            "return_dispatched_at": _canonical_timestamp(self.return_dispatched_at) if self.return_dispatched_at is not None else None,
            "return_eligibility": self.return_eligibility,
            "review_state": self.review_state,
            "state": self.state,
            "statutory_retain_until": _canonical_timestamp(self.statutory_retain_until) if self.statutory_retain_until is not None else None,
            "tenant_record_id": self.tenant_record_id,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256_digest(self) -> str:
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_candidate_document_disposition(
    *,
    tenant_record_id: str,
    disposition_reference: str,
    document_reference: str,
    candidate_reference: str,
    hiring_decision_finalized_at: datetime,
    return_eligibility: str,
    state: str,
    retention_policy_version: str,
    retention_policy_digest: str,
    retention_anchor_event: str,
    retain_until: datetime | None = None,
    legal_hold: bool = False,
    purpose_code: str,
    reason_code: str,
    evidence_version: int = 1,
    actor_reference: str,
    previous_disposition_reference: str | None = None,
    claim_window_end: datetime | None = None,
    return_dispatched_at: datetime | None = None,
    statutory_retain_until: datetime | None = None,
) -> CandidateDocumentDisposition:
    return CandidateDocumentDisposition(
        tenant_record_id=tenant_record_id,
        disposition_reference=disposition_reference,
        document_reference=document_reference,
        candidate_reference=candidate_reference,
        hiring_decision_finalized_at=hiring_decision_finalized_at,
        return_eligibility=return_eligibility,
        state=state,
        retention_policy_version=retention_policy_version,
        retention_policy_digest=retention_policy_digest,
        retention_anchor_event=retention_anchor_event,
        retain_until=retain_until,
        legal_hold=legal_hold,
        purpose_code=purpose_code,
        reason_code=reason_code,
        evidence_version=evidence_version,
        actor_reference=actor_reference,
        previous_disposition_reference=previous_disposition_reference,
        claim_window_end=claim_window_end,
        return_dispatched_at=return_dispatched_at,
        statutory_retain_until=statutory_retain_until,
    )
