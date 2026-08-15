"""Multiple-membership assignment records and portfolio validation."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable
from uuid import UUID

from .errors import AllocationExceededError, InvalidDomainValueError
from .temporal import BitemporalPeriod


@dataclass(frozen=True, slots=True)
class AssignmentRecord:
    """Allocate one person to one position over an effective interval."""

    assignment_record_id: UUID
    person_record_id: UUID
    position_record_id: UUID
    allocation_ratio: Decimal
    period: BitemporalPeriod

    def __post_init__(self) -> None:
        """Require a positive allocation that does not exceed full time."""

        if self.allocation_ratio <= 0 or self.allocation_ratio > 1:
            raise InvalidDomainValueError(
                "allocation_ratio must be greater than zero and no greater than one"
            )


def validate_assignment_portfolio(assignments: Iterable[AssignmentRecord]) -> None:
    """Reject overlapping assignments whose total allocation exceeds one.

    Effective intervals are treated as half-open. Therefore, an assignment
    ending on a date does not overlap another assignment starting that date.
    People are evaluated independently so multiple-membership modeling remains
    explicit rather than being collapsed into one primary assignment.
    """

    events_by_person: dict[UUID, list[tuple[date, int, Decimal]]] = defaultdict(list)
    for assignment in assignments:
        events_by_person[assignment.person_record_id].append(
            (assignment.period.effective_from, 1, assignment.allocation_ratio)
        )
        if assignment.period.effective_to is not None:
            events_by_person[assignment.person_record_id].append(
                (assignment.period.effective_to, 0, -assignment.allocation_ratio)
            )

    for person_record_id, events in events_by_person.items():
        allocated = Decimal("0")
        for effective_day, _event_order, delta in sorted(events):
            allocated += delta
            if allocated > 1:
                raise AllocationExceededError(
                    f"person {person_record_id} has allocation {allocated} "
                    f"on {effective_day}, exceeding 1"
                )
