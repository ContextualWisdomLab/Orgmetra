"""Realistic workforce-composition reporting regressions."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from orgmetra_hris_kernel import (
    AssignmentFact,
    AssignmentPortfolioError,
    DateInterval,
    EmploymentCoverageError,
    EmploymentVersion,
    IntervalError,
    RecordedInterval,
    SingleValuedFactError,
)
from orgmetra_hris_kernel.workforce import build_workforce_composition_snapshot


def _id(value: int) -> UUID:
    """Return stable opaque UUID fixtures without human-readable payloads."""
    return UUID(int=value)


def _recorded(start_day: int = 1, end_day: int | None = None) -> RecordedInterval:
    """Return a January 2026 UTC knowledge interval."""
    start = datetime(2026, 1, start_day, tzinfo=timezone.utc)
    end = None if end_day is None else datetime(2026, 1, end_day, tzinfo=timezone.utc)
    return RecordedInterval(start, end)


def _employment(
    record_id: int,
    version_id: int,
    person_id: int,
    *,
    tenant_id: int = 1,
    status: str = "active",
    concurrency: str = "exclusive",
    recorded: RecordedInterval | None = None,
) -> EmploymentVersion:
    """Build one tenant-scoped employment version."""
    return EmploymentVersion(
        tenant_record_id=_id(tenant_id),
        employment_record_id=_id(record_id),
        employment_record_version_id=_id(version_id),
        person_record_id=_id(person_id),
        employment_status_code=status,
        effective=DateInterval(date(2026, 1, 1)),
        recorded=recorded or _recorded(),
        employment_concurrency_code=concurrency,
    )


def _assignment(
    assignment_id: int,
    employment_id: int,
    person_id: int,
    ratio: str,
    *,
    tenant_id: int = 1,
    recorded: RecordedInterval | None = None,
) -> AssignmentFact:
    """Build one visible position assignment."""
    return AssignmentFact(
        tenant_record_id=_id(tenant_id),
        assignment_record_id=_id(assignment_id),
        employment_record_id=_id(employment_id),
        person_record_id=_id(person_id),
        position_record_id=_id(assignment_id + 1000),
        allocation_ratio=Decimal(ratio),
        effective=DateInterval(date(2026, 1, 1)),
        recorded=recorded or _recorded(),
    )


def test_snapshot_counts_people_once_across_concurrent_employments_and_is_deterministic() -> None:
    """Headcount is person-based while employment and FTE retain real portfolio shape."""
    employments = [
        _employment(101, 1001, 11),
        _employment(102, 1002, 11, concurrency="concurrent"),
        _employment(103, 1003, 12, status="leave"),
        _employment(104, 1004, 13, status="terminated"),
        _employment(105, 1005, 14, tenant_id=2),
    ]
    assignments = [
        _assignment(201, 101, 11, "0.6000"),
        _assignment(202, 102, 11, "0.4000"),
        _assignment(203, 103, 12, "0.5000"),
        _assignment(204, 105, 14, "1.0000", tenant_id=2),
    ]

    snapshot = build_workforce_composition_snapshot(
        employments,
        assignments,
        tenant_record_id=_id(1),
        effective_on=date(2026, 1, 15),
        known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
    )
    reordered = build_workforce_composition_snapshot(
        list(reversed(employments)),
        list(reversed(assignments)),
        tenant_record_id=_id(1),
        effective_on=date(2026, 1, 15),
        known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
    )

    assert snapshot.person_headcount == 2
    assert snapshot.employment_count == 3
    assert snapshot.staffed_assignment_count == 3
    assert snapshot.staffed_fte == Decimal("1.5000")
    assert snapshot.unassigned_person_count == 0
    assert snapshot.employment_status_counts == (("active", 2), ("leave", 1))
    assert snapshot.canonical_json() == reordered.canonical_json()
    assert snapshot.content_digest() == reordered.content_digest()
    assert len(snapshot.content_digest()) == 64


def test_snapshot_reports_unassigned_people_without_exposing_identity_rows() -> None:
    """A worker with eligible employment but no assignment remains visible as a count gap."""
    snapshot = build_workforce_composition_snapshot(
        [_employment(101, 1001, 11), _employment(103, 1003, 12, status="leave")],
        [_assignment(201, 101, 11, "1.0000")],
        tenant_record_id=_id(1),
        effective_on=date(2026, 1, 15),
        known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
    )

    assert snapshot.person_headcount == 2
    assert snapshot.unassigned_person_count == 1
    assert "person_record" not in snapshot.canonical_json()
    assert "employment_record" not in snapshot.canonical_json()


def test_snapshot_reconstructs_what_was_known_before_and_after_a_status_correction() -> None:
    """Recorded/system time changes the report without rewriting business history."""
    employment_id = 101
    person_id = 11
    before = _employment(employment_id, 1001, person_id, recorded=_recorded(1, 20))
    corrected = _employment(
        employment_id,
        1002,
        person_id,
        status="terminated",
        recorded=_recorded(20),
    )

    earlier = build_workforce_composition_snapshot(
        [before, corrected],
        [_assignment(201, employment_id, person_id, "1.0000", recorded=_recorded(1, 20))],
        tenant_record_id=_id(1),
        effective_on=date(2026, 1, 15),
        known_at=datetime(2026, 1, 10, tzinfo=timezone.utc),
    )
    later = build_workforce_composition_snapshot(
        [before, corrected],
        [],
        tenant_record_id=_id(1),
        effective_on=date(2026, 1, 15),
        known_at=datetime(2026, 1, 25, tzinfo=timezone.utc),
    )

    assert earlier.person_headcount == 1
    assert earlier.staffed_fte == Decimal("1.0000")
    assert later.person_headcount == 0
    assert later.employment_count == 0
    assert later.staffed_fte == Decimal("0.0000")


def test_snapshot_fails_closed_on_two_visible_versions_of_one_employment() -> None:
    """Contradictory recorded-visible employment truth cannot become a buyer metric."""
    with pytest.raises(SingleValuedFactError, match="more than one version"):
        build_workforce_composition_snapshot(
            [_employment(101, 1001, 11), _employment(101, 1002, 11)],
            [],
            tenant_record_id=_id(1),
            effective_on=date(2026, 1, 15),
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
        )


def test_snapshot_fails_closed_on_two_visible_versions_of_one_assignment() -> None:
    """A duplicated current assignment identity cannot inflate FTE silently."""
    with pytest.raises(SingleValuedFactError, match="assignment"):
        build_workforce_composition_snapshot(
            [_employment(101, 1001, 11)],
            [_assignment(201, 101, 11, "0.5000"), _assignment(201, 101, 11, "0.5000")],
            tenant_record_id=_id(1),
            effective_on=date(2026, 1, 15),
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
        )


def test_snapshot_reuses_assignment_integrity_instead_of_reporting_bad_fte() -> None:
    """Overallocated employment remains a data-integrity failure, not a misleading metric."""
    with pytest.raises(AssignmentPortfolioError, match="exceed"):
        build_workforce_composition_snapshot(
            [_employment(101, 1001, 11)],
            [_assignment(201, 101, 11, "0.7000"), _assignment(202, 101, 11, "0.5000")],
            tenant_record_id=_id(1),
            effective_on=date(2026, 1, 15),
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
        )


def test_snapshot_rejects_assignment_person_mismatch() -> None:
    """An assignment cannot borrow another person's otherwise valid employment."""
    with pytest.raises(EmploymentCoverageError, match="does not match"):
        build_workforce_composition_snapshot(
            [_employment(101, 1001, 11)],
            [_assignment(201, 101, 12, "1.0000")],
            tenant_record_id=_id(1),
            effective_on=date(2026, 1, 15),
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
        )


def test_snapshot_rejects_naive_knowledge_cutoff_even_when_inputs_are_empty() -> None:
    """Empty reports still require an unambiguous recorded-time coordinate."""
    with pytest.raises(IntervalError, match="timezone-aware"):
        build_workforce_composition_snapshot(
            [],
            [],
            tenant_record_id=_id(1),
            effective_on=date(2026, 1, 15),
            known_at=datetime(2026, 1, 20),
        )
