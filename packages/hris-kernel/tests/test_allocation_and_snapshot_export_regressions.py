"""Review regressions for assignment precision and workforce evidence export."""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from orgmetra_hris_kernel import (
    AssignmentFact,
    AssignmentPortfolioError,
    DateInterval,
    PositionSeatError,
    RecordedInterval,
    SingleValuedFactError,
    WorkforceCompositionSnapshot,
    validate_assignment_portfolio,
    validate_position_seat_capacity,
)


def _id(value: int) -> UUID:
    """Return a stable opaque UUID fixture."""
    return UUID(int=value)


def _assignment(allocation_ratio: object) -> AssignmentFact:
    """Build one visible assignment using an untrusted caller allocation value."""
    return AssignmentFact(
        tenant_record_id=_id(1),
        assignment_record_id=_id(201),
        employment_record_id=_id(101),
        person_record_id=_id(11),
        position_record_id=_id(1201),
        allocation_ratio=allocation_ratio,  # type: ignore[arg-type]
        effective=DateInterval(date(2026, 1, 1)),
        recorded=RecordedInterval(datetime(2026, 1, 1, tzinfo=timezone.utc)),
    )


def _validate_portfolio(assignment: AssignmentFact) -> None:
    """Run the tenant-scoped portfolio boundary for one fixture assignment."""
    validate_assignment_portfolio(
        [assignment],
        tenant_record_id=_id(1),
        person_record_id=_id(11),
        employment_record_id=_id(101),
        effective_on=date(2026, 1, 15),
        known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
    )


def test_snapshot_export_rejects_post_construction_aggregate_mutation() -> None:
    """Canonical evidence must not emit aggregate state that bypassed construction checks."""
    snapshot = WorkforceCompositionSnapshot(
        tenant_record_id=_id(1),
        effective_on=date(2026, 1, 15),
        known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
        person_headcount=1,
        employment_count=1,
        staffed_assignment_count=0,
        staffed_fte=Decimal("0.0000"),
        unassigned_person_count=1,
        employment_status_counts=(("active", 1),),
    )

    object.__setattr__(snapshot, "staffed_fte", Decimal("0.5000"))

    with pytest.raises(SingleValuedFactError, match="internally inconsistent"):
        snapshot.canonical_json()


def test_portfolio_rejects_allocation_scale_beyond_four_decimal_places() -> None:
    """Direct kernel facts must fail closed before exact aggregation can amplify scale."""
    with pytest.raises(AssignmentPortfolioError, match="allocation_ratio"):
        _validate_portfolio(_assignment(Decimal("0.00001")))


def test_portfolio_rejects_nonfinite_allocation_ratio() -> None:
    """Non-finite Decimal values must become governed domain errors, not arithmetic faults."""
    with pytest.raises(AssignmentPortfolioError, match="allocation_ratio"):
        _validate_portfolio(_assignment(Decimal("NaN")))


def test_portfolio_rejects_non_decimal_allocation_ratio() -> None:
    """Only exact Decimal values may cross the HRIS allocation validation boundary."""
    with pytest.raises(AssignmentPortfolioError, match="allocation_ratio"):
        _validate_portfolio(_assignment("0.5000"))


def test_position_capacity_rejects_allocation_scale_beyond_four_decimal_places() -> None:
    """Seat-capacity validation must reject unsafe Decimal scale before exact aggregation."""
    assignment = _assignment(Decimal("0.00001"))

    with pytest.raises(PositionSeatError, match="allocation_ratio"):
        validate_position_seat_capacity(
            [assignment],
            tenant_record_id=_id(1),
            position_record_id=_id(1201),
            effective_on=date(2026, 1, 15),
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
        )
