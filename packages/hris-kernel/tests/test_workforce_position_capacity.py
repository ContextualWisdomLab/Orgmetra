"""Position-capacity regression for workforce composition."""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from orgmetra_hris_kernel import (
    AssignmentFact,
    DateInterval,
    EmploymentVersion,
    PositionSeatError,
    RecordedInterval,
)
from orgmetra_hris_kernel.workforce import build_workforce_composition_snapshot


def _id(value: int) -> UUID:
    """Return one stable opaque UUID fixture."""
    return UUID(int=value)


def test_snapshot_rejects_position_seat_overallocation() -> None:
    """Two workers cannot turn one overfilled seat into valid-looking aggregate FTE."""
    known = RecordedInterval(datetime(2026, 1, 1, tzinfo=timezone.utc))
    effective = DateInterval(date(2026, 1, 1))
    employments = [
        EmploymentVersion(_id(1), _id(101), _id(1001), _id(11), "active", effective, known),
        EmploymentVersion(_id(1), _id(102), _id(1002), _id(12), "active", effective, known),
    ]
    assignments = [
        AssignmentFact(
            _id(1),
            _id(201),
            _id(101),
            _id(11),
            _id(9001),
            Decimal("0.6000"),
            effective,
            known,
            "legacy_unspecified",
        ),
        AssignmentFact(
            _id(1),
            _id(202),
            _id(102),
            _id(12),
            _id(9001),
            Decimal("0.6000"),
            effective,
            known,
            "legacy_unspecified",
        ),
    ]

    with pytest.raises(PositionSeatError, match="exceed"):
        build_workforce_composition_snapshot(
            employments,
            assignments,
            tenant_record_id=_id(1),
            effective_on=date(2026, 1, 15),
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
        )
