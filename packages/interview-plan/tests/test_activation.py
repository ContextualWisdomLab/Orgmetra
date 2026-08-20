"""Regression tests for executable, fail-closed structured-interview activation."""

from dataclasses import replace
from datetime import datetime, timezone
import json

import pytest

from orgmetra_interview_plan import (
    StructuredInterviewActivationReceipt,
    StructuredInterviewActivationVerification,
    activate_structured_interview_plan,
    build_structured_interview_plan,
)

TENANT = "10000000-0000-7000-8000-000000000001"
INTERVIEW_PLAN = "interview_plan:11111111-1111-4111-8111-111111111111"
REQUISITION = "requisition:22222222-2222-4222-8222-222222222222"
JOB_PROFILE = "job_profile:33333333-3333-4333-8333-333333333333"
JOB_ANALYSIS = "job_analysis:44444444-4444-4444-8444-444444444444"
QUESTION_SET = "question_set:55555555-5555-4555-8555-555555555555"
QUESTION_MAP = "question_competency_map:66666666-6666-4666-8666-666666666666"
RATING_ANCHOR = "rating_anchor:77777777-7777-4777-8777-777777777777"
COMPETENCY_A = "competency:88888888-8888-4888-8888-888888888888"
COMPETENCY_B = "competency:99999999-9999-4999-8999-999999999999"
PANEL_A = "actor:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
PANEL_B = "actor:cccccccc-cccc-4ccc-8ccc-cccccccccccc"
APPROVER = "actor:dddddddd-dddd-4ddd-8ddd-dddddddddddd"
AUTHORITY_EVIDENCE = "activation_verification:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
DIGEST_E = "e" * 64
APPROVED_AT = datetime(2026, 8, 21, 5, 0, 0, 123456, tzinfo=timezone.utc)


def plan():
    """Return a valid immutable plan for activation-boundary tests."""
    return build_structured_interview_plan(
        tenant_record_id=TENANT,
        interview_plan_reference=INTERVIEW_PLAN,
        requisition_reference=REQUISITION,
        job_profile_reference=JOB_PROFILE,
        job_analysis_reference=JOB_ANALYSIS,
        job_analysis_digest=DIGEST_A,
        question_set_reference=QUESTION_SET,
        question_set_digest=DIGEST_B,
        question_competency_map_reference=QUESTION_MAP,
        question_competency_map_digest=DIGEST_D,
        rating_anchor_reference=RATING_ANCHOR,
        rating_anchor_digest=DIGEST_C,
        competency_references=(COMPETENCY_A, COMPETENCY_B),
        panel_actor_references=(PANEL_A, PANEL_B),
        question_count=4,
        purpose_code="structured_interview_plan",
        reason_code="approved_requisition_interview",
        generated_at=datetime(2026, 8, 21, 4, 30, tzinfo=timezone.utc),
    )


def verification_for(candidate_plan, **changes):
    """Return matching authoritative host evidence, optionally mutated for failure tests."""
    values = dict(
        tenant_record_id=candidate_plan.tenant_record_id,
        interview_plan_reference=candidate_plan.interview_plan_reference,
        plan_digest=candidate_plan.sha256_digest(),
        approving_actor_reference=APPROVER,
        authority_evidence_reference=AUTHORITY_EVIDENCE,
        authority_evidence_digest=DIGEST_E,
    )
    values.update(changes)
    return StructuredInterviewActivationVerification(**values)


class AllowingAuthority:
    """Host fixture that returns evidence only after its authoritative checks succeed."""

    def __init__(self, verification):
        self.verification = verification
        self.calls = []

    def verify_activation(self, *, plan, approving_actor_reference):
        """Record the exact requested plan/actor and return authoritative evidence."""
        self.calls.append((plan, approving_actor_reference))
        return self.verification


class RejectingAuthority:
    """Host fixture representing a failed tenant/job/provenance/panel verification."""

    def verify_activation(self, *, plan, approving_actor_reference):
        """Fail closed instead of producing activation evidence."""
        raise PermissionError("authoritative activation checks failed")


def test_activation_executes_authority_and_returns_immutable_human_receipt():
    """Bind human confirmation to the exact plan and authoritative verification evidence."""
    candidate_plan = plan()
    authority = AllowingAuthority(verification_for(candidate_plan))

    receipt = activate_structured_interview_plan(
        plan=candidate_plan,
        authority=authority,
        approving_actor_reference=APPROVER,
        approved_at=APPROVED_AT,
    )

    assert authority.calls == [(candidate_plan, APPROVER)]
    payload = json.loads(receipt.canonical_json())
    assert payload["tenant_record_id"] == TENANT
    assert payload["interview_plan_reference"] == INTERVIEW_PLAN
    assert payload["plan_digest"] == candidate_plan.sha256_digest()
    assert payload["approving_actor_reference"] == APPROVER
    assert payload["authority_evidence_reference"] == AUTHORITY_EVIDENCE
    assert payload["authority_evidence_digest"] == DIGEST_E
    assert payload["purpose_code"] == "structured_interview_activation"
    assert payload["reason_code"] == "human_approved_plan_activation"
    assert payload["evidence_version"] == 1
    assert payload["human_confirmation"] is True
    assert payload["activation_state"] == "approved_for_use"
    assert payload["approved_at"] == "2026-08-21T05:00:00.123456Z"
    assert receipt.sha256_digest()
    assert repr(receipt) == "StructuredInterviewActivationReceipt(<redacted>)"


def test_authority_rejection_blocks_activation():
    """Propagate authoritative rejection so no activation receipt can be manufactured."""
    with pytest.raises(PermissionError, match="authoritative activation checks failed"):
        activate_structured_interview_plan(
            plan=plan(),
            authority=RejectingAuthority(),
            approving_actor_reference=APPROVER,
            approved_at=APPROVED_AT,
        )


def test_activation_rejects_non_verification_result():
    """Reject adapters that do not return the published verification contract."""
    class WrongAuthority:
        def verify_activation(self, *, plan, approving_actor_reference):
            return object()

    with pytest.raises(TypeError, match="StructuredInterviewActivationVerification"):
        activate_structured_interview_plan(
            plan=plan(),
            authority=WrongAuthority(),
            approving_actor_reference=APPROVER,
            approved_at=APPROVED_AT,
        )


@pytest.mark.parametrize(
    ("changes", "match"),
    [
        ({"tenant_record_id": "20000000-0000-7000-8000-000000000001"}, "different plan or actor"),
        ({"interview_plan_reference": "interview_plan:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}, "different plan or actor"),
        ({"plan_digest": "f" * 64}, "different plan or actor"),
        ({"approving_actor_reference": PANEL_A}, "different plan or actor"),
    ],
)
def test_activation_rejects_authority_evidence_for_other_scope(changes, match):
    """Reject otherwise well-shaped verification evidence bound to a different scope."""
    candidate_plan = plan()
    authority = AllowingAuthority(verification_for(candidate_plan, **changes))
    with pytest.raises(ValueError, match=match):
        activate_structured_interview_plan(
            plan=candidate_plan,
            authority=authority,
            approving_actor_reference=APPROVER,
            approved_at=APPROVED_AT,
        )


@pytest.mark.parametrize(
    ("changes", "match"),
    [
        ({"authority_evidence_reference": "activation_verification:human-readable"}, "authority_evidence_reference"),
        ({"authority_evidence_digest": "A" * 64}, "authority_evidence_digest"),
    ],
)
def test_activation_rejects_untrusted_authority_evidence_shape(changes, match):
    """Require opaque verification identity and deterministic evidence digest."""
    candidate_plan = plan()
    authority = AllowingAuthority(verification_for(candidate_plan, **changes))
    with pytest.raises(ValueError, match=match):
        activate_structured_interview_plan(
            plan=candidate_plan,
            authority=authority,
            approving_actor_reference=APPROVER,
            approved_at=APPROVED_AT,
        )


@pytest.mark.parametrize(
    ("field", "bad", "match"),
    [
        ("purpose_code", "other_purpose", "purpose_code"),
        ("reason_code", "other_reason", "reason_code"),
        ("evidence_version", True, "evidence_version"),
        ("evidence_version", 0, "evidence_version"),
        ("human_confirmation", False, "human confirmation"),
        ("activation_state", "pending", "activation_state"),
    ],
)
def test_direct_receipt_construction_fails_closed(field, bad, match):
    """Preserve fixed human-authority semantics under direct dataclass construction/replacement."""
    candidate_plan = plan()
    receipt = activate_structured_interview_plan(
        plan=candidate_plan,
        authority=AllowingAuthority(verification_for(candidate_plan)),
        approving_actor_reference=APPROVER,
        approved_at=APPROVED_AT,
    )
    with pytest.raises(ValueError, match=match):
        replace(receipt, **{field: bad})
