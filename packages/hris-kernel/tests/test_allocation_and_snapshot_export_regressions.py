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


def _staffed_snapshot(staffed_fte: Decimal) -> WorkforceCompositionSnapshot:
    """Build one directly constructed, otherwise valid staffed snapshot."""
    return WorkforceCompositionSnapshot(
        tenant_record_id=_id(1),
        effective_on=date(2026, 1, 15),
        known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
        person_headcount=1,
        employment_count=1,
        staffed_assignment_count=1,
        staffed_fte=staffed_fte,
        unassigned_person_count=0,
        employment_status_counts=(("active", 1),),
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


def test_direct_snapshot_rejects_fte_scale_beyond_four_decimal_places() -> None:
    """Every accepted direct FTE must remain bounded for exact comparison arithmetic."""
    with pytest.raises(SingleValuedFactError, match="staffed FTE"):
        _staffed_snapshot(Decimal("1E-5000"))


def test_direct_snapshot_canonicalizes_equivalent_fte_scales() -> None:
    """Equivalent FTE values must emit one canonical four-decimal evidence representation."""
    compact = _staffed_snapshot(Decimal("0.5"))
    fixed_scale = _staffed_snapshot(Decimal("0.5000"))

    assert compact.staffed_fte == Decimal("0.5000")
    assert compact.staffed_fte.as_tuple().exponent == -4
    assert compact.canonical_json() == fixed_scale.canonical_json()
    assert compact.content_digest() == fixed_scale.content_digest()


def test_snapshot_export_rejects_post_construction_fte_scale_mutation() -> None:
    """Canonical export must reject equivalent values whose governed FTE scale was bypassed."""
    snapshot = _staffed_snapshot(Decimal("0.5000"))
    object.__setattr__(snapshot, "staffed_fte", Decimal("0.5"))

    with pytest.raises(SingleValuedFactError, match="canonical four-decimal"):
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
