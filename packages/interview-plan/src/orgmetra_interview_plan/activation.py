"""Executable human-approval boundary for governed structured-interview plans.

The authority adapter is owned by the Orgmetra host. It MUST return verification
only after re-resolving detached creation-bound plan evidence inside the exact
tenant, proving the requisition-to-Job-to-job-analysis binding, verifying
question/mapping/rating provenance, resolving distinct panel actors, confirming
panel eligibility and training, and reviewing the exact approval instant carried
into the receipt. Any failed authoritative check must raise instead of returning
verification evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import hmac
import json
import secrets
from threading import RLock
from typing import NamedTuple, Protocol
from weakref import finalize

from .plan import (
    StructuredInterviewPlan,
    _canonical_timestamp,
    _validate_code,
    _validate_digest,
    _validate_operational_uuid,
    _validate_reference,
)

_PURPOSE_CODE = "structured_interview_activation"
_REASON_CODE = "human_approved_plan_activation"
_ACTIVATION_STATE = "approved_for_use"
_MAX_EVIDENCE_VERSION = 2_147_483_647
_ACTIVATION_RECEIPT_ISSUANCE_TOKEN = object()
_PROCESS_ACTIVATION_RECEIPT_SEAL_KEY = secrets.token_bytes(32)
_ACTIVATION_RECEIPT_SEALS: dict[int, str] = {}
_ACTIVATION_RECEIPT_SEALS_LOCK = RLock()


def _snapshot_utc_datetime(value: datetime, field_name: str) -> datetime:
    """Detach one caller-owned aware datetime into an immutable built-in UTC instant."""
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError(f"{field_name} must be an exact timezone-aware datetime")
    offset = value.utcoffset()
    if type(offset) is not timedelta:
        raise ValueError(f"{field_name} must be an exact timezone-aware datetime")
    local_naive = value.replace(tzinfo=None)
    return (local_naive - offset).replace(tzinfo=timezone.utc)


def _discard_activation_receipt_seal(receipt_id: int) -> None:
    """Discard process-local activation issuance evidence after receipt collection."""
    with _ACTIVATION_RECEIPT_SEALS_LOCK:
        _ACTIVATION_RECEIPT_SEALS.pop(receipt_id, None)


def _register_activation_receipt_seal(receipt: object, seal: str) -> None:
    """Bind one live receipt identity to evidence outside receipt-writable slots."""
    receipt_id = id(receipt)
    with _ACTIVATION_RECEIPT_SEALS_LOCK:
        _ACTIVATION_RECEIPT_SEALS[receipt_id] = seal
    finalize(receipt, _discard_activation_receipt_seal, receipt_id)


def _authoritative_activation_receipt_seal(receipt: object) -> str | None:
    """Return process-local issuance evidence without trusting receipt-owned state."""
    with _ACTIVATION_RECEIPT_SEALS_LOCK:
        return _ACTIVATION_RECEIPT_SEALS.get(id(receipt))


def _seal_activation_receipt(payload_json: str) -> str:
    """Bind one process-local activation issuance to exact canonical payload bytes."""
    return hmac.new(
        _PROCESS_ACTIVATION_RECEIPT_SEAL_KEY,
        payload_json.encode("utf-8"),
        "sha256",
    ).hexdigest()


class StructuredInterviewActivationVerification(NamedTuple):
    """Runtime-immutable authoritative host evidence returned after activation checks pass."""

    tenant_record_id: str
    interview_plan_reference: str
    plan_digest: str
    approving_actor_reference: str
    authority_evidence_reference: str
    authority_evidence_digest: str
    approved_at: datetime

    def __repr__(self) -> str:
        """Return a redacted representation suitable for routine logs and failures."""
        return "StructuredInterviewActivationVerification(<redacted>)"


class StructuredInterviewActivationAuthority(Protocol):
    """Host contract that fail-closes unless every authoritative activation check passes."""

    def verify_activation(
        self,
        *,
        plan_canonical_json: str,
        plan_digest: str,
        approving_actor_reference: str,
        approved_at: datetime,
    ) -> StructuredInterviewActivationVerification:
        """Verify detached creation-bound plan bytes and return exact-scope evidence."""


@dataclass(frozen=True, slots=True, repr=False, weakref_slot=True)
class StructuredInterviewActivationReceipt:
    """Immutable evidence that an accountable human activated one exact reviewed plan."""

    tenant_record_id: str
    interview_plan_reference: str
    plan_digest: str
    approving_actor_reference: str
    authority_evidence_reference: str
    authority_evidence_digest: str
    approved_at: datetime
    purpose_code: str = _PURPOSE_CODE
    reason_code: str = _REASON_CODE
    evidence_version: int = 1
    human_confirmation: bool = True
    activation_state: str = _ACTIVATION_STATE
    _issuance_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Reject forged, ambiguous, weakened, or non-authoritatively issued evidence."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.interview_plan_reference,
            "interview_plan",
            "interview_plan_reference",
        )
        _validate_digest(self.plan_digest, "plan_digest")
        _validate_reference(
            self.approving_actor_reference,
            "actor",
            "approving_actor_reference",
        )
        _validate_reference(
            self.authority_evidence_reference,
            "activation_verification",
            "authority_evidence_reference",
        )
        _validate_digest(self.authority_evidence_digest, "authority_evidence_digest")
        _canonical_timestamp(self.approved_at, "approved_at")
        _validate_code(self.purpose_code, "purpose_code")
        if self.purpose_code != _PURPOSE_CODE:
            raise ValueError("purpose_code must remain structured_interview_activation")
        _validate_code(self.reason_code, "reason_code")
        if self.reason_code != _REASON_CODE:
            raise ValueError("reason_code must remain human_approved_plan_activation")
        if type(self.evidence_version) is not int or not 1 <= self.evidence_version <= _MAX_EVIDENCE_VERSION:
            raise ValueError("evidence_version must be an integer from 1 through 2147483647")
        if self.human_confirmation is not True:
            raise ValueError("human confirmation is mandatory for interview-plan activation")
        if self.activation_state != _ACTIVATION_STATE:
            raise ValueError("activation_state must remain approved_for_use")
        if self._issuance_token is not _ACTIVATION_RECEIPT_ISSUANCE_TOKEN:
            raise TypeError(
                "StructuredInterviewActivationReceipt can only be issued by "
                "activate_structured_interview_plan"
            )
        _register_activation_receipt_seal(
            self,
            _seal_activation_receipt(self._canonical_json_unchecked()),
        )

    def __repr__(self) -> str:
        """Return a redacted representation suitable for routine logs."""
        return "StructuredInterviewActivationReceipt(<redacted>)"

    def _canonical_json_unchecked(self) -> str:
        """Render canonical activation bytes without process-local issuance state."""
        payload = {
            "activation_state": self.activation_state,
            "approved_at": _canonical_timestamp(self.approved_at, "approved_at"),
            "approving_actor_reference": self.approving_actor_reference,
            "authority_evidence_digest": self.authority_evidence_digest,
            "authority_evidence_reference": self.authority_evidence_reference,
            "evidence_version": self.evidence_version,
            "human_confirmation": self.human_confirmation,
            "interview_plan_reference": self.interview_plan_reference,
            "plan_digest": self.plan_digest,
            "purpose_code": self.purpose_code,
            "reason_code": self.reason_code,
            "tenant_record_id": self.tenant_record_id,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def canonical_json(self) -> str:
        """Return creation-bound canonical JSON for immutable audit correlation."""
        canonical = self._canonical_json_unchecked()
        authoritative_seal = _authoritative_activation_receipt_seal(self)
        if (
            type(authoritative_seal) is not str
            or not hmac.compare_digest(
                _seal_activation_receipt(canonical),
                authoritative_seal,
            )
        ):
            raise ValueError(
                "structured interview activation receipt changed after activation receipt issuance"
            )
        return canonical

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact creation-bound activation receipt."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def activate_structured_interview_plan(
    *,
    plan: StructuredInterviewPlan,
    authority: StructuredInterviewActivationAuthority,
    approving_actor_reference: str,
    approved_at: datetime,
) -> StructuredInterviewActivationReceipt:
    """Activate one exact plan only after authoritative host verification succeeds.

    The authority implementation is responsible for tenant-scoped re-resolution,
    relationship/provenance/panel checks, and review of the exact approval instant.
    It receives only detached creation-bound canonical plan bytes plus their digest,
    never the caller's live plan object. Authority results are runtime-immutable tuple
    evidence; this function validates those exact values and emits a value-minimized
    human-approval receipt only for the exact verified scope.
    """
    if type(plan) is not StructuredInterviewPlan:
        raise TypeError("plan must be a StructuredInterviewPlan")
    approved_at_snapshot = _snapshot_utc_datetime(approved_at, "approved_at")
    _validate_reference(approving_actor_reference, "actor", "approving_actor_reference")

    plan_canonical_json = plan.canonical_json()
    plan_payload = json.loads(plan_canonical_json)
    plan_generated_at = datetime.fromisoformat(plan_payload["generated_at"].replace("Z", "+00:00"))
    if approved_at_snapshot < plan_generated_at:
        raise ValueError("approved_at must not precede plan generated_at")
    plan_digest = sha256(plan_canonical_json.encode("utf-8")).hexdigest()
    plan_tenant_record_id = plan_payload["tenant_record_id"]
    interview_plan_reference = plan_payload["interview_plan_reference"]

    verification = authority.verify_activation(
        plan_canonical_json=plan_canonical_json,
        plan_digest=plan_digest,
        approving_actor_reference=approving_actor_reference,
        approved_at=approved_at_snapshot,
    )
    plan.canonical_json()
    if type(verification) is not StructuredInterviewActivationVerification:
        raise TypeError("authority must return StructuredInterviewActivationVerification")

    (
        verified_tenant_record_id,
        verified_interview_plan_reference,
        verified_plan_digest,
        verified_approving_actor_reference,
        verified_authority_evidence_reference,
        verified_authority_evidence_digest,
        verification_approved_at,
    ) = verification
    verified_approved_at = _snapshot_utc_datetime(verification_approved_at, "approved_at")

    _validate_operational_uuid(verified_tenant_record_id, "tenant_record_id")
    _validate_reference(
        verified_interview_plan_reference,
        "interview_plan",
        "interview_plan_reference",
    )
    _validate_digest(verified_plan_digest, "plan_digest")
    _validate_reference(
        verified_approving_actor_reference,
        "actor",
        "approving_actor_reference",
    )
    _validate_reference(
        verified_authority_evidence_reference,
        "activation_verification",
        "authority_evidence_reference",
    )
    _validate_digest(verified_authority_evidence_digest, "authority_evidence_digest")

    expected_scope = (
        plan_tenant_record_id,
        interview_plan_reference,
        plan_digest,
        approving_actor_reference,
        approved_at_snapshot,
    )
    verified_scope = (
        verified_tenant_record_id,
        verified_interview_plan_reference,
        verified_plan_digest,
        verified_approving_actor_reference,
        verified_approved_at,
    )
    if verified_scope != expected_scope:
        raise ValueError(
            "activation authority returned evidence for a different plan or actor or approval time"
        )

    receipt = StructuredInterviewActivationReceipt(
        tenant_record_id=plan_tenant_record_id,
        interview_plan_reference=interview_plan_reference,
        plan_digest=plan_digest,
        approving_actor_reference=approving_actor_reference,
        authority_evidence_reference=verified_authority_evidence_reference,
        authority_evidence_digest=verified_authority_evidence_digest,
        approved_at=approved_at_snapshot,
        _issuance_token=_ACTIVATION_RECEIPT_ISSUANCE_TOKEN,
    )
    object.__setattr__(receipt, "_issuance_token", None)
    return receipt
