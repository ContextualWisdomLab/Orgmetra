"""Regression tests for activation-time mutation of governed interview plans."""

import json

from orgmetra_interview_plan import (
    StructuredInterviewActivationVerification,
    activate_structured_interview_plan,
)
from test_activation import (
    APPROVED_AT,
    APPROVER,
    AUTHORITY_EVIDENCE,
    DIGEST_E,
    plan,
)


class RestoringPlanAliasAuthority:
    """Authority fixture retaining a live plan alias while reviewing detached plan bytes."""

    def __init__(self, live_plan) -> None:
        """Keep an adversarial alias so change-and-restore behavior is deterministic."""
        self.live_plan = live_plan
        self.reviewed_question_count = None

    def verify_activation(
        self,
        *,
        plan_canonical_json,
        plan_digest,
        approving_actor_reference,
        approved_at,
    ):
        """Mutate and restore the live alias while attesting only detached canonical evidence."""
        original_question_count = self.live_plan.question_count
        object.__setattr__(self.live_plan, "question_count", original_question_count - 1)
        payload = json.loads(plan_canonical_json)
        self.reviewed_question_count = payload["question_count"]
        object.__setattr__(self.live_plan, "question_count", original_question_count)
        return StructuredInterviewActivationVerification(
            tenant_record_id=payload["tenant_record_id"],
            interview_plan_reference=payload["interview_plan_reference"],
            plan_digest=plan_digest,
            approving_actor_reference=approving_actor_reference,
            authority_evidence_reference=AUTHORITY_EVIDENCE,
            authority_evidence_digest=DIGEST_E,
            approved_at=approved_at,
        )


def test_activation_detaches_plan_evidence_from_authority_time_aba_mutation():
    """A live plan change-and-restore cycle cannot alter what the authority reviews or approves."""
    candidate_plan = plan()
    original_digest = candidate_plan.sha256_digest()
    authority = RestoringPlanAliasAuthority(candidate_plan)

    receipt = activate_structured_interview_plan(
        plan=candidate_plan,
        authority=authority,
        approving_actor_reference=APPROVER,
        approved_at=APPROVED_AT,
    )

    assert authority.reviewed_question_count == 4
    assert candidate_plan.sha256_digest() == original_digest
    assert receipt.plan_digest == original_digest
