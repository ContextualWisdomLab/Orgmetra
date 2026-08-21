"""Regression for authoritative structured-interview approval-time binding."""

from datetime import datetime, timezone

from orgmetra_interview_plan import (
    StructuredInterviewActivationVerification,
    activate_structured_interview_plan,
    build_structured_interview_plan,
)

TENANT = "10000000-0000-7000-8000-000000000001"
INTERVIEW_PLAN = "interview_plan:11111111-1111-4111-8111-111111111111"
APPROVER = "actor:dddddddd-dddd-4ddd-8ddd-dddddddddddd"
AUTHORITY_EVIDENCE = "activation_verification:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
APPROVED_AT = datetime(2026, 8, 21, 5, 0, 0, 123456, tzinfo=timezone.utc)


def _plan():
    """Return one valid immutable interview plan for the approval-time boundary."""
    return build_structured_interview_plan(
        tenant_record_id=TENANT,
        interview_plan_reference=INTERVIEW_PLAN,
        requisition_reference="requisition:22222222-2222-4222-8222-222222222222",
        job_profile_reference="job_profile:33333333-3333-4333-8333-333333333333",
        job_analysis_reference="job_analysis:44444444-4444-4444-8444-444444444444",
        job_analysis_digest="a" * 64,
        question_set_reference="question_set:55555555-5555-4555-8555-555555555555",
        question_set_digest="b" * 64,
        question_competency_map_reference=(
            "question_competency_map:66666666-6666-4666-8666-666666666666"
        ),
        question_competency_map_digest="c" * 64,
        rating_anchor_reference="rating_anchor:77777777-7777-4777-8777-777777777777",
        rating_anchor_digest="d" * 64,
        competency_references=("competency:88888888-8888-4888-8888-888888888888",),
        panel_actor_references=(
            "actor:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            "actor:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        ),
        question_count=2,
        purpose_code="structured_interview_plan",
        reason_code="approved_requisition_interview",
        generated_at=datetime(2026, 8, 21, 4, 30, tzinfo=timezone.utc),
    )


class TimestampRecordingAuthority:
    """Require the candidate approval instant to cross the authoritative boundary."""

    def __init__(self, candidate_plan) -> None:
        """Capture the plan and initialize the authoritative-call audit list."""
        self.candidate_plan = candidate_plan
        self.calls = []

    def verify_activation(self, *, plan, approving_actor_reference, approved_at):
        """Record the exact approval instant before returning matching evidence."""
        self.calls.append((plan, approving_actor_reference, approved_at))
        return StructuredInterviewActivationVerification(
            tenant_record_id=plan.tenant_record_id,
            interview_plan_reference=plan.interview_plan_reference,
            plan_digest=plan.sha256_digest(),
            approving_actor_reference=approving_actor_reference,
            authority_evidence_reference=AUTHORITY_EVIDENCE,
            authority_evidence_digest="e" * 64,
        )


def test_activation_sends_approval_time_through_authoritative_verification():
    """Do not mint approved evidence from a timestamp the authority never reviewed."""
    candidate_plan = _plan()
    authority = TimestampRecordingAuthority(candidate_plan)

    receipt = activate_structured_interview_plan(
        plan=candidate_plan,
        authority=authority,
        approving_actor_reference=APPROVER,
        approved_at=APPROVED_AT,
    )

    assert authority.calls == [(candidate_plan, APPROVER, APPROVED_AT)]
    assert "2026-08-21T05:00:00.123456Z" in receipt.canonical_json()
