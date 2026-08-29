"""Regression tests for activation-time mutation of governed interview plans."""

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
    plan,
)


class MutatingAuthority:
    """Authority fixture that rewrites the caller's frozen plan before returning evidence."""

    def verify_activation(self, *, plan, approving_actor_reference, approved_at):
        """Mutate one governed field and attempt to attest the rewritten artifact."""
        object.__setattr__(plan, "question_count", plan.question_count - 1)
        return StructuredInterviewActivationVerification(
            tenant_record_id=plan.tenant_record_id,
            interview_plan_reference=plan.interview_plan_reference,
            plan_digest=plan.sha256_digest(),
            approving_actor_reference=approving_actor_reference,
            authority_evidence_reference=AUTHORITY_EVIDENCE,
            authority_evidence_digest=DIGEST_E,
            approved_at=approved_at,
        )


def test_activation_rejects_plan_mutation_during_authority_verification():
    """Reject an authority that rewrites creation-bound plan evidence."""
    candidate_plan = plan()
    original_digest = candidate_plan.sha256_digest()

    with pytest.raises(ValueError, match="changed after plan issuance"):
        activate_structured_interview_plan(
            plan=candidate_plan,
            authority=MutatingAuthority(),
            approving_actor_reference=APPROVER,
            approved_at=APPROVED_AT,
        )

    with pytest.raises(ValueError, match="changed after plan issuance"):
        candidate_plan.sha256_digest()
    assert len(original_digest) == 64
