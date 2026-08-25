"""PII-minimized human selection-review packet contracts.

The packet is review evidence, not an employment decision. It carries only UUID-backed
opaque resource references and governance metadata so candidate-facing or HR workflows
can prepare a decision for an accountable human without copying protected values.
Ordinary object representation is redacted because candidate/evidence references remain
sensitive correlating metadata.
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
_EVIDENCE_VERSION_PATTERN = re.compile(r"^evidence_version_([1-9][0-9]{0,9})$")
_REFERENCE_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]{1,31}:[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$"
)
_REVIEW_PURPOSE = "selection_review"
_ALLOWED_REASON_CODES = frozenset({"candidate_assessment"})
_REVIEW_STATE = "requires_human_decision"
_MODEL_OUTPUT_STATUS = "untrusted_draft"
_NEXT_ACTION = (
    "Review the evidence, confirm job relatedness and business necessity, "
    "then record the accountable human selection decision."
)


def _validate_operational_uuid(value: str, field_name: str) -> None:
    """Require exact canonical non-sentinel UUID text for a governance identity."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be canonical UUID text")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{field_name} must be canonical UUID text") from exc
    if str(parsed) != value or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(f"{field_name} must be a canonical operational UUID")


def _validate_code(value: str, field_name: str) -> None:
    """Require exact bounded, descriptive lower snake_case governance text."""
    if type(value) is not str or len(value) > 64 or not _CODE_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be bounded two-or-more-word lower snake_case")


def _validate_digest(value: str, field_name: str) -> None:
    """Require a lowercase SHA-256 digest for immutable evidence binding."""
    if type(value) is not str or not _DIGEST_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _validate_evidence_version_code(value: str) -> None:
    """Require canonical positive evidence_version_N text without value-bearing suffixes."""
    if type(value) is not str:
        raise ValueError("evidence_version_code must be a canonical positive evidence version")
    match = _EVIDENCE_VERSION_PATTERN.fullmatch(value)
    if match is None or int(match.group(1)) > 2_147_483_647:
        raise ValueError("evidence_version_code must be a canonical positive evidence version")


def _validate_reference(value: str, prefix: str, field_name: str) -> None:
    """Require exact text with the expected namespace and operational UUID suffix."""
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
    if str(parsed) != suffix or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(message)


def _freeze_timestamp(value: datetime) -> datetime:
    """Detach caller-controlled timezone behavior and store one immutable UTC instant."""
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError("generated_at must be an exact timezone-aware datetime")
    try:
        offset = value.utcoffset()
    except Exception as exc:  # noqa: BLE001 - normalize provider behavior at trust boundary.
        raise ValueError("generated_at must be an exact timezone-aware datetime") from exc
    if type(offset) is not timedelta:
        raise ValueError("generated_at must be an exact timezone-aware datetime")
    return (value.replace(tzinfo=None) - offset).replace(tzinfo=timezone.utc)


def _canonical_timestamp(value: datetime) -> str:
    """Render only a previously detached built-in UTC instant as RFC 3339 text.

    The identity check against the single ``timezone.utc`` instance also rejects
    a built-in fixed non-UTC offset such as ``timezone(timedelta(hours=9))``,
    which would otherwise serialize as ``+09:00`` and change the SHA-256
    evidence digest after a low-level ``object.__setattr__`` reinjection.
    """
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError("generated_at must be an exact timezone-aware datetime")
    return value.isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True, repr=False)
class SelectionReviewPacket:
    """Immutable, PII-minimized evidence packet awaiting an accountable human decision."""

    tenant_record_id: str
    candidate_reference: str
    job_profile_reference: str
    decision_evidence_set_reference: str
    evidence_set_digest: str
    reviewer_actor_reference: str
    purpose_code: str
    reason_code: str
    evidence_version_code: str
    generated_at: datetime
    human_confirmation_required: bool = True
    review_state: str = _REVIEW_STATE
    next_action: str = _NEXT_ACTION
    model_draft_reference: str | None = None
    model_draft_digest: str | None = None
    model_provenance_reference: str | None = None
    model_provenance_digest: str | None = None
    model_output_status: str | None = None

    def __repr__(self) -> str:
        """Return a representation that never emits candidate/evidence correlation."""
        return "SelectionReviewPacket(<redacted>)"

    def __post_init__(self) -> None:
        """Fail closed when direct construction drifts from the governed contract."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(self.candidate_reference, "candidate_profile", "candidate_reference")
        _validate_reference(self.job_profile_reference, "job_profile", "job_profile_reference")
        _validate_reference(
            self.decision_evidence_set_reference,
            "decision_evidence_set",
            "decision_evidence_set_reference",
        )
        _validate_digest(self.evidence_set_digest, "evidence_set_digest")
        _validate_reference(self.reviewer_actor_reference, "actor", "reviewer_actor_reference")
        _validate_code(self.purpose_code, "purpose_code")
        if self.purpose_code != _REVIEW_PURPOSE:
            raise ValueError("purpose_code must remain selection_review")
        _validate_code(self.reason_code, "reason_code")
        if self.reason_code not in _ALLOWED_REASON_CODES:
            raise ValueError("reason_code must be an authorized selection-review reason")
        _validate_evidence_version_code(self.evidence_version_code)
        object.__setattr__(self, "generated_at", _freeze_timestamp(self.generated_at))
        if self.human_confirmation_required is not True:
            raise ValueError("human confirmation is mandatory for selection decisions")
        if type(self.review_state) is not str or self.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain requires_human_decision")
        if type(self.next_action) is not str or self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed human-review instruction")
        model_presence = (
            self.model_draft_reference is not None,
            self.model_draft_digest is not None,
            self.model_provenance_reference is not None,
            self.model_provenance_digest is not None,
        )
        if len(set(model_presence)) != 1:
            raise ValueError(
                "model draft, draft digest, provenance, and provenance digest must be supplied together"
            )
        if model_presence[0]:
            _validate_reference(self.model_draft_reference, "model_draft", "model_draft_reference")
            _validate_digest(self.model_draft_digest, "model_draft_digest")
            _validate_reference(
                self.model_provenance_reference,
                "model_provenance",
                "model_provenance_reference",
            )
            _validate_digest(self.model_provenance_digest, "model_provenance_digest")
            if type(self.model_output_status) is not str or self.model_output_status != _MODEL_OUTPUT_STATUS:
                raise ValueError("model-backed evidence must remain untrusted_draft")
        elif self.model_output_status is not None:
            raise ValueError("model_output_status requires model draft evidence")

    def canonical_json(self) -> str:
        """Return deterministic canonical JSON for immutable audit correlation."""
        payload = {
            "candidate_reference": self.candidate_reference,
            "decision_evidence_set_reference": self.decision_evidence_set_reference,
            "evidence_set_digest": self.evidence_set_digest,
            "evidence_version_code": self.evidence_version_code,
            "generated_at": _canonical_timestamp(self.generated_at),
            "human_confirmation_required": self.human_confirmation_required,
            "job_profile_reference": self.job_profile_reference,
            "model_draft_digest": self.model_draft_digest,
            "model_draft_reference": self.model_draft_reference,
            "model_output_status": self.model_output_status,
            "model_provenance_digest": self.model_provenance_digest,
            "model_provenance_reference": self.model_provenance_reference,
            "next_action": self.next_action,
            "purpose_code": self.purpose_code,
            "reason_code": self.reason_code,
            "review_state": self.review_state,
            "reviewer_actor_reference": self.reviewer_actor_reference,
            "tenant_record_id": self.tenant_record_id,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256_digest(self) -> str:
        """Return the SHA-256 digest of the exact canonical UTF-8 packet."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_selection_review_packet(
    *,
    tenant_record_id: str,
    candidate_reference: str,
    job_profile_reference: str,
    decision_evidence_set_reference: str,
    evidence_set_digest: str,
    reviewer_actor_reference: str,
    purpose_code: str,
    reason_code: str,
    evidence_version_code: str,
    generated_at: datetime,
    model_draft_reference: str | None = None,
    model_draft_digest: str | None = None,
    model_provenance_reference: str | None = None,
    model_provenance_digest: str | None = None,
) -> SelectionReviewPacket:
    """Build a governed packet that can only proceed to an accountable human decision."""
    model_output_status = (
        _MODEL_OUTPUT_STATUS
        if any(
            value is not None
            for value in (
                model_draft_reference,
                model_draft_digest,
                model_provenance_reference,
                model_provenance_digest,
            )
        )
        else None
    )
    return SelectionReviewPacket(
        tenant_record_id=tenant_record_id,
        candidate_reference=candidate_reference,
        job_profile_reference=job_profile_reference,
        decision_evidence_set_reference=decision_evidence_set_reference,
        evidence_set_digest=evidence_set_digest,
        reviewer_actor_reference=reviewer_actor_reference,
        purpose_code=purpose_code,
        reason_code=reason_code,
        evidence_version_code=evidence_version_code,
        generated_at=generated_at,
        model_draft_reference=model_draft_reference,
        model_draft_digest=model_draft_digest,
        model_provenance_reference=model_provenance_reference,
        model_provenance_digest=model_provenance_digest,
        model_output_status=model_output_status,
    )
