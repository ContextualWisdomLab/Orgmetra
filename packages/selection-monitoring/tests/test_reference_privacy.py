"""Privacy regressions for selection-monitoring opaque references."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone

import pytest

from orgmetra_selection_monitoring import (
    SelectionOutcomeMonitoringPlan,
    build_selection_outcome_monitoring_plan,
)

UUID1_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
UUID7_TENANT = "10000000-0000-7000-8000-000000000001"


def _valid_values(**overrides) -> dict[str, object]:
    """Return valid constructor values for every governed monitoring field."""
    values: dict[str, object] = {
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
    return values


def _build(**overrides) -> SelectionOutcomeMonitoringPlan:
    """Build a valid packet through the public builder."""
    return build_selection_outcome_monitoring_plan(**_valid_values(**overrides))  # type: ignore[arg-type]


def _direct(**overrides) -> SelectionOutcomeMonitoringPlan:
    """Construct a packet directly to prove dataclass invariants cannot be bypassed."""
    return SelectionOutcomeMonitoringPlan(**_valid_values(**overrides))  # type: ignore[arg-type]


def test_authoritative_uuid7_tenant_identity_is_accepted_by_all_construction_paths() -> None:
    """The monitoring leaf must accept tenant UUIDs already valid in authoritative core."""
    packet = _build(tenant_record_id=UUID7_TENANT)
    replaced = replace(_build(), tenant_record_id=UUID7_TENANT)
    direct = _direct(tenant_record_id=UUID7_TENANT)

    assert packet.tenant_record_id == UUID7_TENANT
    assert replaced.tenant_record_id == UUID7_TENANT
    assert direct.tenant_record_id == UUID7_TENANT


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
    """Reject unsafe reference suffixes through builder, replace, and direct construction."""
    with pytest.raises(ValueError, match=message):
        _build(**{field_name: value})

    packet = _build()
    with pytest.raises(ValueError, match=message):
        replace(packet, **{field_name: value})

    with pytest.raises(ValueError, match=message):
        _direct(**{field_name: value})


@pytest.mark.parametrize(
    ("field_name", "prefix"),
    [
        ("monitoring_plan_reference", "selection_monitoring_plan"),
        ("job_profile_reference", "job_profile"),
        ("selection_process_reference", "selection_process"),
        ("population_snapshot_reference", "population_snapshot"),
        ("outcome_snapshot_reference", "selection_outcome_snapshot"),
        ("protected_attribute_policy_reference", "protected_attribute_policy"),
        ("small_sample_policy_reference", "small_sample_policy"),
        ("statistical_plan_reference", "statistical_plan"),
        ("actor_reference", "actor"),
        ("reviewer_reference", "actor"),
    ],
)
def test_uuid1_trust_reference_is_rejected_by_all_construction_paths(
    field_name: str,
    prefix: str,
) -> None:
    """UUIDv1 timestamp/node metadata must never enter an aggregate trust-reference field."""
    value = f"{prefix}:{UUID1_ID}"
    with pytest.raises(ValueError, match=field_name):
        _build(**{field_name: value})

    with pytest.raises(ValueError, match=field_name):
        replace(_build(), **{field_name: value})

    with pytest.raises(ValueError, match=field_name):
        _direct(**{field_name: value})
