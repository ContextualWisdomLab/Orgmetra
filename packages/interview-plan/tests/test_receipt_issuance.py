"""Regression tests for authoritative structured-interview receipt issuance."""

from dataclasses import replace
from datetime import datetime, timezone

import pytest

import orgmetra_interview_plan.activation as activation_module
from orgmetra_interview_plan import (
    StructuredInterviewActivationReceipt,
    activate_structured_interview_plan,
)
from test_activation import APPROVED_AT, APPROVER, AllowingAuthority, plan, verification_for


def test_activation_receipt_cannot_be_minted_without_verified_factory_path():
    """Reject valid-looking approval evidence that never crossed the authority boundary."""
    with pytest.raises(TypeError, match="activate_structured_interview_plan"):
        StructuredInterviewActivationReceipt(
            tenant_record_id="10000000-0000-7000-8000-000000000001",
            interview_plan_reference="interview_plan:11111111-1111-4111-8111-111111111111",
            plan_digest="a" * 64,
            approving_actor_reference="actor:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
            authority_evidence_reference=(
                "activation_verification:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
            ),
            authority_evidence_digest="e" * 64,
            approved_at=datetime(2026, 8, 21, 5, 0, tzinfo=timezone.utc),
        )


def test_issued_activation_receipt_cannot_be_replaced_with_unverified_scope():
    """Reject dataclass replacement that would reuse issuance proof for changed scope."""
    candidate_plan = plan()
    receipt = activate_structured_interview_plan(
        plan=candidate_plan,
        authority=AllowingAuthority(verification_for(candidate_plan)),
        approving_actor_reference=APPROVER,
        approved_at=APPROVED_AT,
    )

    with pytest.raises(TypeError, match="activate_structured_interview_plan"):
        replace(receipt, plan_digest="b" * 64)


def test_issued_activation_receipt_rejects_post_issuance_rewrite():
    """Reject low-level rewriting of already-issued canonical activation evidence."""
    candidate_plan = plan()
    receipt = activate_structured_interview_plan(
        plan=candidate_plan,
        authority=AllowingAuthority(verification_for(candidate_plan)),
        approving_actor_reference=APPROVER,
        approved_at=APPROVED_AT,
    )
    object.__setattr__(receipt, "plan_digest", "b" * 64)

    with pytest.raises(ValueError, match="changed after activation receipt issuance"):
        receipt.canonical_json()
    with pytest.raises(ValueError, match="changed after activation receipt issuance"):
        receipt.sha256_digest()


def test_missing_process_local_activation_receipt_issuance_evidence_fails_closed():
    """Reject canonical export when process-local issuance evidence is unavailable."""
    candidate_plan = plan()
    receipt = activate_structured_interview_plan(
        plan=candidate_plan,
        authority=AllowingAuthority(verification_for(candidate_plan)),
        approving_actor_reference=APPROVER,
        approved_at=APPROVED_AT,
    )
    activation_module._discard_activation_receipt_seal(id(receipt))

    with pytest.raises(ValueError, match="changed after activation receipt issuance"):
        receipt.canonical_json()
