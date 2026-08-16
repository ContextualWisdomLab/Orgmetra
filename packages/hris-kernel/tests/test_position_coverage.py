"""Memorial Hospital cases for staffable positions and exclusive seats."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from orgmetra_hris_kernel import (
    PositionCoverageError,
    PositionSeatError,
    PositionVersion,
    validate_assignment_position_coverage,
    validate_assignment_write,
    validate_position_seat_capacity,
)

from .conftest import (
    ICU_POSITION,
    JORDAN,
    JORDAN_EMPLOYMENT,
    RILEY,
    RILEY_EMPLOYMENT,
    TENANT,
    effective,
    recorded,
    utc,
)


def _open_icu() -> PositionVersion:
    """Return the open Memorial ICU RN seat."""
    return PositionVersion(
        tenant_record_id=TENANT,
        position_record_id=ICU_POSITION,
        position_record_version_id=UUID("10000000-0000-7000-8000-000000000401"),
        position_status_code="active",
        effective=effective(date(2024, 1, 1)),
        recorded=recorded(utc(2024, 1, 1, 8)),
    )


def test_assignment_requires_an_open_or_active_position(
    jordan_icu_assignment,
) -> None:
    """Do not staff a closed ICU seat."""
    validate_assignment_position_coverage(
        jordan_icu_assignment,
        [_open_icu()],
        known_at=utc(2024, 5, 1),
    )
    closed = replace(_open_icu(), position_status_code="closed")
    with pytest.raises(PositionCoverageError, match="position"):
        validate_assignment_position_coverage(
            jordan_icu_assignment,
            [closed],
            known_at=utc(2024, 5, 1),
        )


def test_assignment_rejects_days_after_the_icu_seat_closes(
    jordan_icu_assignment,
) -> None:
    """A June freeze cannot hide behind an assignment that started in March."""
    open_then_closed = [
        replace(_open_icu(), effective=effective(date(2024, 1, 1), date(2024, 6, 1))),
        replace(
            _open_icu(),
            position_record_version_id=UUID("10000000-0000-7000-8000-000000000402"),
            position_status_code="frozen",
            effective=effective(date(2024, 6, 1)),
        ),
    ]
    with pytest.raises(PositionCoverageError, match="position"):
        validate_assignment_position_coverage(
            jordan_icu_assignment,
            open_then_closed,
            known_at=utc(2024, 6, 15),
        )


def test_riley_cannot_take_a_full_icu_seat_already_held_by_jordan(
    jordan_icu_assignment,
) -> None:
    """Two people cannot consume more than 1.0000 of one exclusive seat."""
    riley = replace(
        jordan_icu_assignment,
        assignment_record_id=UUID("10000000-0000-7000-8000-000000000308"),
        employment_record_id=RILEY_EMPLOYMENT,
        person_record_id=RILEY,
        allocation_ratio=Decimal("1.0000"),
        effective=effective(date(2024, 4, 1)),
    )
    with pytest.raises(PositionSeatError, match="1.0000"):
        validate_position_seat_capacity(
            [jordan_icu_assignment, riley],
            position_record_id=ICU_POSITION,
            effective_on=date(2024, 4, 15),
            known_at=utc(2024, 4, 15),
        )


def test_open_status_is_staffable_and_unrelated_seats_are_ignored(
    jordan_icu_assignment,
) -> None:
    """Coverage uses only the named seat, including an `open` status."""
    other_seat = replace(
        _open_icu(),
        position_record_id=UUID("10000000-0000-7000-8000-000000000108"),
        position_record_version_id=UUID("10000000-0000-7000-8000-000000000403"),
        position_status_code="closed",
    )
    open_icu = replace(_open_icu(), position_status_code="open")
    validate_assignment_position_coverage(
        jordan_icu_assignment,
        [other_seat, open_icu],
        known_at=utc(2024, 5, 1),
    )


def test_float_allocation_does_not_consume_icu_seat_capacity(
    jordan_icu_assignment,
    jordan_float_assignment,
) -> None:
    """Jordan's 0.2000 float row is not part of the ICU 1.0000 budget."""
    validate_position_seat_capacity(
        [jordan_icu_assignment, jordan_float_assignment],
        position_record_id=ICU_POSITION,
        effective_on=date(2024, 5, 1),
        known_at=utc(2024, 5, 1),
    )


def test_riley_may_take_the_remaining_icu_allocation(
    jordan_icu_assignment,
) -> None:
    """Jordan's 0.8000 ICU seat leaves 0.2000 for Riley."""
    riley = replace(
        jordan_icu_assignment,
        assignment_record_id=UUID("10000000-0000-7000-8000-000000000309"),
        employment_record_id=RILEY_EMPLOYMENT,
        person_record_id=RILEY,
        allocation_ratio=Decimal("0.2000"),
        effective=effective(date(2024, 4, 1)),
    )
    validate_position_seat_capacity(
        [jordan_icu_assignment, riley],
        position_record_id=ICU_POSITION,
        effective_on=date(2024, 4, 15),
        known_at=utc(2024, 4, 15),
    )


def test_assignment_write_composes_employment_position_and_seat_rules(
    jordan_icu_assignment,
    jordan_float_assignment,
    jordan_active_employment,
) -> None:
    """One write path must reject a closed seat even when employment coverage is valid."""
    validate_assignment_write(
        jordan_icu_assignment,
        [jordan_icu_assignment, jordan_float_assignment],
        [jordan_active_employment],
        [_open_icu()],
        known_at=utc(2024, 5, 1),
    )
    with pytest.raises(PositionCoverageError, match="position"):
        validate_assignment_write(
            jordan_icu_assignment,
            [jordan_icu_assignment, jordan_float_assignment],
            [jordan_active_employment],
            [replace(_open_icu(), position_status_code="abolished")],
            known_at=utc(2024, 5, 1),
        )
    riley = replace(
        jordan_icu_assignment,
        assignment_record_id=UUID("10000000-0000-7000-8000-000000000310"),
        employment_record_id=RILEY_EMPLOYMENT,
        person_record_id=RILEY,
        allocation_ratio=Decimal("1.0000"),
        effective=effective(date(2024, 4, 1)),
    )
    riley_employment = replace(
        jordan_active_employment,
        employment_record_id=RILEY_EMPLOYMENT,
        person_record_id=RILEY,
        employment_record_version_id=UUID("10000000-0000-7000-8000-000000000226"),
    )
    with pytest.raises(PositionSeatError, match="1.0000"):
        validate_assignment_write(
            riley,
            [jordan_icu_assignment, riley],
            [riley_employment],
            [_open_icu()],
            known_at=utc(2024, 4, 15),
        )
    assert jordan_icu_assignment.person_record_id == JORDAN
    assert jordan_icu_assignment.employment_record_id == JORDAN_EMPLOYMENT
