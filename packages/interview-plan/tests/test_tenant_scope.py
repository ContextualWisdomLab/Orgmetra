"""Tenant-scope regressions for governed structured-interview activation."""

from orgmetra_interview_plan import StructuredInterviewPlan
from test_plan import values


def test_activation_requires_authoritative_tenant_and_job_scope_resolution() -> None:
    """Do not infer tenant ownership or Job linkage from opaque references and digests."""
    action = StructuredInterviewPlan(**values()).next_action

    assert "Within tenant_record_id, re-resolve every plan reference" in action
    assert "verify the requisition-to-Job-to-job-analysis binding" in action
    assert "verify question-set, question-to-competency mapping, and rating-anchor provenance" in action


def test_activation_requires_authoritative_panel_actor_separation() -> None:
    """Do not treat distinct actor-reference strings as distinct authoritative people."""
    action = StructuredInterviewPlan(**values()).next_action

    assert "re-resolve every panel_actor_reference" in action
    assert "prove the resolved panel actor identities are distinct" in action
    assert "verify panel eligibility and training" in action
