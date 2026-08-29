"""Bitemporal workforce-composition change regressions."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone, tzinfo
from decimal import Decimal, localcontext
from uuid import UUID

import pytest

from orgmetra_hris_kernel import (
    AssignmentFact,
    DateInterval,
    EmploymentVersion,
    IdentityScopeError,
    IntervalError,
    RecordedInterval,
    WorkforceCompositionChangeSnapshot,
    WorkforceCompositionSnapshot,
    build_workforce_composition_change_snapshot,
    build_workforce_composition_snapshot,
)


def _id(value: int) -> UUID:
    return UUID(int=value)


def _employment(
    record_id: int,
    version_id: int,
    person_id: int,
    *,
    effective_start: date,
    status: str = "active",
) -> EmploymentVersion:
    return EmploymentVersion(
        tenant_record_id=_id(1),
        employment_record_id=_id(record_id),
        employment_record_version_id=_id(version_id),
        person_record_id=_id(person_id),
        employment_status_code=status,
        effective=DateInterval(effective_start),
        recorded=RecordedInterval(datetime(2026, 1, 1, tzinfo=timezone.utc)),
    )


def _assignment(
    assignment_id: int,
    employment_id: int,
    person_id: int,
    *,
    effective_start: date,
    ratio: str = "1.0000",
) -> AssignmentFact:
    return AssignmentFact(
        tenant_record_id=_id(1),
        assignment_record_id=_id(assignment_id),
        employment_record_id=_id(employment_id),
        person_record_id=_id(person_id),
        position_record_id=_id(assignment_id + 1000),
        allocation_ratio=Decimal(ratio),
        effective=DateInterval(effective_start),
        recorded=RecordedInterval(datetime(2026, 1, 1, tzinfo=timezone.utc)),
    )


def _source_facts() -> tuple[list[EmploymentVersion], list[AssignmentFact]]:
    employments = [
        _employment(101, 1001, 11, effective_start=date(2026, 1, 1)),
        _employment(102, 1002, 12, effective_start=date(2026, 1, 1), status="leave"),
        _employment(103, 1003, 13, effective_start=date(2026, 2, 1)),
    ]
    assignments = [
        _assignment(201, 101, 11, effective_start=date(2026, 1, 1)),
        _assignment(202, 102, 12, effective_start=date(2026, 1, 1), ratio="0.5000"),
        _assignment(203, 103, 13, effective_start=date(2026, 2, 1)),
    ]
    return employments, assignments


def _aggregate_snapshot(effective_on: date, staffed_fte: str) -> WorkforceCompositionSnapshot:
    """Build one valid aggregate endpoint with a controlled FTE spelling."""
    return WorkforceCompositionSnapshot(
        tenant_record_id=_id(1),
        effective_on=effective_on,
        known_at=datetime(2026, 2, 20, tzinfo=timezone.utc),
        person_headcount=1,
        employment_count=1,
        staffed_assignment_count=1,
        staffed_fte=Decimal(staffed_fte),
        unassigned_person_count=0,
        employment_status_counts=(("active", 1),),
    )


class _SequencedOffsetTimezone(tzinfo):
    """Timezone provider that changes its offset on each request."""

    def __init__(self) -> None:
        self.calls = 0

    def utcoffset(self, value: datetime | None) -> timedelta:
        """Return different offsets to detect duplicate cutoff resolution."""
        self.calls += 1
        return timedelta(hours=self.calls - 1)


def test_change_snapshot_compares_two_effective_dates_at_one_knowledge_cutoff() -> None:
    employments, assignments = _source_facts()
    snapshot = build_workforce_composition_change_snapshot(
        employments,
        assignments,
        tenant_record_id=_id(1),
        from_effective_on=date(2026, 1, 15),
        to_effective_on=date(2026, 2, 15),
        known_at=datetime(2026, 2, 20, tzinfo=timezone.utc),
    )

    assert snapshot.opening_snapshot.person_headcount == 2
    assert snapshot.closing_snapshot.person_headcount == 3
    assert snapshot.person_headcount_change == 1
    assert snapshot.employment_count_change == 1
    assert snapshot.staffed_assignment_count_change == 1
    assert snapshot.staffed_fte_change == Decimal("1.0000")
    assert snapshot.unassigned_person_count_change == 0
    assert snapshot.employment_status_changes == (("active", 1), ("leave", 0))
    assert '"schema_version":"orgmetra.workforce_composition_change.v1"' in snapshot.canonical_json()
    assert "person_record_id" not in snapshot.canonical_json()
    assert len(snapshot.content_digest()) == 64


def test_staffed_fte_change_is_independent_of_decimal_context_precision() -> None:
    """FTE deltas and their evidence must not depend on a caller's Decimal precision."""
    snapshot = WorkforceCompositionChangeSnapshot(
        _aggregate_snapshot(date(2026, 1, 15), "0.1234"),
        _aggregate_snapshot(date(2026, 2, 15), "0.2345"),
    )

    with localcontext() as context:
        context.prec = 2
        low_precision = (
            snapshot.staffed_fte_change,
            snapshot.canonical_json(),
            snapshot.content_digest(),
        )
    with localcontext() as context:
        context.prec = 28
        normal_precision = (
            snapshot.staffed_fte_change,
            snapshot.canonical_json(),
            snapshot.content_digest(),
        )

    assert low_precision == normal_precision
    assert low_precision[0] == Decimal("0.1111")


def test_change_builder_freezes_one_cutoff_before_building_both_endpoints() -> None:
    """Both change endpoints must use one detached instant from a mutable provider."""
    provider = _SequencedOffsetTimezone()
    snapshot = build_workforce_composition_change_snapshot(
        [],
        [],
        tenant_record_id=_id(1),
        from_effective_on=date(2026, 1, 15),
        to_effective_on=date(2026, 2, 15),
        known_at=datetime(2026, 2, 20, tzinfo=provider),
    )

    assert provider.calls == 1
    assert snapshot.opening_snapshot.known_at == snapshot.closing_snapshot.known_at
    assert snapshot.opening_snapshot.known_at == datetime(2026, 2, 20, tzinfo=timezone.utc)


def test_change_snapshot_is_deterministic_for_reordered_source_facts() -> None:
    employments, assignments = _source_facts()
    first = build_workforce_composition_change_snapshot(
        employments,
        assignments,
        tenant_record_id=_id(1),
        from_effective_on=date(2026, 1, 15),
        to_effective_on=date(2026, 2, 15),
        known_at=datetime(2026, 2, 20, tzinfo=timezone.utc),
    )
    second = build_workforce_composition_change_snapshot(
        list(reversed(employments)),
        list(reversed(assignments)),
        tenant_record_id=_id(1),
        from_effective_on=date(2026, 1, 15),
        to_effective_on=date(2026, 2, 15),
        known_at=datetime(2026, 2, 20, tzinfo=timezone.utc),
    )

    assert first.canonical_json() == second.canonical_json()
    assert first.content_digest() == second.content_digest()


def test_change_snapshot_rejects_non_forward_effective_window() -> None:
    with pytest.raises(IntervalError, match="later") as error:
        build_workforce_composition_change_snapshot(
            [],
            [],
            tenant_record_id=_id(1),
            from_effective_on=date(2026, 2, 15),
            to_effective_on=date(2026, 2, 15),
            known_at=datetime(2026, 2, 20, tzinfo=timezone.utc),
        )
    assert "Choose a later comparison date" in error.value.next_action


def test_direct_change_snapshot_rejects_cross_tenant_comparison() -> None:
    known_at = datetime(2026, 2, 20, tzinfo=timezone.utc)
    opening = build_workforce_composition_snapshot(
        [], [], tenant_record_id=_id(1), effective_on=date(2026, 1, 15), known_at=known_at
    )
    closing = build_workforce_composition_snapshot(
        [], [], tenant_record_id=_id(2), effective_on=date(2026, 2, 15), known_at=known_at
    )

    with pytest.raises(IdentityScopeError, match="same tenant"):
        WorkforceCompositionChangeSnapshot(opening, closing)


def test_direct_change_snapshot_rejects_different_knowledge_cutoffs() -> None:
    opening = build_workforce_composition_snapshot(
        [],
        [],
        tenant_record_id=_id(1),
        effective_on=date(2026, 1, 15),
        known_at=datetime(2026, 2, 19, tzinfo=timezone.utc),
    )
    closing = build_workforce_composition_snapshot(
        [],
        [],
        tenant_record_id=_id(1),
        effective_on=date(2026, 2, 15),
        known_at=datetime(2026, 2, 20, tzinfo=timezone.utc),
    )

    with pytest.raises(IntervalError, match="knowledge cutoff"):
        WorkforceCompositionChangeSnapshot(opening, closing)
