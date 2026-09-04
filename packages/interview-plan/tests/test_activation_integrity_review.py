"""Regressions for current-head structured-interview activation integrity findings."""

from datetime import datetime, timedelta, timezone, tzinfo
from hashlib import sha256
import json

import pytest

from orgmetra_interview_plan import (
    StructuredInterviewActivationVerification,
    activate_structured_interview_plan,
)
from test_activation import (
    APPROVED_AT,
    APPROVER,
    AUTHORITY_EVIDENCE,
    DIGEST_E,
    AllowingAuthority,
    RejectingAuthority,
    plan,
    verification_for,
)

ALTERNATE_AUTHORITY_EVIDENCE = "activation_verification:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


class MutableOffsetTimezone(tzinfo):
    """UTC-offset provider whose offset can change after initial validation."""

    def __init__(self, offset_hours: int) -> None:
        """Store the mutable offset used by the adversarial approval-time fixture."""
        self.offset_hours = offset_hours

    def utcoffset(self, value):
        """Return the currently configured offset."""
        return timedelta(hours=self.offset_hours)

    def dst(self, value):
        """Return zero daylight-saving offset for deterministic test behavior."""
        return timedelta(0)

    def tzname(self, value):
        """Return a stable diagnostic name for the mutable test timezone."""
        return "MutableOffsetTimezone"


class UnknownOffsetTimezone(tzinfo):
    """Timezone fixture that cannot establish an authoritative UTC offset."""

    def utcoffset(self, value):
        """Return no offset so activation must fail before authority work."""
        return None

    def dst(self, value):
        """Return no daylight-saving value for the deliberately invalid fixture."""
        return None

    def tzname(self, value):
        """Return a stable diagnostic name for the invalid timezone fixture."""
        return "UnknownOffsetTimezone"


class ApprovalTimeMutatingAuthority:
    """Mutate caller-owned timezone state only after receiving the approval snapshot."""

    def __init__(self, source_timezone: MutableOffsetTimezone) -> None:
        """Keep the caller timezone so authority work can mutate it deterministically."""
        self.source_timezone = source_timezone

    def verify_activation(
        self,
        *,
        plan_canonical_json,
        plan_digest,
        approving_actor_reference,
        approved_at,
    ):
        """Require immutable built-in UTC evidence, then mutate the caller timezone."""
        assert approved_at.tzinfo is timezone.utc
        assert approved_at == APPROVED_AT
        self.source_timezone.offset_hours = 2
        payload = json.loads(plan_canonical_json)
        return StructuredInterviewActivationVerification(
            tenant_record_id=payload["tenant_record_id"],
            interview_plan_reference=payload["interview_plan_reference"],
            plan_digest=plan_digest,
            approving_actor_reference=approving_actor_reference,
            authority_evidence_reference=AUTHORITY_EVIDENCE,
            authority_evidence_digest=DIGEST_E,
            approved_at=approved_at,
        )


class DetachedPlanEvidenceAuthority:
    """Accept only immutable creation-bound plan evidence, never the caller's live plan object."""

    def __init__(self, verification: StructuredInterviewActivationVerification) -> None:
        """Store one matching verification result and initialize the call audit list."""
        self.verification = verification
        self.calls = []

    def verify_activation(
        self,
        *,
        plan_canonical_json: str,
        plan_digest: str,
        approving_actor_reference: str,
        approved_at: datetime,
    ) -> StructuredInterviewActivationVerification:
        """Prove authority work is bound to detached canonical bytes and their exact digest."""
        assert type(plan_canonical_json) is str
        payload = json.loads(plan_canonical_json)
        assert payload["question_count"] == 4
        assert plan_digest == sha256(plan_canonical_json.encode("utf-8")).hexdigest()
        self.calls.append((plan_canonical_json, plan_digest, approving_actor_reference, approved_at))
        return self.verification


def test_existing_plan_identity_cannot_renew_issuance_seal_after_mutation():
    """Repeated initialization must not legitimize changed bytes on one issued plan identity."""
    candidate_plan = plan()
    object.__setattr__(candidate_plan, "question_count", 3)

    with pytest.raises(ValueError, match="issuance evidence already exists"):
        candidate_plan.__post_init__()
    with pytest.raises(ValueError, match="changed after plan issuance"):
        candidate_plan.canonical_json()
    with pytest.raises(ValueError, match="changed after plan issuance"):
        activate_structured_interview_plan(
            plan=candidate_plan,
            authority=RejectingAuthority(),
            approving_actor_reference=APPROVER,
            approved_at=APPROVED_AT,
        )


def test_existing_receipt_identity_cannot_renew_issuance_seal_after_mutation():
    """Receipt revalidation must not create new issuance evidence after factory issuance."""
    candidate_plan = plan()
    receipt = activate_structured_interview_plan(
        plan=candidate_plan,
        authority=AllowingAuthority(verification_for(candidate_plan)),
        approving_actor_reference=APPROVER,
        approved_at=APPROVED_AT,
    )
    original_canonical = receipt.canonical_json()
    object.__setattr__(receipt, "plan_digest", "f" * 64)

    receipt.__post_init__()

    with pytest.raises(ValueError, match="changed after activation receipt issuance"):
        receipt.canonical_json()
    object.__setattr__(receipt, "plan_digest", json.loads(original_canonical)["plan_digest"])
    assert receipt.canonical_json() == original_canonical


def test_activation_rejects_naive_approval_time_before_authority_work():
    """A caller must supply an aware approval instant before authoritative review."""
    with pytest.raises(ValueError, match="approved_at must be an exact timezone-aware datetime"):
        activate_structured_interview_plan(
            plan=plan(),
            authority=RejectingAuthority(),
            approving_actor_reference=APPROVER,
            approved_at=datetime(2026, 8, 21, 5, 0, 0),
        )


def test_activation_rejects_approval_time_with_unknown_offset():
    """An aware-looking timestamp without a concrete UTC offset is not auditable evidence."""
    with pytest.raises(ValueError, match="approved_at must be an exact timezone-aware datetime"):
        activate_structured_interview_plan(
            plan=plan(),
            authority=RejectingAuthority(),
            approving_actor_reference=APPROVER,
            approved_at=datetime(2026, 8, 21, 5, 0, 0, tzinfo=UnknownOffsetTimezone()),
        )


def test_activation_freezes_mutable_timezone_before_authority_and_receipt():
    """Authority work cannot make one approved_at value represent two UTC instants."""
    mutable_timezone = MutableOffsetTimezone(1)
    caller_time = datetime(2026, 8, 21, 6, 0, 0, 123456, tzinfo=mutable_timezone)
    candidate_plan = plan()

    receipt = activate_structured_interview_plan(
        plan=candidate_plan,
        authority=ApprovalTimeMutatingAuthority(mutable_timezone),
        approving_actor_reference=APPROVER,
        approved_at=caller_time,
    )

    payload = json.loads(receipt.canonical_json())
    assert payload["approved_at"] == "2026-08-21T05:00:00.123456Z"
    assert receipt.approved_at.tzinfo is timezone.utc
    assert receipt.approved_at == APPROVED_AT


def test_activation_authority_receives_detached_creation_bound_plan_evidence():
    """Do not expose a live plan that can be changed and restored while authority work runs."""
    candidate_plan = plan()
    verification = verification_for(candidate_plan)
    authority = DetachedPlanEvidenceAuthority(verification)

    receipt = activate_structured_interview_plan(
        plan=candidate_plan,
        authority=authority,
        approving_actor_reference=APPROVER,
        approved_at=APPROVED_AT,
    )

    assert len(authority.calls) == 1
    plan_canonical_json, plan_digest, actor_reference, approved_at = authority.calls[0]
    assert json.loads(plan_canonical_json)["interview_plan_reference"] == candidate_plan.interview_plan_reference
    assert plan_digest == candidate_plan.sha256_digest()
    assert actor_reference == APPROVER
    assert approved_at == APPROVED_AT
    assert receipt.plan_digest == plan_digest


def test_verification_contract_cannot_be_rewritten_with_object_setattr():
    """Authority evidence must be runtime-immutable so field reads cannot mix revisions."""
    verification = verification_for(plan())

    with pytest.raises((AttributeError, TypeError)):
        object.__setattr__(verification, "authority_evidence_reference", ALTERNATE_AUTHORITY_EVIDENCE)

    assert verification.authority_evidence_reference == AUTHORITY_EVIDENCE


def test_verification_contract_explicitly_binds_reviewed_approval_time():
    """Authority verification must expose the exact approval instant it attests."""
    field_names = set(StructuredInterviewActivationVerification._fields)

    assert "approved_at" in field_names


def test_activation_rejects_verification_for_different_approval_time():
    """Do not accept authority evidence that attests a different approval instant."""
    candidate_plan = plan()
    verification = verification_for(
        candidate_plan,
        approved_at=APPROVED_AT + timedelta(seconds=1),
    )

    with pytest.raises(ValueError, match="different plan or actor or approval time"):
        activate_structured_interview_plan(
            plan=candidate_plan,
            authority=AllowingAuthority(verification),
            approving_actor_reference=APPROVER,
            approved_at=APPROVED_AT,
        )
