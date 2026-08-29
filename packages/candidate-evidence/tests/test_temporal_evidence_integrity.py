"""Recorded-time integrity regressions for candidate-evidence intake."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo

import pytest

from orgmetra_candidate_evidence import build_candidate_evidence_intake_packet


class _ForgedCollectedAt(datetime):
    """Attempt to forge immutable evidence through datetime subclass methods."""

    def astimezone(self, tz=None):  # noqa: ANN001
        """Preserve the hostile runtime type through UTC normalization."""
        return self

    def isoformat(self, sep="T", timespec="auto") -> str:  # noqa: ARG002
        """Render a different instant from the underlying datetime value."""
        return "2099-12-31T23:59:59+00:00"


class _MutableOffset(tzinfo):
    """Expose timezone state that can change after packet construction."""

    def __init__(self) -> None:
        """Start with a zero offset."""
        self.offset = timedelta(0)

    def utcoffset(self, value):  # type: ignore[no-untyped-def]
        """Return the current mutable offset."""
        del value
        return self.offset

    def dst(self, value):  # type: ignore[no-untyped-def]
        """Keep daylight saving fixed."""
        del value
        return timedelta(0)


class _ExplodingOffset(tzinfo):
    """Raise arbitrary provider behavior while an offset is resolved."""

    def utcoffset(self, value):  # type: ignore[no-untyped-def]
        """Raise an implementation detail the boundary must normalize."""
        del value
        raise RuntimeError("provider details must not escape")

    def dst(self, value):  # type: ignore[no-untyped-def]
        """Keep daylight saving fixed if queried."""
        del value
        return timedelta(0)


def _build(collected_at: datetime):
    """Build one otherwise-valid packet around the supplied evidence instant."""
    return build_candidate_evidence_intake_packet(
        tenant_record_id="12345678-1234-4234-8234-123456789abc",
        intake_reference="candidate_evidence_intake:11111111-1111-4111-8111-111111111111",
        candidate_profile_reference="candidate_profile:22222222-2222-4222-8222-222222222222",
        requisition_reference="requisition:33333333-3333-4333-8333-333333333333",
        job_profile_reference="job_profile:44444444-4444-4444-8444-444444444444",
        job_requirements_reference="job_requirements:55555555-5555-4555-8555-555555555555",
        job_requirements_digest="a" * 64,
        evidence_set_reference="evidence_set:66666666-6666-4666-8666-666666666666",
        evidence_set_digest="b" * 64,
        source_provenance_reference="source_provenance:77777777-7777-4777-8777-777777777777",
        source_provenance_digest="c" * 64,
        handling_policy_reference="handling_policy:88888888-8888-4888-8888-888888888888",
        handling_policy_digest="d" * 64,
        retention_policy_reference="retention_policy:99999999-9999-4999-8999-999999999999",
        retention_policy_digest="e" * 64,
        actor_reference="actor:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        evidence_item_count=5,
        purpose_code="candidate_evidence_intake",
        reason_code="requisition_candidate_review",
        collected_at=collected_at,
    )


def test_candidate_evidence_rejects_datetime_subclasses_before_canonicalization() -> None:
    """Do not let caller-controlled datetime methods rewrite candidate audit evidence."""
    forged = _ForgedCollectedAt(2026, 8, 21, 5, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="collected_at must be an exact timezone-aware datetime"):
        _build(forged)


def test_candidate_evidence_detaches_mutable_timezone_state() -> None:
    """Keep canonical evidence stable after caller-owned timezone state mutates."""
    zone = _MutableOffset()
    packet = _build(datetime(2026, 8, 21, 5, 0, tzinfo=zone))
    first_json = packet.canonical_json()
    first_digest = packet.sha256_digest()

    zone.offset = timedelta(hours=9)

    assert packet.collected_at.tzinfo is timezone.utc
    assert packet.canonical_json() == first_json
    assert packet.sha256_digest() == first_digest


def test_candidate_evidence_normalizes_timezone_provider_exceptions() -> None:
    """Do not leak arbitrary timezone-provider exceptions from packet construction."""
    with pytest.raises(ValueError, match="collected_at"):
        _build(datetime(2026, 8, 21, 5, 0, tzinfo=_ExplodingOffset()))


@pytest.mark.parametrize(
    "collected_at",
    [
        datetime.min.replace(tzinfo=timezone(timedelta(hours=1))),
        datetime.max.replace(tzinfo=timezone(-timedelta(hours=1))),
    ],
)
def test_candidate_evidence_normalizes_unrepresentable_utc_overflow(
    collected_at: datetime,
) -> None:
    """Normalize out-of-range UTC conversion into the packet's boundary error."""
    with pytest.raises(ValueError, match="collected_at"):
        _build(collected_at)


def test_candidate_evidence_rejects_postconstruction_timezone_reinjection() -> None:
    """Fail closed if low-level mutation reintroduces executable timezone behavior."""
    packet = _build(datetime(2026, 8, 21, 5, 0, tzinfo=timezone.utc))
    object.__setattr__(packet, "collected_at", datetime(2026, 8, 21, 5, 0, tzinfo=_MutableOffset()))
    with pytest.raises(ValueError, match="collected_at"):
        packet.canonical_json()


def test_candidate_evidence_rejects_builtin_non_utc_timezone_reinjection() -> None:
    """Reject immutable non-UTC offsets that would serialize outside canonical UTC."""
    packet = _build(datetime(2026, 8, 21, 5, 0, tzinfo=timezone.utc))
    object.__setattr__(
        packet,
        "collected_at",
        datetime(2026, 8, 21, 14, 0, tzinfo=timezone(timedelta(hours=9))),
    )
    with pytest.raises(ValueError, match="collected_at"):
        packet.canonical_json()
