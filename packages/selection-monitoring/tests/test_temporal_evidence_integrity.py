"""Regression tests for exact temporal types in immutable monitoring evidence."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone, tzinfo

import pytest

from orgmetra_selection_monitoring import build_selection_outcome_monitoring_plan


class ForgedDate(date):
    """Date subclass able to forge the canonical evidence rendering."""

    def isoformat(self) -> str:
        """Return a date different from the underlying business date."""
        return "2099-12-31"


class ForgedDateTime(datetime):
    """Datetime subclass able to forge the canonical evidence rendering."""

    def astimezone(self, tz=None):  # type: ignore[no-untyped-def]
        """Keep the subclass alive across the UTC normalization call."""
        return self

    def isoformat(self, *args, **kwargs) -> str:  # type: ignore[no-untyped-def]
        """Return an instant different from the underlying evidence instant."""
        return "2099-12-31T23:59:59+00:00"


class MutableTimezone(tzinfo):
    """Timezone provider whose offset can change after packet issuance."""

    def __init__(self, offset: timedelta) -> None:
        """Store one caller-controlled offset."""
        self.offset = offset

    def utcoffset(self, dt: datetime | None) -> timedelta:
        """Return the current mutable offset."""
        return self.offset

    def dst(self, dt: datetime | None) -> timedelta:
        """Expose no daylight-saving adjustment."""
        return timedelta(0)

    def tzname(self, dt: datetime | None) -> str:
        """Return a stable diagnostic timezone name."""
        return "MutableTimezone"


class RaisingTimezone(tzinfo):
    """Timezone provider that raises while resolving its UTC offset."""

    def utcoffset(self, dt: datetime | None) -> timedelta:
        """Raise caller-controlled behavior at the trust boundary."""
        raise RuntimeError("provider failure")

    def dst(self, dt: datetime | None) -> timedelta:
        """Expose no daylight-saving adjustment."""
        return timedelta(0)


def valid_kwargs() -> dict[str, object]:
    """Return one otherwise valid aggregate-monitoring plan input."""
    return {
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


@pytest.mark.parametrize("field_name", ["monitoring_start", "monitoring_end"])
def test_rejects_date_subclasses_that_can_forge_canonical_business_time(field_name: str) -> None:
    """Do not let subclass methods rewrite immutable business-time evidence."""
    kwargs = valid_kwargs()
    kwargs[field_name] = ForgedDate(2026, 1, 1 if field_name == "monitoring_start" else 3)

    with pytest.raises(ValueError, match="calendar date"):
        build_selection_outcome_monitoring_plan(**kwargs)


def test_rejects_datetime_subclasses_that_can_forge_canonical_recorded_time() -> None:
    """Do not let subclass methods rewrite immutable recorded-time evidence."""
    kwargs = valid_kwargs()
    kwargs["generated_at"] = ForgedDateTime(2026, 4, 2, 8, 30, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="timezone-aware"):
        build_selection_outcome_monitoring_plan(**kwargs)


def test_detaches_mutable_timezone_from_immutable_generated_time() -> None:
    """Do not let a timezone provider rewrite canonical evidence after issuance."""
    provider = MutableTimezone(timedelta(hours=9))
    kwargs = valid_kwargs()
    kwargs["generated_at"] = datetime(2026, 4, 2, 17, 30, tzinfo=provider)

    plan = build_selection_outcome_monitoring_plan(**kwargs)
    before = plan.canonical_json()
    provider.offset = timedelta(hours=-7)

    assert plan.canonical_json() == before
    assert plan.generated_at == datetime(2026, 4, 2, 8, 30, tzinfo=timezone.utc)
    assert plan.generated_at.tzinfo is timezone.utc


def test_rejects_future_generated_time() -> None:
    """Do not seal a monitoring plan for a system time that has not occurred."""
    kwargs = valid_kwargs()
    kwargs["generated_at"] = datetime(2099, 1, 1, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="generated_at must not be in the future"):
        build_selection_outcome_monitoring_plan(**kwargs)


def test_normalizes_timezone_provider_failure() -> None:
    """Do not leak arbitrary timezone-provider exceptions across the evidence boundary."""
    kwargs = valid_kwargs()
    kwargs["generated_at"] = datetime(2026, 4, 2, 8, 30, tzinfo=RaisingTimezone())

    with pytest.raises(ValueError, match="timezone-aware"):
        build_selection_outcome_monitoring_plan(**kwargs)


def test_rejects_timezone_normalization_overflow() -> None:
    """Fail closed when a valid offset cannot be represented as a UTC datetime."""
    kwargs = valid_kwargs()
    kwargs["generated_at"] = datetime.min.replace(tzinfo=timezone(timedelta(hours=14)))

    with pytest.raises(ValueError, match="timezone-aware"):
        build_selection_outcome_monitoring_plan(**kwargs)


def test_rejects_post_construction_timezone_reinjection() -> None:
    """Do not emit evidence after low-level replacement of the frozen UTC instant."""
    plan = build_selection_outcome_monitoring_plan(**valid_kwargs())
    object.__setattr__(
        plan,
        "generated_at",
        datetime(2026, 4, 2, 17, 30, tzinfo=timezone(timedelta(hours=9))),
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        plan.canonical_json()
