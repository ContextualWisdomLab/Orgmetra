"""Regression coverage for the structured-interview activation plan type boundary."""

from datetime import datetime, timezone

import pytest

from orgmetra_interview_plan import (
    StructuredInterviewActivationVerification,
    activate_structured_interview_plan,
)

TENANT = "10000000-0000-7000-8000-000000000001"
INTERVIEW_PLAN = "interview_plan:11111111-1111-4111-8111-111111111111"
APPROVER = "actor:dddddddd-dddd-4ddd-8ddd-dddddddddddd"
AUTHORITY_EVIDENCE = "activation_verification:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
PLAN_DIGEST = "a" * 64
AUTHORITY_DIGEST = "b" * 64


class DuckTypedPlan:
    """Mimic trusted plan fields without ever passing StructuredInterviewPlan validation."""

    tenant_record_id = TENANT
    interview_plan_reference = INTERVIEW_PLAN
    generated_at = datetime(2026, 8, 21, 4, 30, tzinfo=timezone.utc)

    def sha256_digest(self) -> str:
        """Return a plausible digest so the old duck-typed boundary can be exercised."""
        return PLAN_DIGEST


class RecordingAuthority:
    """Return internally consistent evidence while recording whether authority work ran."""

    def __init__(self) -> None:
        """Initialize the authority call counter."""
        self.calls = 0

    def verify_activation(self, *, plan, approving_actor_reference, approved_at):
        """Return evidence matching whatever validated activation request was supplied."""
        self.calls += 1
        return StructuredInterviewActivationVerification(
            tenant_record_id=plan.tenant_record_id,
            interview_plan_reference=plan.interview_plan_reference,
            plan_digest=plan.sha256_digest(),
            approving_actor_reference=approving_actor_reference,
            authority_evidence_reference=AUTHORITY_EVIDENCE,
            authority_evidence_digest=AUTHORITY_DIGEST,
            approved_at=approved_at,
        )


def test_activation_rejects_duck_typed_plan_before_authority_work():
    """Never let an unvalidated plan-shaped object reach the authoritative adapter."""
    authority = RecordingAuthority()

    with pytest.raises(TypeError, match="plan must be a StructuredInterviewPlan"):
        activate_structured_interview_plan(
            plan=DuckTypedPlan(),
            authority=authority,
            approving_actor_reference=APPROVER,
            approved_at=datetime(2026, 8, 21, 5, 0, tzinfo=timezone.utc),
        )

    assert authority.calls == 0
