"""Executable contract for authoritative performance-goal plan activation."""

from dataclasses import replace
from datetime import datetime, timezone
import json
from uuid import uuid4

import pytest

from orgmetra_performance_goal_plan import (
    PerformanceGoalPlanActivationReceipt,
    PerformanceGoalPlanActivationVerification,
    PerformanceGoalPlanPacket,
    activate_performance_goal_plan,
    build_performance_goal_plan_packet,
)

TENANT = "01890f3d-4d6a-7cc0-8a9d-9a83bb1cc001"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64


def ref(prefix: str) -> str:
    """Return one canonical UUIDv4 namespaced reference."""
    return f"{prefix}:{uuid4()}"


def packet() -> PerformanceGoalPlanPacket:
    """Build one reviewed goal-plan packet eligible for authority verification."""
    return build_performance_goal_plan_packet(
        tenant_record_id=TENANT,
        performance_goal_plan_reference=ref("performance_goal_plan"),
        employment_record_reference=ref("employment_record"),
        job_profile_reference=ref("job_profile"),
        performance_cycle_reference=ref("performance_cycle"),
        goal_set_digest=DIGEST_A,
        measurement_definition_digest=DIGEST_B,
        goal_count=3,
        feedback_cadence_code="monthly_check_in",
        requester_reference=ref("actor"),
        reviewer_reference=ref("actor"),
        purpose_code="performance_goal_plan_review",
        reason_code="goal_plan_activation_review",
        generated_at=datetime(2026, 8, 23, 1, 0, tzinfo=timezone.utc),
    )


class Authority:
    """Deterministic authority fixture for exact-scope activation tests."""

    def __init__(self, plan: PerformanceGoalPlanPacket) -> None:
        """Bind the fixture to one reviewed plan."""
        self.plan = plan
        self.calls = 0
        self.mutate_plan = False
        self.scope_override: dict[str, object] = {}

    def verify_activation(
        self,
        *,
        plan: PerformanceGoalPlanPacket,
        approving_actor_reference: str,
        approved_at: datetime,
    ) -> PerformanceGoalPlanActivationVerification:
        """Return authority evidence for the exact reviewed plan scope."""
        self.calls += 1
        if self.mutate_plan:
            object.__setattr__(plan, "goal_count", 4)
        values: dict[str, object] = {
            "tenant_record_id": self.plan.tenant_record_id,
            "performance_goal_plan_reference": self.plan.performance_goal_plan_reference,
            "employment_record_reference": self.plan.employment_record_reference,
            "job_profile_reference": self.plan.job_profile_reference,
            "performance_cycle_reference": self.plan.performance_cycle_reference,
            "goal_set_digest": self.plan.goal_set_digest,
            "measurement_definition_digest": self.plan.measurement_definition_digest,
            "feedback_cadence_code": self.plan.feedback_cadence_code,
            "approving_actor_reference": approving_actor_reference,
            "approved_at": approved_at,
            "verified_at": datetime(2026, 8, 23, 1, 2, tzinfo=timezone.utc),
            "authority_evidence_reference": ref("performance_goal_authority"),
            "authority_evidence_digest": DIGEST_C,
        }
        values.update(self.scope_override)
        return PerformanceGoalPlanActivationVerification(**values)  # type: ignore[arg-type]


def test_activation_emits_value_minimized_authority_bound_receipt() -> None:
    """A reviewed plan activates only through exact-scope human authority evidence."""
    item = packet()
    authority = Authority(item)
    receipt = activate_performance_goal_plan(
        item,
        approving_actor_reference=item.reviewer_reference,
        approved_at=datetime(2026, 8, 23, 1, 1, tzinfo=timezone.utc),
        authority=authority,
    )
    document = json.loads(receipt.canonical_json())
    assert authority.calls == 1
    assert repr(receipt) == "PerformanceGoalPlanActivationReceipt(<redacted>)"
    assert document["tenant_record_id"] == TENANT
    assert document["plan_digest"] == item.sha256_digest()
    assert document["activation_state"] == "authoritatively_activated"
    assert document["rating_authority"] == "not_authorized_for_performance_rating"
    assert document["employment_decision_authority"] == "not_authorized_for_employment_decision"
    assert document["approved_at"] == "2026-08-23T01:01:00Z"
    assert document["activated_at"] == "2026-08-23T01:02:00Z"
    assert "goal_text" not in document
    assert "performance_rating" not in document
    assert len(receipt.sha256_digest()) == 64


def test_activation_rejects_non_plan_before_authority_work() -> None:
    """Duck-typed objects cannot enter the high-impact activation authority boundary."""
    item = packet()
    authority = Authority(item)
    with pytest.raises(TypeError):
        activate_performance_goal_plan(
            object(),  # type: ignore[arg-type]
            approving_actor_reference=item.reviewer_reference,
            approved_at=datetime(2026, 8, 23, 1, 1, tzinfo=timezone.utc),
            authority=authority,
        )
    assert authority.calls == 0


def test_activation_requires_the_reviewed_human_actor() -> None:
    """Activation cannot substitute a different actor for the reviewed accountable human."""
    item = packet()
    authority = Authority(item)
    with pytest.raises(ValueError, match="reviewed reviewer"):
        activate_performance_goal_plan(
            item,
            approving_actor_reference=ref("actor"),
            approved_at=datetime(2026, 8, 23, 1, 1, tzinfo=timezone.utc),
            authority=authority,
        )
    assert authority.calls == 0


def test_activation_rejects_approval_before_review_evidence_exists() -> None:
    """Human approval cannot predate the reviewed plan evidence it activates."""
    item = packet()
    authority = Authority(item)
    with pytest.raises(ValueError, match="approved_at"):
        activate_performance_goal_plan(
            item,
            approving_actor_reference=item.reviewer_reference,
            approved_at=datetime(2026, 8, 23, 0, 59, tzinfo=timezone.utc),
            authority=authority,
        )
    assert authority.calls == 0


def test_activation_rejects_non_verification_authority_result() -> None:
    """Authority results must use the exact governed verification runtime type."""
    item = packet()

    class BadAuthority:
        """Return a non-governed authority result."""

        def verify_activation(self, **kwargs: object) -> object:
            """Return a forged result object."""
            return object()

    with pytest.raises(TypeError, match="verification"):
        activate_performance_goal_plan(
            item,
            approving_actor_reference=item.reviewer_reference,
            approved_at=datetime(2026, 8, 23, 1, 1, tzinfo=timezone.utc),
            authority=BadAuthority(),
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("tenant_record_id", "01890f3d-4d6a-7cc0-8a9d-9a83bb1cc999"),
        ("goal_set_digest", "d" * 64),
        ("feedback_cadence_code", "quarterly_check_in"),
        ("approving_actor_reference", None),
    ],
)
def test_activation_rejects_authority_scope_drift(field_name: str, value: object) -> None:
    """Authority evidence must match the exact pre-call reviewed plan scope."""
    item = packet()
    authority = Authority(item)
    authority.scope_override[field_name] = (
        ref("actor") if field_name == "approving_actor_reference" else value
    )
    with pytest.raises(ValueError, match="scope"):
        activate_performance_goal_plan(
            item,
            approving_actor_reference=item.reviewer_reference,
            approved_at=datetime(2026, 8, 23, 1, 1, tzinfo=timezone.utc),
            authority=authority,
        )


def test_activation_rejects_plan_mutation_across_authority_call() -> None:
    """Authority work cannot rewrite the reviewed plan and then activate the rewrite."""
    item = packet()
    authority = Authority(item)
    authority.mutate_plan = True
    with pytest.raises(ValueError):
        activate_performance_goal_plan(
            item,
            approving_actor_reference=item.reviewer_reference,
            approved_at=datetime(2026, 8, 23, 1, 1, tzinfo=timezone.utc),
            authority=authority,
        )


def test_verification_rejects_invalid_chronology_and_governance() -> None:
    """Authority verification is itself a strict value-minimized governed artifact."""
    item = packet()
    authority = Authority(item)
    valid = authority.verify_activation(
        plan=item,
        approving_actor_reference=item.reviewer_reference,
        approved_at=datetime(2026, 8, 23, 1, 1, tzinfo=timezone.utc),
    )
    assert repr(valid) == "PerformanceGoalPlanActivationVerification(<redacted>)"
    with pytest.raises(ValueError, match="verified_at"):
        replace(valid, verified_at=datetime(2026, 8, 23, 1, 0, tzinfo=timezone.utc))
    with pytest.raises(ValueError):
        replace(valid, authority_evidence_digest="not-a-digest")
    with pytest.raises(ValueError):
        replace(valid, activation_state="auto_activated")


def test_receipt_cannot_be_constructed_or_rewritten_outside_activation() -> None:
    """Issued activation evidence cannot be minted or replaced without authority verification."""
    item = packet()
    authority = Authority(item)
    receipt = activate_performance_goal_plan(
        item,
        approving_actor_reference=item.reviewer_reference,
        approved_at=datetime(2026, 8, 23, 1, 1, tzinfo=timezone.utc),
        authority=authority,
    )
    with pytest.raises(TypeError):
        replace(receipt, plan_digest="d" * 64)
    object.__setattr__(receipt, "plan_digest", "d" * 64)
    with pytest.raises(ValueError, match="altered"):
        receipt.canonical_json()

    with pytest.raises(TypeError):
        PerformanceGoalPlanActivationReceipt(
            activation_reference=ref("performance_goal_activation"),
            tenant_record_id=item.tenant_record_id,
            performance_goal_plan_reference=item.performance_goal_plan_reference,
            plan_digest=item.sha256_digest(),
            approving_actor_reference=item.reviewer_reference,
            approved_at=datetime(2026, 8, 23, 1, 1, tzinfo=timezone.utc),
            activated_at=datetime(2026, 8, 23, 1, 2, tzinfo=timezone.utc),
            authority_evidence_reference=ref("performance_goal_authority"),
            authority_evidence_digest=DIGEST_C,
        )
