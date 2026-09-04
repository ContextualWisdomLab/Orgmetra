"""Regression coverage for compensation-review recorded-time evidence integrity."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo

import pytest

from orgmetra_compensation_change_review import build_compensation_change_review_packet


class ForgedDateTime(datetime):
    """Datetime subclass able to forge canonical recorded-time evidence."""

    def astimezone(self, tz=None):  # type: ignore[no-untyped-def]
        """Keep the hostile subclass alive across UTC normalization."""
        return self

    def isoformat(self, *args, **kwargs) -> str:  # type: ignore[no-untyped-def]
        """Return an instant different from the underlying review evidence."""
        return "2099-12-31T23:59:59+00:00"


class MutableOffsetTimezone(tzinfo):
    """Timezone whose offset can change after a packet has been issued."""

    def __init__(self, offset_hours: int) -> None:
        self.offset_hours = offset_hours

    def utcoffset(self, dt):  # type: ignore[no-untyped-def]
        """Return the current mutable offset."""
        return timedelta(hours=self.offset_hours)

    def dst(self, dt):  # type: ignore[no-untyped-def]
        """Keep daylight-saving behavior deterministic for the regression."""
        return timedelta(0)


class MissingOffsetTimezone(tzinfo):
    """Timezone object that cannot establish a concrete UTC offset."""

    def utcoffset(self, dt):  # type: ignore[no-untyped-def]
        """Signal that the recorded instant cannot be resolved."""
        return None

    def dst(self, dt):  # type: ignore[no-untyped-def]
        """Keep daylight-saving behavior absent for this invalid timezone."""
        return None


def test_rejects_datetime_subclasses_that_can_forge_recorded_time_evidence(
    valid_packet_kwargs: dict[str, object],
) -> None:
    """Canonical audit evidence must not call caller-overridable datetime methods."""
    kwargs = valid_packet_kwargs.copy()
    kwargs["generated_at"] = ForgedDateTime(2026, 8, 21, 4, 25, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="generated_at"):
        build_compensation_change_review_packet(**kwargs)


def test_rejects_timezone_without_resolvable_utc_offset(
    valid_packet_kwargs: dict[str, object],
) -> None:
    """Recorded-time evidence must fail closed when its UTC instant is indeterminate."""
    kwargs = valid_packet_kwargs.copy()
    kwargs["generated_at"] = datetime(2026, 8, 21, 4, 25, tzinfo=MissingOffsetTimezone())

    with pytest.raises(ValueError, match="generated_at"):
        build_compensation_change_review_packet(**kwargs)


def test_corrupted_post_issuance_time_fails_closed_before_canonical_export(
    valid_packet_kwargs: dict[str, object],
) -> None:
    """Low-level mutation must not make an indeterminate recorded time exportable."""
    packet = build_compensation_change_review_packet(**valid_packet_kwargs)
    object.__setattr__(
        packet,
        "generated_at",
        datetime(2026, 8, 21, 4, 25, tzinfo=MissingOffsetTimezone()),
    )

    with pytest.raises(ValueError, match="generated_at"):
        packet.canonical_json()


def test_freezes_mutable_timezone_before_issuing_recorded_time_evidence(
    valid_packet_kwargs: dict[str, object],
) -> None:
    """Caller-owned tzinfo mutation must not rewrite or invalidate issued audit evidence."""
    mutable_timezone = MutableOffsetTimezone(9)
    kwargs = valid_packet_kwargs.copy()
    kwargs["generated_at"] = datetime(2026, 8, 21, 13, 25, tzinfo=mutable_timezone)

    packet = build_compensation_change_review_packet(**kwargs)
    canonical_before = packet.canonical_json()
    digest_before = packet.sha256_digest()

    assert packet.generated_at.tzinfo is timezone.utc
    assert '"generated_at":"2026-08-21T04:25:00Z"' in canonical_before

    mutable_timezone.offset_hours = -5

    assert packet.canonical_json() == canonical_before
    assert packet.sha256_digest() == digest_before
