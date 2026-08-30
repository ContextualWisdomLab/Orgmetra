"""Regression tests for immutable selection-monitoring issuance evidence."""

from __future__ import annotations

import copy
from datetime import date, datetime, timezone
import pickle

import pytest

from orgmetra_selection_monitoring import build_selection_outcome_monitoring_plan
from orgmetra_selection_monitoring import plan as plan_module


_BASE_KWARGS: dict[str, object] = {
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
    "generated_at": datetime(2026, 4, 2, 8, 30, 0, 123456, tzinfo=timezone.utc),
}


def _build_plan():
    """Build one valid issued monitoring plan for tamper-evidence regressions."""
    return build_selection_outcome_monitoring_plan(**_BASE_KWARGS)


def test_post_issuance_rewrite_cannot_change_canonical_evidence() -> None:
    """Reject a valid-value rewrite after the governed plan has been issued."""
    plan = _build_plan()
    original = plan.canonical_json()

    object.__setattr__(plan, "population_snapshot_digest", "f" * 64)

    with pytest.raises(ValueError, match="changed after issuance"):
        plan.canonical_json()
    with pytest.raises(ValueError, match="changed after issuance"):
        plan.sha256_digest()
    assert original != plan_module._canonical_plan_json_unchecked(plan)


def test_missing_process_local_issuance_evidence_fails_closed() -> None:
    """Reject canonical export when process-local issuance evidence is unavailable."""
    plan = _build_plan()
    plan_module._discard_plan_seal(id(plan))

    with pytest.raises(ValueError, match="issuance evidence is unavailable"):
        plan.canonical_json()


def test_copied_or_serialized_plan_fails_closed_without_issuance_evidence() -> None:
    """Reject copies and serialized plans that bypass the original issuance seal."""
    plan = _build_plan()
    clones = (
        copy.copy(plan),
        copy.deepcopy(plan),
        pickle.loads(pickle.dumps(plan)),
    )

    for clone in clones:
        with pytest.raises(ValueError, match="issuance evidence is unavailable"):
            clone.canonical_json()


def test_reinitialization_cannot_renew_issuance_evidence_after_valid_value_rewrite() -> None:
    """Keep one live plan identity bound to its original construction evidence."""
    plan = _build_plan()
    original = plan.canonical_json()

    object.__setattr__(plan, "population_snapshot_digest", "f" * 64)

    with pytest.raises(ValueError, match="issuance evidence already exists"):
        plan.__post_init__()
    with pytest.raises(ValueError, match="changed after issuance"):
        plan.canonical_json()
    assert original != plan_module._canonical_plan_json_unchecked(plan)


def test_discarded_seal_cannot_be_renewed_after_valid_value_rewrite() -> None:
    """Do not let seal loss reset the live plan's single-use issuance lifecycle."""
    plan = _build_plan()
    original = plan.canonical_json()

    plan_module._discard_plan_seal(id(plan))
    object.__setattr__(plan, "population_snapshot_digest", "f" * 64)

    with pytest.raises(ValueError, match="issuance evidence already exists"):
        plan.__post_init__()
    with pytest.raises(ValueError, match="issuance evidence is unavailable"):
        plan.canonical_json()
    assert original != plan_module._canonical_plan_json_unchecked(plan)
