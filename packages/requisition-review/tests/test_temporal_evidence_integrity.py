"""Recorded-time integrity regressions for requisition-review evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo

import pytest

from orgmetra_requisition_review import build_requisition_review_packet


class _ForgedGeneratedAt(datetime):
    """Attempt to forge canonical evidence through datetime subclass methods."""

    def astimezone(self, tz=None):  # noqa: ANN001
        """Preserve the hostile runtime type through UTC normalization."""
        return self

    def isoformat(self, sep="T", timespec="auto") -> str:  # noqa: ARG002
        """Render a different instant from the underlying datetime value."""
        return "2099-01-01T00:00:00+00:00"


class _MutableOffset(tzinfo):
    """Expose timezone state that can change after packet construction."""

    def __init__(self) -> None:
        """Start at UTC."""
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


class _OversizedOffset(tzinfo):
    """Return one extreme offset so UTC detachment overflows the datetime range."""

    def utcoffset(self, value):  # type: ignore[no-untyped-def]
        """Force the subtraction outside representable instants."""
        del value
        return timedelta(hours=23, minutes=59)

    def dst(self, value):  # type: ignore[no-untyped-def]
        """Keep daylight saving fixed."""
        del value
        return timedelta(0)


def _build(generated_at: datetime):
    """Build one otherwise-valid requisition-review packet."""
    return build_requisition_review_packet(
        tenant_record_id="2b37b937-c3f1-49aa-8d19-785a7b7a9917",
        requisition_reference="requisition:11111111-1111-4111-8111-111111111111",
        job_profile_reference="job_profile:22222222-2222-4222-8222-222222222222",
        job_requirements_reference="job_requirements:33333333-3333-4333-8333-333333333333",
        job_requirements_digest="0" * 64,
        requirements_version_code="requirements_version_1",
        headcount_authorization_reference="headcount_authorization:44444444-4444-4444-8444-444444444444",
        hiring_manager_actor_reference="actor:55555555-5555-4555-8555-555555555555",
        approver_actor_reference="actor:66666666-6666-4666-8666-666666666666",
        requested_opening_count=3,
        purpose_code="requisition_review",
        reason_code="approved_growth_plan",
        generated_at=generated_at,
    )


def test_requisition_review_rejects_datetime_subclasses_before_canonicalization() -> None:
    """Do not let caller-controlled datetime methods rewrite approval evidence."""
    forged = _ForgedGeneratedAt(2026, 8, 21, 5, 10, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="generated_at must be an exact timezone-aware datetime"):
        _build(forged)


def test_requisition_review_detaches_mutable_timezone_state() -> None:
    """Keep canonical approval evidence stable after caller timezone state mutates."""
    zone = _MutableOffset()
    packet = _build(datetime(2026, 8, 21, 5, 10, tzinfo=zone))
    first_json = packet.canonical_json()
    first_digest = packet.sha256_digest()

    zone.offset = timedelta(hours=9)

    assert packet.generated_at.tzinfo is timezone.utc
    assert packet.canonical_json() == first_json
    assert packet.sha256_digest() == first_digest


def test_requisition_review_normalizes_timezone_provider_exceptions() -> None:
    """Do not leak arbitrary timezone-provider exceptions from packet construction."""
    with pytest.raises(ValueError, match="generated_at"):
        _build(datetime(2026, 8, 21, 5, 10, tzinfo=_ExplodingOffset()))


def test_requisition_review_rejects_postconstruction_timezone_reinjection() -> None:
    """Fail closed if low-level mutation reintroduces executable timezone behavior."""
    packet = _build(datetime(2026, 8, 21, 5, 10, tzinfo=timezone.utc))
    object.__setattr__(packet, "generated_at", datetime(2026, 8, 21, 5, 10, tzinfo=_MutableOffset()))
    with pytest.raises(ValueError, match="generated_at"):
        packet.canonical_json()


def test_requisition_review_normalizes_offset_overflow_to_value_error() -> None:
    """Fail closed with the contract error when UTC detachment overflows."""
    extreme = datetime(1, 1, 1, 0, 0, tzinfo=_OversizedOffset())
    with pytest.raises(ValueError, match="generated_at"):
        _build(extreme)
