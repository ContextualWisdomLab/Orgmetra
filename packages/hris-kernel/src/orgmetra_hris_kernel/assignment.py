"""Assignment portfolio and employment-coverage rules."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from orgmetra_hris_kernel.errors import AssignmentPortfolioError, EmploymentCoverageError
from orgmetra_hris_kernel.facts import AssignmentFact, EmploymentVersion
from orgmetra_hris_kernel.intervals import DateInterval
from orgmetra_hris_kernel.resolution import resolve_bitemporal_facts

_ONE = Decimal("1.0000")
_ZERO = Decimal("0")


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
    person_record_id: UUID,
    employment_record_id: UUID,
    effective_on: date,
    known_at: datetime,
) -> None:
    """Reject invalid ratios or a visible allocation total above 1.0000.

    Args:
        assignments: Candidate assignment facts, including other people.
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
        if fact.person_record_id == person_record_id
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
    """Require the assignment's person and days to match an active employment.

    Raises:
        EmploymentCoverageError: Link the correct employment or shorten the assignment.
    """
    named = [
        version
        for version in employment_versions
        if version.employment_record_id == assignment.employment_record_id
    ]
    if any(version.person_record_id != assignment.person_record_id for version in named):
        raise EmploymentCoverageError(
            "Assignment person does not match the named employment.",
            next_action="Select the employment that belongs to this worker, then save.",
        )
    visible = [
        version
        for version in named
        if version.recorded.contains(known_at)
    ]
    if not visible or not _union_covers(
        [version.effective for version in visible],
        assignment.effective,
    ):
        raise EmploymentCoverageError(
            "Assignment is not covered by an active employment version.",
            next_action="Shorten the assignment or restore an active employment that covers those days.",
        )
