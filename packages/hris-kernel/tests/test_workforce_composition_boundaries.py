"""Boundary regressions for bitemporal workforce-composition reporting."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from orgmetra_hris_kernel import (
    AssignmentFact,
    DateInterval,
    EmploymentExclusivityError,
    EmploymentVersion,
    RecordedInterval,
)
from orgmetra_hris_kernel.errors import IntervalError, SingleValuedFactError
from orgmetra_hris_kernel.workforce import (
    WorkforceCompositionSnapshot,
    build_workforce_composition_snapshot,
)


def _id(value: int) -> UUID:
    """Return a stable opaque UUID fixture."""
    return UUID(int=value)


def _direct_snapshot(
    *,
    known_at: datetime,
    employment_status_counts: tuple[tuple[str, int], ...] = (("active", 1),),
) -> WorkforceCompositionSnapshot:
    """Build a direct public snapshot fixture without using the aggregate builder."""
    return WorkforceCompositionSnapshot(
        tenant_record_id=_id(1),
        effective_on=date(2026, 1, 15),
        known_at=known_at,
        person_headcount=1,
        employment_count=1,
        staffed_assignment_count=0,
        staffed_fte=Decimal("0.0000"),
        unassigned_person_count=1,
        employment_status_counts=employment_status_counts,
    )


def test_direct_snapshot_rejects_timezone_naive_knowledge_cutoff() -> None:
    """Direct evidence construction must not depend on the host's local timezone."""
    with pytest.raises(IntervalError, match="timezone-aware"):
        _direct_snapshot(known_at=datetime(2026, 1, 20))


def test_direct_snapshot_rejects_noncanonical_status_order() -> None:
    """Equivalent aggregates cannot produce different evidence because tuple order drifted."""
    with pytest.raises(SingleValuedFactError, match="canonical status order"):
        _direct_snapshot(
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            employment_status_counts=(("leave", 1), ("active", 1)),
        )


def test_direct_snapshot_rejects_duplicate_status_codes() -> None:
    """One employment status may appear only once in canonical aggregate evidence."""
    with pytest.raises(SingleValuedFactError, match="duplicate status"):
        _direct_snapshot(
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            employment_status_counts=(("active", 1), ("active", 1)),
        )


def test_snapshot_excludes_future_business_and_late_recorded_facts() -> None:
    """Scheduled or not-yet-known facts cannot leak into an earlier workforce report."""
    known_from_start = RecordedInterval(datetime(2026, 1, 1, tzinfo=timezone.utc))
    known_late = RecordedInterval(datetime(2026, 1, 25, tzinfo=timezone.utc))
    january = DateInterval(date(2026, 1, 1))
    february = DateInterval(date(2026, 2, 1))

    employments = [
        EmploymentVersion(_id(1), _id(101), _id(1001), _id(11), "active", january, known_from_start),
        EmploymentVersion(_id(1), _id(102), _id(1002), _id(12), "active", february, known_from_start),
        EmploymentVersion(_id(1), _id(103), _id(1003), _id(13), "active", january, known_late),
    ]
    assignments = [
        AssignmentFact(_id(1), _id(201), _id(101), _id(11), _id(1201), Decimal("0.7500"), january, known_from_start),
        AssignmentFact(_id(1), _id(202), _id(102), _id(12), _id(1202), Decimal("1.0000"), february, known_from_start),
        AssignmentFact(_id(1), _id(203), _id(101), _id(11), _id(1203), Decimal("0.1000"), january, known_late),
    ]

    snapshot = build_workforce_composition_snapshot(
        employments,
        assignments,
        tenant_record_id=_id(1),
        effective_on=date(2026, 1, 15),
        known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
    )

    assert snapshot.person_headcount == 1
    assert snapshot.employment_count == 1
    assert snapshot.staffed_assignment_count == 1
    assert snapshot.staffed_fte == Decimal("0.7500")


def test_snapshot_rejects_overlapping_exclusive_employments() -> None:
    """An impossible exclusive portfolio must not be normalized into plausible headcount."""
    known = RecordedInterval(datetime(2026, 1, 1, tzinfo=timezone.utc))
    effective = DateInterval(date(2026, 1, 1))
    employments = [
        EmploymentVersion(_id(1), _id(101), _id(1001), _id(11), "active", effective, known),
        EmploymentVersion(_id(1), _id(102), _id(1002), _id(11), "active", effective, known),
    ]

    with pytest.raises(EmploymentExclusivityError, match="exclusive employments overlap"):
        build_workforce_composition_snapshot(
            employments,
            [],
            tenant_record_id=_id(1),
            effective_on=date(2026, 1, 15),
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
        )


def test_empty_snapshot_has_deterministic_empty_status_evidence() -> None:
    """An empty workforce still has stable canonical evidence rather than missing fields."""
    snapshot = build_workforce_composition_snapshot(
        [],
        [],
        tenant_record_id=_id(1),
        effective_on=date(2026, 1, 15),
        known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
    )

    assert snapshot.person_headcount == 0
    assert snapshot.staffed_fte == Decimal("0.0000")
    assert '"employment_status_counts":[]' in snapshot.canonical_json()
