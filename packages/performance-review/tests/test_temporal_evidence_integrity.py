"""Regression coverage for system-recorded performance-review time integrity."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone, tzinfo

import pytest

import orgmetra_performance_review.packet as packet_module
from orgmetra_performance_review import build_performance_review_packet


class ForgedDateTime(datetime):
    """Datetime subclass able to forge canonical evidence rendering."""

    def astimezone(self, tz=None):  # type: ignore[no-untyped-def]
        """Keep the subclass alive across UTC normalization."""
        return self

    def isoformat(self, *args, **kwargs) -> str:  # type: ignore[no-untyped-def]
        """Return an instant different from the underlying evidence instant."""
        return "2099-12-31T23:59:59+00:00"


class MutableTimezone(tzinfo):
    """Clock timezone provider whose offset changes after evidence issuance."""

    def __init__(self, offset: timedelta) -> None:
        """Store one mutable offset."""
        self.offset = offset

    def utcoffset(self, dt: datetime | None) -> timedelta:
        """Return the current mutable offset."""
        return self.offset

    def dst(self, dt: datetime | None) -> timedelta:
        """Expose no daylight-saving adjustment."""
        return timedelta(0)


class NullOffsetTimezone(tzinfo):
    """Clock timezone provider with no concrete UTC offset."""

    def utcoffset(self, dt: datetime | None) -> None:
        """Return no usable offset."""
        return None

    def dst(self, dt: datetime | None) -> None:
        """Return no daylight-saving offset."""
        return None


class RaisingTimezone(tzinfo):
    """Clock timezone provider that raises while resolving UTC offset."""

    def utcoffset(self, dt: datetime | None) -> timedelta:
        """Raise at the recorded-time trust boundary."""
        raise RuntimeError("provider failure")

    def dst(self, dt: datetime | None) -> timedelta:
        """Expose no daylight-saving adjustment."""
        return timedelta(0)


def valid_kwargs() -> dict[str, object]:
    """Return one otherwise valid performance-review packet input."""
    return {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "performance_review_reference": "performance_review:22222222-2222-4222-8222-222222222222",
        "person_record_reference": "person_record:33333333-3333-4333-8333-333333333333",
        "employment_record_reference": "employment_record:44444444-4444-4444-8444-444444444444",
        "job_profile_reference": "job_profile:55555555-5555-4555-8555-555555555555",
        "performance_cycle_reference": "performance_cycle:66666666-6666-4666-8666-666666666666",
        "criterion_set_reference": "criterion_set:77777777-7777-4777-8777-777777777777",
        "criterion_set_digest": "a" * 64,
        "goal_plan_reference": "performance_goal_plan:88888888-8888-4888-8888-888888888888",
        "goal_plan_digest": "b" * 64,
        "criterion_observation_snapshot_reference": "criterion_observation_snapshot:99999999-9999-4999-8999-999999999999",
        "criterion_observation_snapshot_digest": "c" * 64,
        "development_plan_reference": "development_plan:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "development_plan_digest": "d" * 64,
        "reviewer_reference": "actor:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "purpose_code": "performance_review",
        "reason_code": "scheduled_cycle_review",
        "review_period_start": date(2026, 1, 1),
        "review_period_end": date(2026, 6, 30),
    }


def test_rejects_datetime_subclasses_from_trusted_clock_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Canonical audit evidence must not invoke overridable datetime methods."""
    forged = ForgedDateTime(2026, 8, 19, 5, 15, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(packet_module, "_system_recorded_at", lambda: forged)

    with pytest.raises(ValueError, match="generated_at"):
        build_performance_review_packet(**valid_kwargs())


def test_detaches_mutable_clock_timezone_from_recorded_time_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mutable clock timezone provider must not rewrite issued evidence."""
    provider = MutableTimezone(timedelta(hours=9))
    recorded_at = datetime(2026, 8, 19, 14, 15, 30, tzinfo=provider)
    monkeypatch.setattr(packet_module, "_system_recorded_at", lambda: recorded_at)

    packet = build_performance_review_packet(**valid_kwargs())
    before = packet.canonical_json()
    provider.offset = timedelta(hours=-7)

    assert packet.canonical_json() == before
    assert packet.generated_at == datetime(2026, 8, 19, 5, 15, 30, tzinfo=timezone.utc)
    assert packet.generated_at.tzinfo is timezone.utc


def test_rejects_future_system_recorded_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """Do not seal evidence when the trusted clock reports a future instant."""
    monkeypatch.setattr(
        packet_module,
        "_system_recorded_at",
        lambda: datetime(2099, 1, 1, tzinfo=timezone.utc),
    )

    with pytest.raises(ValueError, match="generated_at must not be in the future"):
        build_performance_review_packet(**valid_kwargs())


def test_rejects_clock_timezone_without_concrete_offset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject clock adapters that cannot resolve a concrete UTC offset."""
    recorded_at = datetime(2026, 8, 19, 5, 15, 30, tzinfo=NullOffsetTimezone())
    monkeypatch.setattr(packet_module, "_system_recorded_at", lambda: recorded_at)

    with pytest.raises(ValueError, match="generated_at"):
        build_performance_review_packet(**valid_kwargs())


def test_normalizes_clock_timezone_provider_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Do not leak clock timezone exceptions across the evidence boundary."""
    recorded_at = datetime(2026, 8, 19, 5, 15, 30, tzinfo=RaisingTimezone())
    monkeypatch.setattr(packet_module, "_system_recorded_at", lambda: recorded_at)

    with pytest.raises(ValueError, match="generated_at"):
        build_performance_review_packet(**valid_kwargs())


def test_rejects_clock_timezone_normalization_overflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail closed when a clock instant cannot be represented as UTC."""
    recorded_at = datetime.min.replace(tzinfo=timezone(timedelta(hours=14)))
    monkeypatch.setattr(packet_module, "_system_recorded_at", lambda: recorded_at)

    with pytest.raises(ValueError, match="generated_at"):
        build_performance_review_packet(**valid_kwargs())


def test_rejects_post_construction_timezone_reinjection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not emit evidence after low-level replacement of the frozen UTC instant."""
    monkeypatch.setattr(
        packet_module,
        "_system_recorded_at",
        lambda: datetime(2026, 8, 19, 5, 15, 30, tzinfo=timezone.utc),
    )
    packet = build_performance_review_packet(**valid_kwargs())
    object.__setattr__(
        packet,
        "generated_at",
        datetime(2026, 8, 19, 14, 15, 30, tzinfo=timezone(timedelta(hours=9))),
    )

    with pytest.raises(ValueError, match="generated_at"):
        packet.canonical_json()
