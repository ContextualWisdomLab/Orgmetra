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


def direct_receipt() -> StructuredInterviewActivationReceipt:
    """Return one syntactically valid receipt that never crossed the authority factory."""
    return StructuredInterviewActivationReceipt(
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


def test_activation_receipt_cannot_be_minted_without_verified_factory_path():
    """Directly constructed values cannot export authoritative activation evidence."""
    receipt = direct_receipt()

    with pytest.raises(ValueError, match="changed after activation receipt issuance"):
        receipt.canonical_json()
    with pytest.raises(ValueError, match="changed after activation receipt issuance"):
        receipt.sha256_digest()


def test_receipt_issuance_capabilities_are_not_module_attributes():
    """Do not publish callables or secrets that can mint verified receipt evidence."""
    forbidden_names = (
        "_ACTIVATION_RECEIPT_ISSUANCE_TOKEN",
        "_PROCESS_ACTIVATION_RECEIPT_SEAL_KEY",
        "_ACTIVATION_RECEIPT_SEALS",
        "_register_activation_receipt_seal",
        "_seal_activation_receipt",
        "_discard_activation_receipt_seal",
        "_authoritative_activation_receipt_seal",
    )

    assert all(not hasattr(activation_module, name) for name in forbidden_names)


def test_private_constructor_argument_cannot_mint_verified_receipt_directly():
    """Constructor-private-looking keywords must never act as issuance authority."""
    with pytest.raises(TypeError, match="_issuance_token"):
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
            _issuance_token=object(),
        )


def test_issued_activation_receipt_cannot_be_replaced_with_unverified_scope():
    """Dataclass replacement creates unissued values rather than reusable trust evidence."""
    candidate_plan = plan()
    receipt = activate_structured_interview_plan(
        plan=candidate_plan,
        authority=AllowingAuthority(verification_for(candidate_plan)),
        approving_actor_reference=APPROVER,
        approved_at=APPROVED_AT,
    )

    replacement = replace(receipt, plan_digest="b" * 64)

    with pytest.raises(ValueError, match="changed after activation receipt issuance"):
        replacement.canonical_json()
    with pytest.raises(ValueError, match="changed after activation receipt issuance"):
        replacement.sha256_digest()
    assert receipt.canonical_json()


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
