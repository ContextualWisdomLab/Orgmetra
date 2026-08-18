from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta, timezone, tzinfo
from hashlib import sha256
import json

import pytest

from orgmetra_selection_monitoring import (
    SelectionOutcomeMonitoringPlan,
    build_selection_outcome_monitoring_plan,
)


DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
DIGEST_E = "e" * 64


def valid_kwargs() -> dict[str, object]:
    return {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "monitoring_plan_reference": "selection_monitoring_plan:plan-001",
        "job_profile_reference": "job_profile:job-001",
        "selection_process_reference": "selection_process:process-001",
        "population_snapshot_reference": "population_snapshot:population-001",
        "population_snapshot_digest": DIGEST_A,
        "outcome_snapshot_reference": "selection_outcome_snapshot:outcomes-001",
        "outcome_snapshot_digest": DIGEST_B,
        "protected_attribute_policy_reference": "protected_attribute_policy:policy-001",
        "protected_attribute_policy_digest": DIGEST_C,
        "small_sample_policy_reference": "small_sample_policy:policy-001",
        "small_sample_policy_digest": DIGEST_D,
        "statistical_plan_reference": "statistical_plan:plan-001",
        "statistical_plan_digest": DIGEST_E,
        "actor_reference": "actor:requester-001",
        "reviewer_reference": "actor:reviewer-001",
        "monitoring_start": date(2026, 1, 1),
        "monitoring_end": date(2026, 3, 31),
        "purpose_code": "selection_outcome_monitoring",
        "reason_code": "quarterly_selection_governance",
        "generated_at": datetime(2026, 4, 2, 8, 30, 0, 123456, tzinfo=timezone.utc),
    }


def build_valid() -> SelectionOutcomeMonitoringPlan:
    return build_selection_outcome_monitoring_plan(**valid_kwargs())


def test_builds_aggregate_only_human_review_plan() -> None:
    plan = build_valid()

    assert plan.analysis_scope == "total_selection_process_by_job"
    assert plan.contains_individual_records is False
    assert plan.human_confirmation_required is True
    assert plan.decision_authority == "human_review_only"
    assert plan.review_state == "requires_human_review"
    assert "authorized analyst" in plan.next_action
    assert "legal conclusion" in plan.next_action


def test_canonical_json_and_digest_are_deterministic_and_value_free() -> None:
    plan = build_valid()
    payload = json.loads(plan.canonical_json())

    assert payload["generated_at"] == "2026-04-02T08:30:00.123456Z"
    assert payload["monitoring_start"] == "2026-01-01"
    assert payload["monitoring_end"] == "2026-03-31"
    assert "candidate" not in payload
    assert "protected_attribute_value" not in payload
    assert plan.sha256_digest() == sha256(plan.canonical_json().encode("utf-8")).hexdigest()


def test_fractional_seconds_remain_distinct_evidence() -> None:
    first = build_valid()
    second = replace(
        first,
        generated_at=first.generated_at + timedelta(microseconds=1),
    )

    assert first.canonical_json() != second.canonical_json()
    assert first.sha256_digest() != second.sha256_digest()


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("tenant_record_id", "not-a-uuid"),
        ("tenant_record_id", "00000000-0000-0000-0000-000000000000"),
        ("tenant_record_id", "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF"),
        ("tenant_record_id", None),
    ],
)
def test_rejects_nonoperational_tenant_identity(field_name: str, value: object) -> None:
    kwargs = valid_kwargs()
    kwargs[field_name] = value
    with pytest.raises(ValueError, match="tenant_record_id"):
        build_selection_outcome_monitoring_plan(**kwargs)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("monitoring_plan_reference", "wrong:plan-001", "selection_monitoring_plan"),
        ("job_profile_reference", "job:job-001", "job_profile"),
        ("selection_process_reference", "selection:process-001", "selection_process"),
        ("population_snapshot_reference", "population:population-001", "population_snapshot"),
        ("outcome_snapshot_reference", "outcome:outcomes-001", "selection_outcome_snapshot"),
        (
            "protected_attribute_policy_reference",
            "policy:protected-001",
            "protected_attribute_policy",
        ),
        ("small_sample_policy_reference", "policy:small-001", "small_sample_policy"),
        ("statistical_plan_reference", "statistics:plan-001", "statistical_plan"),
        ("actor_reference", "person:requester-001", "actor"),
        ("reviewer_reference", "reviewer:reviewer-001", "actor"),
        ("actor_reference", "actor:", "actor"),
        ("actor_reference", 1, "actor"),
        ("actor_reference", "actor:" + "a" * 155, "actor"),
    ],
)
def test_rejects_bad_opaque_references(
    field_name: str,
    value: object,
    message: str,
) -> None:
    kwargs = valid_kwargs()
    kwargs[field_name] = value
    with pytest.raises(ValueError, match=message):
        build_selection_outcome_monitoring_plan(**kwargs)


@pytest.mark.parametrize(
    "field_name",
    [
        "population_snapshot_digest",
        "outcome_snapshot_digest",
        "protected_attribute_policy_digest",
        "small_sample_policy_digest",
        "statistical_plan_digest",
    ],
)
@pytest.mark.parametrize("value", ["A" * 64, "a" * 63, 1])
def test_rejects_malformed_digests(field_name: str, value: object) -> None:
    kwargs = valid_kwargs()
    kwargs[field_name] = value
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        build_selection_outcome_monitoring_plan(**kwargs)


def test_reviewer_must_be_distinct_from_requester() -> None:
    kwargs = valid_kwargs()
    kwargs["reviewer_reference"] = kwargs["actor_reference"]
    with pytest.raises(ValueError, match="different accountable actor"):
        build_selection_outcome_monitoring_plan(**kwargs)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("monitoring_start", datetime(2026, 1, 1, tzinfo=timezone.utc), "calendar date"),
        ("monitoring_end", datetime(2026, 3, 31, tzinfo=timezone.utc), "calendar date"),
        ("monitoring_start", "2026-01-01", "calendar date"),
        ("monitoring_end", "2026-03-31", "calendar date"),
    ],
)
def test_rejects_non_date_monitoring_bounds(
    field_name: str,
    value: object,
    message: str,
) -> None:
    kwargs = valid_kwargs()
    kwargs[field_name] = value
    with pytest.raises(ValueError, match=message):
        build_selection_outcome_monitoring_plan(**kwargs)


def test_rejects_reverse_monitoring_window() -> None:
    kwargs = valid_kwargs()
    kwargs["monitoring_start"] = date(2026, 4, 1)
    with pytest.raises(ValueError, match="must not precede"):
        build_selection_outcome_monitoring_plan(**kwargs)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("purpose_code", "selection_review", "selection_outcome_monitoring"),
        ("purpose_code", "SelectionOutcomeMonitoring", "lower snake_case"),
        ("purpose_code", "a_" + "b" * 64, "lower snake_case"),
        ("purpose_code", 1, "lower snake_case"),
        ("reason_code", "quarterly", "lower snake_case"),
        ("reason_code", "Quarterly_Review", "lower snake_case"),
        ("reason_code", 1, "lower snake_case"),
    ],
)
def test_rejects_bad_governance_codes(
    field_name: str,
    value: object,
    message: str,
) -> None:
    kwargs = valid_kwargs()
    kwargs[field_name] = value
    with pytest.raises(ValueError, match=message):
        build_selection_outcome_monitoring_plan(**kwargs)


class NullOffsetTz(tzinfo):
    def utcoffset(self, dt: datetime | None) -> None:
        return None

    def dst(self, dt: datetime | None) -> None:
        return None

    def tzname(self, dt: datetime | None) -> str:
        return "NULL"


@pytest.mark.parametrize(
    "value",
    [
        datetime(2026, 4, 2, 8, 30),
        "2026-04-02T08:30:00Z",
        1,
        datetime(2026, 4, 2, 8, 30).replace(tzinfo=NullOffsetTz()),
    ],
)
def test_rejects_nonaware_generation_time(value: object) -> None:
    kwargs = valid_kwargs()
    kwargs["generated_at"] = value
    with pytest.raises(ValueError, match="timezone-aware"):
        build_selection_outcome_monitoring_plan(**kwargs)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("analysis_scope", "component_only", "total_selection_process_by_job"),
        ("contains_individual_records", True, "aggregate-only"),
        ("contains_individual_records", 0, "aggregate-only"),
        ("human_confirmation_required", False, "human confirmation"),
        ("human_confirmation_required", 1, "human confirmation"),
        ("decision_authority", "automated", "human_review_only"),
        ("review_state", "approved", "requires_human_review"),
        ("next_action", "Compute adverse impact.", "governed monitoring instruction"),
    ],
)
def test_direct_constructor_and_replace_fail_closed(
    field_name: str,
    value: object,
    message: str,
) -> None:
    plan = build_valid()
    with pytest.raises(ValueError, match=message):
        replace(plan, **{field_name: value})


def test_frozen_plan_rejects_mutation() -> None:
    plan = build_valid()
    with pytest.raises(FrozenInstanceError):
        plan.review_state = "approved"


def test_timezone_is_normalized_without_losing_precision() -> None:
    kwargs = valid_kwargs()
    kwargs["generated_at"] = datetime(
        2026,
        4,
        2,
        17,
        30,
        0,
        654321,
        tzinfo=timezone(timedelta(hours=9)),
    )
    plan = build_selection_outcome_monitoring_plan(**kwargs)

    payload = json.loads(plan.canonical_json())
    assert payload["generated_at"] == "2026-04-02T08:30:00.654321Z"
