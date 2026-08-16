"""Multiple-membership assignment records and portfolio validation."""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from .errors import (
    AllocationExceededError,
    InvalidDomainValueError,
    PositionAssignmentConflictError,
)
from .records import EmploymentRecord, EmploymentVersionRecord
from .temporal import BitemporalPeriod, _require_aware, resolve_bitemporal_facts_by_identity


@dataclass(frozen=True, slots=True)
class AssignmentRecord:
    """Allocate one person, through one employment, to one position."""

    assignment_record_id: UUID
    person_record_id: UUID
    employment_record_id: UUID
    position_record_id: UUID
    allocation_ratio: Decimal
    period: BitemporalPeriod

    def __post_init__(self) -> None:
        """Require one finite positive allocation that can persist as numeric(5,4)."""

        if (
            not self.allocation_ratio.is_finite()
            or self.allocation_ratio <= 0
            or self.allocation_ratio > 1
        ):
            raise InvalidDomainValueError(
                "allocation_ratio must be finite, greater than zero, and no greater than one"
            )
        if self.allocation_ratio.quantize(Decimal("0.0001")) != self.allocation_ratio:
            raise InvalidDomainValueError(
                "allocation_ratio must be finite with at most four decimal places"
            )


def _append_allocation_events(
    events: dict[UUID, list[tuple[date, int, Decimal]]],
    key: UUID,
    assignment: AssignmentRecord,
) -> None:
    """Record start and optional end events for one allocation sweep."""

    events[key].append(
        (assignment.period.effective_from, 1, assignment.allocation_ratio)
    )
    if assignment.period.effective_to is not None:
        events[key].append(
            (assignment.period.effective_to, 0, -assignment.allocation_ratio)
        )


def _reject_if_allocation_exceeds(
    events_by_key: dict[UUID, list[tuple[date, int, Decimal]]],
    error_type: type[AllocationExceededError] | type[PositionAssignmentConflictError],
    message: str,
) -> None:
    """Walk sorted half-open events and fail closed when allocation exceeds one."""

    for events in events_by_key.values():
        allocated = Decimal("0")
        for _effective_day, _event_order, delta in sorted(events):
            allocated += delta
            if allocated > 1:
                raise error_type(message)


def validate_assignment_portfolio(
    assignments: Iterable[AssignmentRecord],
    *,
    known_at: datetime,
) -> None:
    """Reject overlapping visible assignments whose total allocation exceeds one.

    Only rows known at ``known_at`` are counted, so a closed recorded interval
    does not inflate current FTE. People and positions are evaluated
    independently so multiple-membership and job-share remain explicit. The
    raised error is deliberately generic so adapters can expose it without
    leaking a person identifier, schedule date, or exact allocation ratio.
    Review overlapping rows and close the superseded recorded interval before
    saving a correction.
    """

    _require_aware(known_at, "known_at")
    visible = [
        assignment
        for assignment in assignments
        if assignment.period.was_known_at(known_at)
    ]
    events_by_person: dict[UUID, list[tuple[date, int, Decimal]]] = defaultdict(list)
    events_by_position: dict[UUID, list[tuple[date, int, Decimal]]] = defaultdict(list)
    for assignment in visible:
        _append_allocation_events(
            events_by_person, assignment.person_record_id, assignment
        )
        _append_allocation_events(
            events_by_position, assignment.position_record_id, assignment
        )
    _reject_if_allocation_exceeds(
        events_by_person,
        AllocationExceededError,
        "assignment portfolio allocation exceeds allowed maximum",
    )
    _reject_if_allocation_exceeds(
        events_by_position,
        PositionAssignmentConflictError,
        "position assignment allocation exceeds allowed maximum",
    )


def validate_assignment_portfolio_history(
    assignments: Iterable[AssignmentRecord],
) -> None:
    """Reject any recorded-time endpoint where a visible portfolio exceeds one.

    Write-time integrity checks every ``recorded_from`` and ``recorded_to``
    instant because that is when visibility changes. Close the superseded
    recorded interval before recording a correction.
    """

    materialized = tuple(assignments)
    moments: set[datetime] = set()
    for assignment in materialized:
        moments.add(assignment.period.recorded_from)
        if assignment.period.recorded_to is not None:
            moments.add(assignment.period.recorded_to)
    for moment in moments:
        validate_assignment_portfolio(materialized, known_at=moment)


def validate_assignment_employment_coverage(
    assignment: AssignmentRecord,
    employments: Iterable[EmploymentRecord],
    versions: Iterable[EmploymentVersionRecord],
    *,
    known_at: datetime,
) -> None:
    """Reject an assignment that is not covered by its named employment.

    The durable employment must belong to the same person, and the version
    visible at ``known_at`` must cover the assignment's effective interval.
    Attach the assignment to the employment that was in force, or correct the
    dates, before saving.
    """

    _require_aware(known_at, "known_at")
    anchors = {
        employment.employment_record_id: employment for employment in employments
    }
    anchor = anchors.get(assignment.employment_record_id)
    if anchor is None or anchor.person_record_id != assignment.person_record_id:
        raise InvalidDomainValueError(
            "assignment must reference a covering employment for the same person"
        )
    visible = resolve_bitemporal_facts_by_identity(
        [
            version
            for version in versions
            if version.employment_record_id == assignment.employment_record_id
        ],
        effective_on=assignment.period.effective_from,
        known_at=known_at,
        identity_of=lambda version: version.employment_record_id,
    )
    version = visible.get(assignment.employment_record_id)
    if version is None or not version.period.covers_effective_interval(assignment.period):
        raise InvalidDomainValueError(
            "assignment must reference a covering employment for the same person"
        )
