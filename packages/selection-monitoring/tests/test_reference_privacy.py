"""Privacy regressions for selection-monitoring opaque references."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone

import pytest

from orgmetra_selection_monitoring import build_selection_outcome_monitoring_plan


def _build(**overrides):
    """Build a valid packet using canonical UUID-backed opaque references."""
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


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        (
            "monitoring_plan_reference",
            "selection_monitoring_plan:Quarterly-Plan",
            "opaque selection_monitoring_plan",
        ),
        ("job_profile_reference", "job_profile:RN-ICU", "opaque job_profile"),
        (
            "selection_process_reference",
            "selection_process:hiring-2026",
            "opaque selection_process",
        ),
        (
            "protected_attribute_policy_reference",
            "protected_attribute_policy:race-gender",
            "opaque protected_attribute_policy",
        ),
        ("actor_reference", "actor:seonghobae", "opaque actor"),
        (
            "reviewer_reference",
            "actor:00000000-0000-0000-0000-000000000000",
            "opaque actor",
        ),
        (
            "population_snapshot_reference",
            "population_snapshot:FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF",
            "opaque population_snapshot",
        ),
    ],
)
def test_references_reject_value_bearing_sentinel_and_noncanonical_suffixes(
    field_name: str,
    value: object,
    message: str,
) -> None:
    """Reject reference suffixes that can leak values or evade opaque-ID rules."""
    with pytest.raises(ValueError, match=message):
        _build(**{field_name: value})

    packet = _build()
    with pytest.raises(ValueError, match=message):
        replace(packet, **{field_name: value})
