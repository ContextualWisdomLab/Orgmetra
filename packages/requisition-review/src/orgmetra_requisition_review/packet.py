"""PII-minimized requisition-review packet contracts.

The packet is approval evidence for opening a recruiting workflow, not a candidate
selection decision. It binds one planned opening to an authoritative Job, optional
Position seat, job-requirements evidence, accountable actors, and governance metadata
without copying candidate or employee PII.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import re
from typing import NamedTuple
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


class _RequisitionReviewSnapshot(NamedTuple):
    """Hold one immutable read of every field that can enter canonical evidence."""

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
    position_record_reference: str | None
    human_confirmation_required: bool
    review_state: str
    next_action: str


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
    """Require exact bounded descriptive lower snake_case governance text."""
    if (
        type(value) is not str
        or len(value) > 64
        or not _CODE_PATTERN.fullmatch(value)
    ):
        raise ValueError(
            f"{field_name} must be bounded two-or-more-word lower snake_case"
        )


def _validate_reference(value: str, prefix: str, field_name: str) -> None:
    """Require exact text with the expected namespace and operational UUID suffix."""
    namespace = f"{prefix}:"
    if type(value) is not str or len(value) > 160 or not value.startswith(namespace):
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
    if type(value) is not str or not _REQUIREMENTS_VERSION_PATTERN.fullmatch(value):
        raise ValueError(
            "requirements_version_code must match requirements_version_<positive-integer>"
        )


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
    try:
        return (value.replace(tzinfo=None) - offset).replace(tzinfo=timezone.utc)
    except OverflowError as exc:
        raise ValueError("generated_at must be an exact timezone-aware datetime") from exc


def _canonical_timestamp(value: datetime) -> str:
    """Render only a previously detached built-in UTC instant as RFC 3339 text."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError("generated_at must be an exact timezone-aware datetime")
    return value.isoformat().replace("+00:00", "Z")


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
        snapshot = self._snapshot()
        self._validate_governance_fields(snapshot)
        object.__setattr__(self, "generated_at", _freeze_timestamp(snapshot.generated_at))
        self._validate_human_review_fields(snapshot)

    def _snapshot(self) -> _RequisitionReviewSnapshot:
        """Read each evidence field once so validation and emission share one state."""
        return _RequisitionReviewSnapshot(
            tenant_record_id=self.tenant_record_id,
            requisition_reference=self.requisition_reference,
            job_profile_reference=self.job_profile_reference,
            job_requirements_reference=self.job_requirements_reference,
            job_requirements_digest=self.job_requirements_digest,
            requirements_version_code=self.requirements_version_code,
            headcount_authorization_reference=self.headcount_authorization_reference,
            hiring_manager_actor_reference=self.hiring_manager_actor_reference,
            approver_actor_reference=self.approver_actor_reference,
            requested_opening_count=self.requested_opening_count,
            purpose_code=self.purpose_code,
            reason_code=self.reason_code,
            generated_at=self.generated_at,
            position_record_reference=self.position_record_reference,
            human_confirmation_required=self.human_confirmation_required,
            review_state=self.review_state,
            next_action=self.next_action,
        )

    def _validate_governance_fields(self, snapshot: _RequisitionReviewSnapshot) -> None:
        """Validate one captured governance state before it can become audit evidence."""
        _validate_operational_uuid(snapshot.tenant_record_id, "tenant_record_id")
        _validate_reference(
            snapshot.requisition_reference,
            "requisition",
            "requisition_reference",
        )
        _validate_reference(
            snapshot.job_profile_reference,
            "job_profile",
            "job_profile_reference",
        )
        _validate_reference(
            snapshot.job_requirements_reference,
            "job_requirements",
            "job_requirements_reference",
        )
        if (
            type(snapshot.job_requirements_digest) is not str
            or not _DIGEST_PATTERN.fullmatch(snapshot.job_requirements_digest)
        ):
            raise ValueError("job_requirements_digest must be lowercase SHA-256 hex")
        _validate_requirements_version_code(snapshot.requirements_version_code)
        _validate_reference(
            snapshot.headcount_authorization_reference,
            "headcount_authorization",
            "headcount_authorization_reference",
        )
        _validate_reference(
            snapshot.hiring_manager_actor_reference,
            "actor",
            "hiring_manager_actor_reference",
        )
        _validate_reference(
            snapshot.approver_actor_reference,
            "actor",
            "approver_actor_reference",
        )
        if snapshot.hiring_manager_actor_reference == snapshot.approver_actor_reference:
            raise ValueError("hiring manager and approver must be different actor references")
        if (
            type(snapshot.requested_opening_count) is not int
            or not 1 <= snapshot.requested_opening_count <= 100
        ):
            raise ValueError("requested_opening_count must be an integer from 1 through 100")
        if snapshot.position_record_reference is not None:
            _validate_reference(
                snapshot.position_record_reference,
                "position_record",
                "position_record_reference",
            )
            if snapshot.requested_opening_count != 1:
                raise ValueError("an exact Position seat can authorize exactly one opening")
        _validate_code(snapshot.purpose_code, "purpose_code")
        if snapshot.purpose_code != _REVIEW_PURPOSE:
            raise ValueError("purpose_code must remain requisition_review")
        _validate_code(snapshot.reason_code, "reason_code")
        if snapshot.reason_code not in _ALLOWED_REASON_CODES:
            raise ValueError("reason_code must use a reviewed non-sensitive requisition reason")

    def _validate_human_review_fields(self, snapshot: _RequisitionReviewSnapshot) -> None:
        """Keep one captured state pending the accountable human-review contract."""
        if snapshot.human_confirmation_required is not True:
            raise ValueError("human confirmation is mandatory for requisition approval")
        if type(snapshot.review_state) is not str or snapshot.review_state != _REVIEW_STATE:
            raise ValueError("review_state must remain requires_human_approval")
        if type(snapshot.next_action) is not str or snapshot.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed requisition-review instruction")

    def __repr__(self) -> str:
        """Return a fully redacted representation safe for routine logs and assertions."""
        return "RequisitionReviewPacket(<redacted>)"

    def canonical_json(self) -> str:
        """Return deterministic canonical JSON for immutable audit correlation."""
        snapshot = self._snapshot()
        self._validate_governance_fields(snapshot)
        generated_at = _canonical_timestamp(snapshot.generated_at)
        self._validate_human_review_fields(snapshot)
        payload = {
            "approver_actor_reference": snapshot.approver_actor_reference,
            "generated_at": generated_at,
            "headcount_authorization_reference": snapshot.headcount_authorization_reference,
            "hiring_manager_actor_reference": snapshot.hiring_manager_actor_reference,
            "human_confirmation_required": snapshot.human_confirmation_required,
            "job_profile_reference": snapshot.job_profile_reference,
            "job_requirements_digest": snapshot.job_requirements_digest,
            "job_requirements_reference": snapshot.job_requirements_reference,
            "next_action": snapshot.next_action,
            "position_record_reference": snapshot.position_record_reference,
            "purpose_code": snapshot.purpose_code,
            "reason_code": snapshot.reason_code,
            "requested_opening_count": snapshot.requested_opening_count,
            "requirements_version_code": snapshot.requirements_version_code,
            "requisition_reference": snapshot.requisition_reference,
            "review_state": snapshot.review_state,
            "tenant_record_id": snapshot.tenant_record_id,
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
