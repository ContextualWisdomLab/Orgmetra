"""Assignment portfolio and employment-coverage rules."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from orgmetra_hris_kernel.errors import (
    AssignmentPortfolioError,
    EmploymentCoverageError,
    PositionCoverageError,
    PositionSeatError,
)
from orgmetra_hris_kernel.facts import AssignmentFact, EmploymentVersion, PositionVersion
from orgmetra_hris_kernel.intervals import DateInterval
from orgmetra_hris_kernel.resolution import resolve_bitemporal_facts

_ONE = Decimal("1.0000")
_ZERO = Decimal("0")
_ASSIGNMENT_ELIGIBLE_EMPLOYMENT_STATUSES = frozenset({"active", "leave"})
_STAFFABLE_POSITION_STATUSES = frozenset({"active", "open"})


def _ratio_is_valid(allocation_ratio: Decimal) -> bool:
    """Return whether one assignment row stays inside (0, 1.0000]."""
    return allocation_ratio > _ZERO and allocation_ratio <= _ONE


def _union_covers(intervals: list[DateInterval], target: DateInterval) -> bool:
    """Return whether merged employment periods cover the assignment period."""
    cursor = target.start
    while target.end is None or cursor < target.end:
        covering = next((interval for interval in intervals if interval.contains(cursor)), None)
        if covering is None:
            return False
        if covering.end is None:
            return True
        cursor = covering.end
    return True


def validate_assignment_portfolio(
    assignments: list[AssignmentFact],
    *,
    tenant_record_id: UUID,
    person_record_id: UUID,
    employment_record_id: UUID,
    effective_on: date,
    known_at: datetime,
) -> None:
    """Reject invalid ratios or a visible allocation total above 1.0000.

    Args:
        assignments: Candidate assignment facts, including other tenants and people.
        tenant_record_id: Tenant namespace whose employment allocation is reviewed.
        person_record_id: Worker whose portfolio is being saved.
        employment_record_id: Employment that owns the allocations.
        effective_on: The day whose split is being reviewed.
        known_at: The knowledge cutoff used for the review.

    Raises:
        AssignmentPortfolioError: Reduce one allocation, then save again.
    """
    scoped = [
        fact
        for fact in assignments
        if fact.tenant_record_id == tenant_record_id
        and fact.person_record_id == person_record_id
        and fact.employment_record_id == employment_record_id
    ]
    for fact in scoped:
        if not _ratio_is_valid(fact.allocation_ratio):
            raise AssignmentPortfolioError(
                "allocation_ratio must be greater than 0 and at most 1.0000.",
                next_action="Enter an allocation between 0.0001 and 1.0000, then save.",
            )
    visible = resolve_bitemporal_facts(
        scoped,
        tenant_record_id=tenant_record_id,
        identity_of="employment_record_id",
        identity_value=employment_record_id,
        effective_on=effective_on,
        known_at=known_at,
    )
    total = sum((fact.allocation_ratio for fact in visible), start=_ZERO)
    if total > _ONE:
        raise AssignmentPortfolioError(
            "Visible allocations for one employment exceed 1.0000.",
            next_action="Reduce one assignment so the employment total is at most 1.0000.",
        )


def validate_assignment_employment_coverage(
    assignment: AssignmentFact,
    employment_versions: list[EmploymentVersion],
    *,
    known_at: datetime,
) -> None:
    """Require the assignment's tenant, person, and days to match eligible employment.

    ``active`` and ``leave`` versions remain assignment-eligible; terminal or
    otherwise non-eligible statuses cannot provide staffing coverage. Versions
    from another tenant are never eligible evidence for this assignment. Two
    simultaneously recorded-visible versions may not overlap the assignment's
    effective interval because contradictory status facts must fail closed.

    Raises:
        EmploymentCoverageError: Link or correct the employment before saving.
    """
    named = [
        version
        for version in employment_versions
        if version.tenant_record_id == assignment.tenant_record_id
        and version.employment_record_id == assignment.employment_record_id
    ]
    if any(version.person_record_id != assignment.person_record_id for version in named):
        raise EmploymentCoverageError(
            "Assignment person does not match the named employment.",
            next_action="Select the employment that belongs to this worker, then save.",
        )
    assignment_visible = [
        version
        for version in named
        if version.recorded.contains(known_at)
        and version.effective.overlaps(assignment.effective)
    ]
    for index, left in enumerate(assignment_visible):
        for right in assignment_visible[index + 1 :]:
            if left.effective.overlaps(right.effective):
                raise EmploymentCoverageError(
                    "Assignment intersects contradictory employment versions in this tenant.",
                    next_action=(
                        "Close the superseded recorded employment version, then save the assignment again."
                    ),
                )
    visible = [
        version
        for version in assignment_visible
        if version.employment_status_code in _ASSIGNMENT_ELIGIBLE_EMPLOYMENT_STATUSES
    ]
    if not visible or not _union_covers(
        [version.effective for version in visible],
        assignment.effective,
    ):
        raise EmploymentCoverageError(
            "Assignment is not covered by an active or leave employment version in this tenant.",
            next_action="Link this tenant's employment or restore eligible coverage for those days.",
        )


def validate_assignment_position_coverage(
    assignment: AssignmentFact,
    position_versions: list[PositionVersion],
    *,
    known_at: datetime,
) -> None:
    """Require every assignment day to land on one unambiguous staffable position.

    ``active`` and ``open`` seats remain staffable. ``closed``, ``frozen``, and
    ``abolished`` seats cannot receive new or continuing allocations. A matching
    position identifier in another tenant never supplies local staffing coverage.
    Simultaneously recorded-visible position versions may not overlap the
    assignment interval because a position is a single-valued seat-state fact.

    Raises:
        PositionCoverageError: Choose an open seat or correct contradictory position history.
    """
    named = [
        version
        for version in position_versions
        if version.tenant_record_id == assignment.tenant_record_id
        and version.position_record_id == assignment.position_record_id
    ]
    assignment_visible = [
        version
        for version in named
        if version.recorded.contains(known_at)
        and version.effective.overlaps(assignment.effective)
    ]
    for index, left in enumerate(assignment_visible):
        for right in assignment_visible[index + 1 :]:
            if left.effective.overlaps(right.effective):
                raise PositionCoverageError(
                    "Assignment intersects contradictory position versions in this tenant.",
                    next_action=(
                        "Close the superseded recorded position version, then save the assignment again."
                    ),
                )
    visible = [
        version
        for version in assignment_visible
        if version.position_status_code in _STAFFABLE_POSITION_STATUSES
    ]
    if not visible or not _union_covers(
        [version.effective for version in visible],
        assignment.effective,
    ):
        raise PositionCoverageError(
            "Assignment is not covered by an active or open position version in this tenant.",
            next_action="Choose this tenant's staffable seat or shorten the assignment to open days.",
        )


def validate_position_seat_capacity(
    assignments: list[AssignmentFact],
    *,
    tenant_record_id: UUID,
    position_record_id: UUID,
    effective_on: date,
    known_at: datetime,
) -> None:
    """Reject a tenant seat whose visible allocations exceed 1.0000 on one day.

    Args:
        assignments: Candidate assignment facts, including other tenants and positions.
        tenant_record_id: Tenant namespace whose position capacity is reviewed.
        position_record_id: Seat whose FTE capacity is being reviewed.
        effective_on: The day whose split is being reviewed.
        known_at: The knowledge cutoff used for the review.

    Raises:
        PositionSeatError: Reduce one allocation so the seat total is at most 1.0000.
    """
    scoped = [
        fact
        for fact in assignments
        if fact.tenant_record_id == tenant_record_id
        and fact.position_record_id == position_record_id
    ]
    visible = resolve_bitemporal_facts(
        scoped,
        tenant_record_id=tenant_record_id,
        identity_of="position_record_id",
        identity_value=position_record_id,
        effective_on=effective_on,
        known_at=known_at,
    )
    total = sum((fact.allocation_ratio for fact in visible), start=_ZERO)
    if total > _ONE:
        raise PositionSeatError(
            "Visible allocations for one position exceed 1.0000.",
            next_action="Reduce one assignment so the seat total is at most 1.0000.",
        )


def _allocation_probe_days(
    assignments: list[AssignmentFact],
    target: DateInterval,
) -> list[date]:
    """Return start days that can change the visible allocation mix."""
    probe_days = {target.start}
    for fact in assignments:
        if fact.effective.overlaps(target) and target.contains(fact.effective.start):
            probe_days.add(fact.effective.start)
    return sorted(probe_days)


def validate_assignment_write(
    assignment: AssignmentFact,
    assignments: list[AssignmentFact],
    employment_versions: list[EmploymentVersion],
    position_versions: list[PositionVersion],
    *,
    known_at: datetime,
) -> None:
    """Reject an assignment that fails tenant-scoped employment, position, or FTE rules.

    Review the failure, correct the overlapping job or seat, then save again.
    """
    validate_assignment_employment_coverage(
        assignment,
        employment_versions,
        known_at=known_at,
    )
    validate_assignment_position_coverage(
        assignment,
        position_versions,
        known_at=known_at,
    )
    for probe_day in _allocation_probe_days(assignments, assignment.effective):
        validate_assignment_portfolio(
            assignments,
            tenant_record_id=assignment.tenant_record_id,
            person_record_id=assignment.person_record_id,
            employment_record_id=assignment.employment_record_id,
            effective_on=probe_day,
            known_at=known_at,
        )
        validate_position_seat_capacity(
            assignments,
            tenant_record_id=assignment.tenant_record_id,
            position_record_id=assignment.position_record_id,
            effective_on=probe_day,
            known_at=known_at,
        )
