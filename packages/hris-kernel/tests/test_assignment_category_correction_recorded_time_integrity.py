"""Recorded-time integrity regressions for Assignment category corrections."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone, tzinfo
from uuid import UUID

import pytest

from orgmetra_hris_kernel import (
    AssignmentSupersessionFact,
    CorrectionError,
    correct_assignment_category,
)

SUPERSESSION = UUID("10000000-0000-7000-8000-000000000390")
REPLACEMENT = UUID("10000000-0000-7000-8000-000000000391")


class FixedCallerTimezone(tzinfo):
    """Expose caller-owned timezone behavior behind an exact built-in datetime."""

    def utcoffset(self, dt: datetime | None) -> timedelta:
        """Return one valid offset while remaining caller-controlled code."""
        return timedelta(hours=9)

    def dst(self, dt: datetime | None) -> timedelta:
        """Provide a stable daylight-saving offset for datetime compatibility."""
        return timedelta(0)

    def tzname(self, dt: datetime | None) -> str:
        """Return a deterministic display name that must not survive detachment."""
        return "CALLER"


class ExplodingCallerTimezone(FixedCallerTimezone):
    """Raise from offset resolution to verify stable domain error normalization."""

    def utcoffset(self, dt: datetime | None) -> timedelta:
        """Simulate an untrusted timezone provider failure."""
        raise RuntimeError("caller-controlled timezone failure")


class OffsetlessCallerTimezone(FixedCallerTimezone):
    """Return no usable offset despite carrying a non-null tzinfo object."""

    def utcoffset(self, dt: datetime | None) -> None:
        """Expose the offsetless custom-timezone case explicitly."""
        return None


class ForgedTimedelta(timedelta):
    """Represent caller-defined executable offset evidence."""


class ForgedOffsetCallerTimezone(FixedCallerTimezone):
    """Return a timedelta subtype rather than an exact trusted offset value."""

    def utcoffset(self, dt: datetime | None) -> timedelta:
        """Preserve valid numeric offset semantics while changing runtime identity."""
        return ForgedTimedelta(hours=9)


def _caller_recorded_at(zone: tzinfo) -> datetime:
    """Build an exact datetime whose timezone implementation remains caller-owned."""
    return datetime(2024, 6, 1, 12, 0, tzinfo=zone)


def test_category_correction_detaches_caller_timezone_before_returning_provenance(
    jordan_icu_assignment,
) -> None:
    """Accepted recorded time keeps the instant without executable caller timezone state."""
    predecessor = replace(jordan_icu_assignment, assignment_category_code="primary")
    caller_time = _caller_recorded_at(FixedCallerTimezone())

    closed, replacement, supersession = correct_assignment_category(
        predecessor,
        replacement_assignment_record_id=REPLACEMENT,
        assignment_supersession_record_id=SUPERSESSION,
        corrected_category_code="concurrent_secondary",
        recorded_at=caller_time,
    )

    for stored in (
        closed.recorded.end,
        replacement.recorded.start,
        supersession.recorded_at,
    ):
        assert type(stored) is datetime
        assert type(stored.tzinfo) is timezone
        assert stored.utcoffset() == timedelta(hours=9)


def test_direct_supersession_construction_detaches_caller_timezone(
    jordan_icu_assignment,
) -> None:
    """Direct provenance construction applies the same fixed-offset detachment boundary."""
    predecessor = replace(jordan_icu_assignment, assignment_category_code="primary")

    supersession = AssignmentSupersessionFact(
        tenant_record_id=predecessor.tenant_record_id,
        assignment_supersession_record_id=SUPERSESSION,
        predecessor_assignment_record_id=predecessor.assignment_record_id,
        replacement_assignment_record_id=REPLACEMENT,
        recorded_at=_caller_recorded_at(FixedCallerTimezone()),
    )

    assert type(supersession.recorded_at) is datetime
    assert type(supersession.recorded_at.tzinfo) is timezone
    assert supersession.recorded_at.utcoffset() == timedelta(hours=9)


@pytest.mark.parametrize(
    "caller_timezone",
    [ExplodingCallerTimezone(), OffsetlessCallerTimezone(), ForgedOffsetCallerTimezone()],
)
def test_category_correction_rejects_untrusted_timezone_offset_evidence(
    jordan_icu_assignment,
    caller_timezone,
) -> None:
    """Reject provider failures, missing offsets, and executable offset subtypes."""
    predecessor = replace(jordan_icu_assignment, assignment_category_code="primary")

    with pytest.raises(CorrectionError, match="recorded_at"):
        correct_assignment_category(
            predecessor,
            replacement_assignment_record_id=REPLACEMENT,
            assignment_supersession_record_id=SUPERSESSION,
            corrected_category_code="concurrent_secondary",
            recorded_at=_caller_recorded_at(caller_timezone),
        )
