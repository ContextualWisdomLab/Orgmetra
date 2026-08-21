"""Executable human-approval boundary for governed structured-interview plans.

The authority adapter is owned by the Orgmetra host. It MUST return verification
only after re-resolving the plan inside the exact tenant, proving the
requisition-to-Job-to-job-analysis binding, verifying question/mapping/rating
provenance, resolving distinct panel actors, confirming panel eligibility and
training, and reviewing the exact approval instant carried into the receipt.
Any failed authoritative check must raise instead of returning verification evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from typing import Protocol

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


@dataclass(frozen=True, slots=True)
class StructuredInterviewActivationVerification:
    """Authoritative host evidence returned only after all activation checks pass."""

    tenant_record_id: str
    interview_plan_reference: str
    plan_digest: str
    approving_actor_reference: str
    authority_evidence_reference: str
    authority_evidence_digest: str


class StructuredInterviewActivationAuthority(Protocol):
    """Host contract that fail-closes unless every authoritative activation check passes."""

    def verify_activation(
        self,
        *,
        plan: StructuredInterviewPlan,
        approving_actor_reference: str,
        approved_at: datetime,
    ) -> StructuredInterviewActivationVerification:
        """Return exact-scope evidence only after reviewing the exact approval instant."""


@dataclass(frozen=True, slots=True, repr=False)
class StructuredInterviewActivationReceipt:
    """Immutable evidence that an accountable human activated one exact reviewed plan."""

    tenant_record_id: str
    interview_plan_reference: str
    plan_digest: str
    approving_actor_reference: str
    authority_evidence_reference: str
    authority_evidence_digest: str
    approved_at: object
    purpose_code: str = _PURPOSE_CODE
    reason_code: str = _REASON_CODE
    evidence_version: int = 1
    human_confirmation: bool = True
    activation_state: str = _ACTIVATION_STATE

    def __post_init__(self) -> None:
        """Reject forged, ambiguous, or weakened activation evidence."""
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

    def __repr__(self) -> str:
        """Return a redacted representation suitable for routine logs."""
        return "StructuredInterviewActivationReceipt(<redacted>)"

    def canonical_json(self) -> str:
        """Return deterministic canonical JSON for immutable audit correlation."""
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

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical UTF-8 activation receipt."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def activate_structured_interview_plan(
    *,
    plan: StructuredInterviewPlan,
    authority: StructuredInterviewActivationAuthority,
    approving_actor_reference: str,
    approved_at: datetime,
) -> StructuredInterviewActivationReceipt:
    """Activate one exact plan only after authoritative host verification succeeds.

    The authority implementation is responsible for the actual tenant-scoped
    re-resolution, relationship/provenance/panel checks, and review of the exact
    approval instant. This function rejects a non-contract result or evidence bound
    to a different plan/actor and emits a value-minimized immutable human-approval
    receipt only for the exact verified scope.
    """
    if type(plan) is not StructuredInterviewPlan:
        raise TypeError("plan must be a StructuredInterviewPlan")
    _canonical_timestamp(approved_at, "approved_at")
    if approved_at < plan.generated_at:
        raise ValueError("approved_at must not precede plan generated_at")
    _validate_reference(approving_actor_reference, "actor", "approving_actor_reference")
    verification = authority.verify_activation(
        plan=plan,
        approving_actor_reference=approving_actor_reference,
        approved_at=approved_at,
    )
    if not isinstance(verification, StructuredInterviewActivationVerification):
        raise TypeError("authority must return StructuredInterviewActivationVerification")

    _validate_reference(
        verification.authority_evidence_reference,
        "activation_verification",
        "authority_evidence_reference",
    )
    _validate_digest(verification.authority_evidence_digest, "authority_evidence_digest")

    expected_scope = (
        plan.tenant_record_id,
        plan.interview_plan_reference,
        plan.sha256_digest(),
        approving_actor_reference,
    )
    verified_scope = (
        verification.tenant_record_id,
        verification.interview_plan_reference,
        verification.plan_digest,
        verification.approving_actor_reference,
    )
    if verified_scope != expected_scope:
        raise ValueError("activation authority returned evidence for a different plan or actor")

    return StructuredInterviewActivationReceipt(
        tenant_record_id=plan.tenant_record_id,
        interview_plan_reference=plan.interview_plan_reference,
        plan_digest=plan.sha256_digest(),
        approving_actor_reference=approving_actor_reference,
        authority_evidence_reference=verification.authority_evidence_reference,
        authority_evidence_digest=verification.authority_evidence_digest,
        approved_at=approved_at,
    )
