"""Boundary regressions for bitemporal workforce-composition reporting."""

from __future__ import annotations

from datetime import date, datetime, timezone, tzinfo
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


class _UnknownOffsetTimezone(tzinfo):
    """Timezone marker whose UTC offset is intentionally indeterminate."""

    def utcoffset(self, value: datetime | None) -> None:
        """Return no offset so the datetime is not a usable absolute instant."""
        return None


def _id(value: int) -> UUID:
    """Return a stable opaque UUID fixture."""
    return UUID(int=value)


def _direct_snapshot(
    *,
    known_at: datetime,
    employment_status_counts: tuple[tuple[str, int], ...] = (("active", 1),),
    person_headcount: int = 1,
    employment_count: int = 1,
    staffed_assignment_count: int = 0,
    staffed_fte: Decimal = Decimal("0.0000"),
    unassigned_person_count: int = 1,
) -> WorkforceCompositionSnapshot:
    """Build a direct public snapshot fixture without using the aggregate builder."""
    return WorkforceCompositionSnapshot(
        tenant_record_id=_id(1),
        effective_on=date(2026, 1, 15),
        known_at=known_at,
        person_headcount=person_headcount,
        employment_count=employment_count,
        staffed_assignment_count=staffed_assignment_count,
        staffed_fte=staffed_fte,
        unassigned_person_count=unassigned_person_count,
        employment_status_counts=employment_status_counts,
    )


def test_direct_snapshot_rejects_timezone_naive_knowledge_cutoff() -> None:
    """Direct evidence construction must not depend on the host's local timezone."""
    with pytest.raises(IntervalError, match="timezone-aware"):
        _direct_snapshot(known_at=datetime(2026, 1, 20))


def test_direct_snapshot_rejects_unknown_offset_knowledge_cutoff() -> None:
    """A tzinfo marker without an offset is not a reproducible absolute instant."""
    with pytest.raises(IntervalError, match="timezone-aware"):
        _direct_snapshot(known_at=datetime(2026, 1, 20, tzinfo=_UnknownOffsetTimezone()))


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


def test_direct_snapshot_rejects_negative_aggregate_counts() -> None:
    """Portable evidence cannot hash a negative workforce count."""
    with pytest.raises(SingleValuedFactError, match="internally inconsistent"):
        _direct_snapshot(
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            person_headcount=-1,
        )


def test_direct_snapshot_rejects_boolean_aggregate_counts() -> None:
    """Boolean values must not masquerade as integer workforce counts."""
    with pytest.raises(SingleValuedFactError, match="internally inconsistent"):
        _direct_snapshot(
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            employment_count=True,
        )


def test_direct_snapshot_rejects_unassigned_count_above_headcount() -> None:
    """Unassigned people cannot exceed the distinct people represented."""
    with pytest.raises(SingleValuedFactError, match="internally inconsistent"):
        _direct_snapshot(
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            unassigned_person_count=2,
        )


def test_direct_snapshot_rejects_nonfinite_staffed_fte() -> None:
    """NaN or infinite FTE values cannot enter deterministic audit evidence."""
    with pytest.raises(SingleValuedFactError, match="internally inconsistent"):
        _direct_snapshot(
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            staffed_fte=Decimal("NaN"),
        )


def test_direct_snapshot_rejects_non_decimal_staffed_fte() -> None:
    """FTE evidence must remain Decimal so finite and canonical formatting are guaranteed."""
    with pytest.raises(SingleValuedFactError, match="internally inconsistent"):
        _direct_snapshot(
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            staffed_fte=0,  # type: ignore[arg-type]
        )


def test_direct_snapshot_rejects_fte_without_staffed_assignments() -> None:
    """Zero staffed assignments cannot carry positive FTE evidence."""
    with pytest.raises(SingleValuedFactError, match="internally inconsistent"):
        _direct_snapshot(
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            staffed_fte=Decimal("0.0001"),
        )


def test_direct_snapshot_rejects_zero_fte_with_staffed_assignments() -> None:
    """A staffed assignment must contribute a positive allocation."""
    with pytest.raises(SingleValuedFactError, match="internally inconsistent"):
        _direct_snapshot(
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            staffed_assignment_count=1,
            staffed_fte=Decimal("0.0000"),
            unassigned_person_count=0,
        )


def test_direct_snapshot_rejects_staffing_without_employment_totals() -> None:
    """Staffing cannot exist when no reportable employment is represented."""
    with pytest.raises(SingleValuedFactError, match="internally inconsistent"):
        _direct_snapshot(
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            employment_status_counts=(),
            employment_count=0,
            staffed_assignment_count=1,
            staffed_fte=Decimal("0.5000"),
            unassigned_person_count=0,
        )


def test_direct_snapshot_rejects_staffing_without_people() -> None:
    """Staffing cannot exist when no reportable person is represented."""
    with pytest.raises(SingleValuedFactError, match="internally inconsistent"):
        _direct_snapshot(
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            person_headcount=0,
            staffed_assignment_count=1,
            staffed_fte=Decimal("0.5000"),
            unassigned_person_count=0,
        )


def test_direct_snapshot_rejects_fte_above_staffed_assignment_count() -> None:
    """Each staffed assignment contributes at most one full-time allocation."""
    with pytest.raises(SingleValuedFactError, match="internally inconsistent"):
        _direct_snapshot(
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            staffed_assignment_count=1,
            staffed_fte=Decimal("1.0001"),
            unassigned_person_count=0,
        )


def test_direct_snapshot_rejects_assigned_person_without_staffing() -> None:
    """A person counted as assigned requires at least one staffed assignment."""
    with pytest.raises(SingleValuedFactError, match="internally inconsistent"):
        _direct_snapshot(
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            unassigned_person_count=0,
        )


def test_direct_snapshot_rejects_staffing_when_every_person_is_unassigned() -> None:
    """Staffed assignments cannot coexist with an entirely unassigned workforce."""
    with pytest.raises(SingleValuedFactError, match="internally inconsistent"):
        _direct_snapshot(
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            staffed_assignment_count=1,
            staffed_fte=Decimal("0.5000"),
            unassigned_person_count=1,
        )


def test_direct_snapshot_rejects_more_assigned_people_than_assignments() -> None:
    """Distinct assigned people cannot exceed the number of staffed assignments."""
    with pytest.raises(SingleValuedFactError, match="internally inconsistent"):
        _direct_snapshot(
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            person_headcount=2,
            employment_count=2,
            employment_status_counts=(("active", 2),),
            staffed_assignment_count=1,
            staffed_fte=Decimal("0.5000"),
            unassigned_person_count=0,
        )


def test_direct_snapshot_rejects_boolean_status_counts() -> None:
    """Boolean values must not serialize as employment counts."""
    with pytest.raises(SingleValuedFactError, match="internally inconsistent"):
        _direct_snapshot(
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            employment_status_counts=(("active", True),),  # type: ignore[tuple-item]
        )


def test_direct_snapshot_rejects_negative_status_counts() -> None:
    """Negative per-status counts cannot reconcile a workforce aggregate."""
    with pytest.raises(SingleValuedFactError, match="internally inconsistent"):
        _direct_snapshot(
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            employment_status_counts=(("active", -1), ("leave", 2)),
        )


def test_direct_snapshot_rejects_status_total_mismatch() -> None:
    """Per-status employment counts must reconcile to total employment count."""
    with pytest.raises(SingleValuedFactError, match="internally inconsistent"):
        _direct_snapshot(
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            employment_status_counts=(("active", 2),),
        )


def test_direct_snapshot_rejects_nonreportable_status_code() -> None:
    """Direct evidence cannot introduce a status outside the reportable workforce vocabulary."""
    with pytest.raises(SingleValuedFactError, match="internally inconsistent"):
        _direct_snapshot(
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            employment_status_counts=(("terminated", 1),),
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
