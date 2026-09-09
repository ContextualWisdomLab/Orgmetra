"""Privacy regressions for aggregate selection-outcome monitoring evidence."""

from dataclasses import replace
from datetime import date, datetime, timezone

import pytest

from orgmetra_selection_monitoring import build_selection_outcome_monitoring_plan


def _build():
    """Build one valid aggregate monitoring plan for privacy-focused assertions."""
    return build_selection_outcome_monitoring_plan(
        tenant_record_id="11111111-1111-4111-8111-111111111111",
        monitoring_plan_reference="selection_monitoring_plan:10000000-0000-4000-8000-000000000001",
        job_profile_reference="job_profile:10000000-0000-4000-8000-000000000002",
        selection_process_reference="selection_process:10000000-0000-4000-8000-000000000003",
        population_snapshot_reference="population_snapshot:10000000-0000-4000-8000-000000000004",
        population_snapshot_digest="a" * 64,
        outcome_snapshot_reference="selection_outcome_snapshot:10000000-0000-4000-8000-000000000005",
        outcome_snapshot_digest="b" * 64,
        protected_attribute_policy_reference="protected_attribute_policy:10000000-0000-4000-8000-000000000006",
        protected_attribute_policy_digest="c" * 64,
        small_sample_policy_reference="small_sample_policy:10000000-0000-4000-8000-000000000007",
        small_sample_policy_digest="d" * 64,
        statistical_plan_reference="statistical_plan:10000000-0000-4000-8000-000000000008",
        statistical_plan_digest="e" * 64,
        actor_reference="actor:10000000-0000-4000-8000-000000000009",
        reviewer_reference="actor:10000000-0000-4000-8000-00000000000a",
        monitoring_start=date(2026, 1, 1),
        monitoring_end=date(2026, 3, 31),
        purpose_code="selection_outcome_monitoring",
        reason_code="quarterly_selection_governance",
        generated_at=datetime(2026, 4, 2, 8, 30, 0, 123456, tzinfo=timezone.utc),
    )


@pytest.mark.parametrize(
    "reason_code",
    ["jane_doe", "salary_120000", "race_gender_review", "candidate_alice_smith"],
)
def test_reason_code_rejects_personal_or_value_bearing_free_form_codes(reason_code: str) -> None:
    """Prevent governance reason metadata from becoming an individual-data channel."""
    plan = _build()
    with pytest.raises(ValueError):
        replace(plan, reason_code=reason_code)


def test_repr_redacts_selection_monitoring_correlations() -> None:
    """Keep Job, actor, policy, and statistical correlations out of routine repr output."""
    plan = _build()
    rendered = repr(plan)
    assert rendered == "SelectionOutcomeMonitoringPlan(<redacted>)"
    for sensitive in (
        plan.job_profile_reference,
        plan.actor_reference,
        plan.protected_attribute_policy_reference,
        plan.statistical_plan_digest,
    ):
        assert sensitive not in rendered
