"""PII-minimized requisition-review packet contracts.

The packet is approval evidence for opening a recruiting workflow, not a candidate
selection decision. It binds one planned opening to an authoritative Job, optional
Position seat, job-requirements evidence, accountable actors, and governance metadata
without copying candidate or employee PII.
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
_REQUIREMENTS_VERSION_PATTERN = re.compile(r"^requirements_version_[1-9][0-9]{0,8}$")
_REVIEW_PURPOSE = "requisition_review"
_REVIEW_STATE = "requires_human_approval"
_ALLOWED_REASON_CODES = frozenset({"approved_growth_plan"})
_NEXT_ACTION = (
    "Within tenant_record_id, re-resolve hiring_manager_actor_reference and "
    "approver_actor_reference through the authoritative actor boundary and verify their "
    "resolved actor identities are distinct; then confirm the opening is tied to the "
    "approved Job requirements and authorized headcount before recording accountable human "
    "requisition approval."
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
    if (
        not isinstance(value, str)
        or len(value) > 64
        or not _CODE_PATTERN.fullmatch(value)
    ):
        raise ValueError(
            f"{field_name} must be bounded two-or-more-word lower snake_case"
        )


def _validate_reference(value: str, prefix: str, field_name: str) -> None:
    """Require an expected namespace plus a canonical non-sentinel UUID suffix."""
    namespace = f"{prefix}:"
    if not isinstance(value, str) or len(value) > 160 or not value.startswith(namespace):
        raise ValueError(
            f"{field_name} must be an opaque {prefix}:<canonical-uuid> reference"
        )
    suffix = value[len(namespace) :]
    try:
        parsed = UUID(suffix)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(
            f"{field_name} must be an opaque {prefix}:<canonical-uuid> reference"
        ) from exc
    if str(parsed) != suffix or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(
            f"{field_name} must be an opaque {prefix}:<canonical-uuid> reference"
        )


def _validate_requirements_version_code(value: str) -> None:
    """Require a bounded numeric requirements-version identifier without semantic text."""
    if not isinstance(value, str) or not _REQUIREMENTS_VERSION_PATTERN.fullmatch(value):
        raise ValueError(
            "requirements_version_code must match requirements_version_<positive-integer>"
        )


def _canonical_timestamp(value: datetime) -> str:
    """Render an aware instant as deterministic UTC RFC 3339 text without precision loss."""
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True, repr=False)
class RequisitionReviewPacket:
    """Immutable evidence packet awaiting accountable human requisition approval."""

    tenant_record_id: str
    requisition_reference: str
    job_profile_reference: str
    job_requirements_reference: str
    job_requirements_digest: str
    requirements_version_code: str
    headcount_authorization_reference: str
    hiring_manager_actor_reference: str
    approver_actor_reference: str
    requested_opening_count: int
    purpose_code: str
    reason_code: str
    generated_at: datetime
    position_record_reference: str | None = None
    human_confirmation_required: bool = True
    review_state: str = _REVIEW_STATE
    next_action: str = _NEXT_ACTION

    def __post_init__(self) -> None:
        """Fail closed when direct construction drifts from the governed contract."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(self.requisition_reference, "requisition", "requisition_reference")
        _validate_reference(self.job_profile_reference, "job_profile", "job_profile_reference")
        _validate_reference(
            self.job_requirements_reference,
            "job_requirements",
            "job_requirements_reference",
        )
        if (
            not isinstance(self.job_requirements_digest, str)
            or not _DIGEST_PATTERN.fullmatch(self.job_requirements_digest)
        ):
            raise ValueError("job_requirements_digest must be lowercase SHA-256 hex")
        _validate_requirements_version_code(self.requirements_version_code)
        _validate_reference(
            self.headcount_authorization_reference,
            "headcount_authorization",
            "headcount_authorization_reference",
        )
        _validate_reference(
            self.hiring_manager_actor_reference,
            "actor",
            "hiring_manager_actor_reference",
        )
        _validate_reference(self.approver_actor_reference, "actor", "approver_actor_reference")
        if self.hiring_manager_actor_reference == self.approver_actor_reference:
            raise ValueError("hiring manager and approver must be different actor references")
        if type(self.requested_opening_count) is not int or not 1 <= self.requested_opening_count <= 100:
            raise ValueError("requested_opening_count must be an integer from 1 through 100")
        if self.position_record_reference is not None:
            _validate_reference(
                self.position_record_reference,
                "position_record",
                "position_record_reference",
            )
            if self.requested_opening_count != 1:
                raise ValueError("an exact Position seat can authorize exactly one opening")
        _validate_code(self.purpose_code, "purpose_code")
        if self.purpose_code != _REVIEW_PURPOSE:
            raise ValueError("purpose_code must remain requisition_review")
        _validate_code(self.reason_code, "reason_code")
        if self.reason_code not in _ALLOWED_REASON_CODES:
            raise ValueError("reason_code must use a reviewed non-sensitive requisition reason")
        _canonical_timestamp(self.generated_at)
        if self.human_confirmation_required is not True:
            raise ValueError("human confirmation is mandatory for requisition approval")
        if self.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain requires_human_approval")
        if self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed requisition-review instruction")

    def __repr__(self) -> str:
        """Return a fully redacted representation safe for routine logs and assertions."""
        return "RequisitionReviewPacket(<redacted>)"

    def canonical_json(self) -> str:
        """Return deterministic canonical JSON for immutable audit correlation."""
        payload = {
            "approver_actor_reference": self.approver_actor_reference,
            "generated_at": _canonical_timestamp(self.generated_at),
            "headcount_authorization_reference": self.headcount_authorization_reference,
            "hiring_manager_actor_reference": self.hiring_manager_actor_reference,
            "human_confirmation_required": self.human_confirmation_required,
            "job_profile_reference": self.job_profile_reference,
            "job_requirements_digest": self.job_requirements_digest,
            "job_requirements_reference": self.job_requirements_reference,
            "next_action": self.next_action,
            "position_record_reference": self.position_record_reference,
            "purpose_code": self.purpose_code,
            "reason_code": self.reason_code,
            "requested_opening_count": self.requested_opening_count,
            "requirements_version_code": self.requirements_version_code,
            "requisition_reference": self.requisition_reference,
            "review_state": self.review_state,
            "tenant_record_id": self.tenant_record_id,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical UTF-8 packet."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_requisition_review_packet(
    *,
    tenant_record_id: str,
    requisition_reference: str,
    job_profile_reference: str,
    job_requirements_reference: str,
    job_requirements_digest: str,
    requirements_version_code: str,
    headcount_authorization_reference: str,
    hiring_manager_actor_reference: str,
    approver_actor_reference: str,
    requested_opening_count: int,
    purpose_code: str,
    reason_code: str,
    generated_at: datetime,
    position_record_reference: str | None = None,
) -> RequisitionReviewPacket:
    """Build a governed opening packet that remains pending human approval."""
    return RequisitionReviewPacket(
        tenant_record_id=tenant_record_id,
        requisition_reference=requisition_reference,
        job_profile_reference=job_profile_reference,
        job_requirements_reference=job_requirements_reference,
        job_requirements_digest=job_requirements_digest,
        requirements_version_code=requirements_version_code,
        headcount_authorization_reference=headcount_authorization_reference,
        hiring_manager_actor_reference=hiring_manager_actor_reference,
        approver_actor_reference=approver_actor_reference,
        requested_opening_count=requested_opening_count,
        purpose_code=purpose_code,
        reason_code=reason_code,
        generated_at=generated_at,
        position_record_reference=position_record_reference,
    )
