from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from orgmetra_selection_monitoring import build_selection_outcome_monitoring_plan


def _build(**overrides):
    values = {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "monitoring_plan_reference": "selection_monitoring_plan:plan-001",
        "job_profile_reference": "job_profile:job-001",
        "selection_process_reference": "selection_process:process-001",
        "population_snapshot_reference": "population_snapshot:population-001",
        "population_snapshot_digest": "a" * 64,
        "outcome_snapshot_reference": "selection_outcome_snapshot:outcomes-001",
        "outcome_snapshot_digest": "b" * 64,
        "protected_attribute_policy_reference": "protected_attribute_policy:policy-001",
        "protected_attribute_policy_digest": "c" * 64,
        "small_sample_policy_reference": "small_sample_policy:policy-001",
        "small_sample_policy_digest": "d" * 64,
        "statistical_plan_reference": "statistical_plan:plan-001",
        "statistical_plan_digest": "e" * 64,
        "actor_reference": "actor:requester-001",
        "reviewer_reference": "actor:reviewer-001",
        "monitoring_start": date(2026, 1, 1),
        "monitoring_end": date(2026, 3, 31),
        "purpose_code": "selection_outcome_monitoring",
        "reason_code": "quarterly_selection_governance",
        "generated_at": datetime(2026, 4, 2, 8, 30, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return build_selection_outcome_monitoring_plan(**values)


def test_requester_and_reviewer_require_authoritative_actor_separation() -> None:
    with pytest.raises(ValueError, match="different accountable actor"):
        _build(reviewer_reference="actor:requester-001")

    normalized_next_action = _build().next_action.lower()
    assert "actor_reference and reviewer_reference" in normalized_next_action
    assert "resolved actor identities are distinct" in normalized_next_action
