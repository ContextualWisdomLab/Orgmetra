"""Actor-separation and tenant-scope regressions for selection-monitoring evidence."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from orgmetra_selection_monitoring import build_selection_outcome_monitoring_plan


def _build(**overrides):
    """Build a valid monitoring plan with canonical opaque references."""
    values = {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "monitoring_plan_reference": "selection_monitoring_plan:10000000-0000-4000-8000-000000000001",
        "job_profile_reference": "job_profile:10000000-0000-4000-8000-000000000002",
        "selection_process_reference": "selection_process:10000000-0000-4000-8000-000000000003",
        "population_snapshot_reference": "population_snapshot:10000000-0000-4000-8000-000000000004",
        "population_snapshot_digest": "a" * 64,
        "outcome_snapshot_reference": "selection_outcome_snapshot:10000000-0000-4000-8000-000000000005",
        "outcome_snapshot_digest": "b" * 64,
        "protected_attribute_policy_reference": "protected_attribute_policy:10000000-0000-4000-8000-000000000006",
        "protected_attribute_policy_digest": "c" * 64,
        "small_sample_policy_reference": "small_sample_policy:10000000-0000-4000-8000-000000000007",
        "small_sample_policy_digest": "d" * 64,
        "statistical_plan_reference": "statistical_plan:10000000-0000-4000-8000-000000000008",
        "statistical_plan_digest": "e" * 64,
        "actor_reference": "actor:10000000-0000-4000-8000-000000000009",
        "reviewer_reference": "actor:10000000-0000-4000-8000-00000000000a",
        "monitoring_start": date(2026, 1, 1),
        "monitoring_end": date(2026, 3, 31),
        "purpose_code": "selection_outcome_monitoring",
        "reason_code": "quarterly_selection_governance",
        "generated_at": datetime(2026, 4, 2, 8, 30, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return build_selection_outcome_monitoring_plan(**values)


def test_requester_and_reviewer_require_authoritative_actor_separation() -> None:
    """Require both syntactic and authoritative actor separation before review."""
    with pytest.raises(ValueError, match="different accountable actor"):
        _build(reviewer_reference="actor:10000000-0000-4000-8000-000000000009")

    normalized_next_action = _build().next_action.lower()
    assert "actor_reference and reviewer_reference" in normalized_next_action
    assert "resolved actor identities are distinct" in normalized_next_action


def test_review_requires_every_reference_to_resolve_in_the_exact_tenant() -> None:
    """Prevent cross-tenant evidence mixing behind otherwise valid opaque references."""
    action = _build().next_action
    tenant_clause = "Within tenant_record_id, re-resolve every packet reference"
    actor_clause = "verify their resolved actor identities are distinct"
    job_clause = "verify Job scope"
    review_clause = "accountable human reviewer"

    assert tenant_clause in action
    assert action.index(tenant_clause) < action.index(actor_clause)
    assert action.index(actor_clause) < action.index(job_clause)
    assert action.index(job_clause) < action.index(review_clause)
