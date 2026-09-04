"""Regression coverage for the structured-interview activation plan type boundary."""

from datetime import datetime, timezone

import pytest

from orgmetra_interview_plan import activate_structured_interview_plan

TENANT = "10000000-0000-7000-8000-000000000001"
INTERVIEW_PLAN = "interview_plan:11111111-1111-4111-8111-111111111111"
APPROVER = "actor:dddddddd-dddd-4ddd-8ddd-dddddddddddd"
PLAN_DIGEST = "a" * 64


class DuckTypedPlan:
    """Mimic trusted plan fields without ever passing StructuredInterviewPlan validation."""

    tenant_record_id = TENANT
    interview_plan_reference = INTERVIEW_PLAN
    generated_at = datetime(2026, 8, 21, 4, 30, tzinfo=timezone.utc)

    def sha256_digest(self) -> str:
        """Return a plausible digest so the old duck-typed boundary can be exercised."""
        return PLAN_DIGEST


class RecordingAuthority:
    """Record whether authority work incorrectly runs for an untrusted plan-shaped object."""

    def __init__(self) -> None:
        """Initialize the authority call counter."""
        self.calls = 0

    def verify_activation(
        self,
        *,
        plan_canonical_json,
        plan_digest,
        approving_actor_reference,
        approved_at,
    ):
        """Fail loudly if a duck-typed plan reaches authoritative work."""
        self.calls += 1
        raise AssertionError("duck-typed plan reached authority")


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
