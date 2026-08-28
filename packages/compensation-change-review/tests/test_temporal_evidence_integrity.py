"""Regression coverage for compensation-review recorded-time evidence integrity."""

from __future__ import annotations

from datetime import datetime, timezone

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


def test_rejects_datetime_subclasses_that_can_forge_recorded_time_evidence(
    valid_packet_kwargs: dict[str, object],
) -> None:
    """Canonical audit evidence must not call caller-overridable datetime methods."""
    kwargs = valid_packet_kwargs.copy()
    kwargs["generated_at"] = ForgedDateTime(2026, 8, 21, 4, 25, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="generated_at"):
        build_compensation_change_review_packet(**kwargs)
