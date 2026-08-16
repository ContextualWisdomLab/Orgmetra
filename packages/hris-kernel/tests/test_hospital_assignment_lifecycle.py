"""Realistic Memorial Hospital assignment correction across two knowledge cutoffs."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import UUID

from orgmetra_hris_kernel import (
    AssignmentFact,
    close_recorded_interval,
    resolve_bitemporal_facts,
    validate_assignment_employment_coverage,
    validate_assignment_portfolio,
)

from .conftest import (
    ICU_POSITION,
    JORDAN,
    JORDAN_EMPLOYMENT,
    effective,
    recorded,
    utc,
)


def test_june_correction_changes_may_history_only_after_it_is_recorded(
    jordan_active_employment,
    jordan_icu_assignment,
    jordan_float_assignment,
) -> None:
    """On 15 June HR learns Jordan was 1.0000 ICU from 1 April, not 0.8000 / 0.2000.

    Reconstruct 1 May twice:
    - known 1 June: still the original split
    - known 1 July: the corrected full-time ICU assignment
    """
    validate_assignment_employment_coverage(
        jordan_icu_assignment,
        [jordan_active_employment],
        known_at=utc(2024, 6, 1),
    )
    validate_assignment_portfolio(
        [jordan_icu_assignment, jordan_float_assignment],
        person_record_id=JORDAN,
        employment_record_id=JORDAN_EMPLOYMENT,
        effective_on=date(2024, 5, 1),
        known_at=utc(2024, 6, 1),
    )

    closed_icu = close_recorded_interval(jordan_icu_assignment, recorded_to=utc(2024, 6, 15, 10))
    closed_float = close_recorded_interval(
        jordan_float_assignment,
        recorded_to=utc(2024, 6, 15, 10),
    )
    corrected_icu = AssignmentFact(
        tenant_record_id=jordan_icu_assignment.tenant_record_id,
        assignment_record_id=UUID("10000000-0000-7000-8000-000000000305"),
        employment_record_id=JORDAN_EMPLOYMENT,
        person_record_id=JORDAN,
        position_record_id=ICU_POSITION,
        allocation_ratio=Decimal("1.0000"),
        effective=effective(date(2024, 4, 1)),
        recorded=recorded(utc(2024, 6, 15, 10)),
    )
    original_through_march = replace(
        jordan_icu_assignment,
        assignment_record_id=UUID("10000000-0000-7000-8000-000000000306"),
        effective=effective(date(2024, 3, 1), date(2024, 4, 1)),
        recorded=recorded(utc(2024, 6, 15, 10)),
    )
    original_float_through_march = replace(
        jordan_float_assignment,
        assignment_record_id=UUID("10000000-0000-7000-8000-000000000307"),
        effective=effective(date(2024, 3, 1), date(2024, 4, 1)),
        recorded=recorded(utc(2024, 6, 15, 10)),
    )
    history = [
        closed_icu,
        closed_float,
        original_through_march,
        original_float_through_march,
        corrected_icu,
    ]

    known_in_june = resolve_bitemporal_facts(
        history,
        identity_of="person_record_id",
        identity_value=JORDAN,
        effective_on=date(2024, 5, 1),
        known_at=utc(2024, 6, 1),
    )
    assert {(item.position_record_id, item.allocation_ratio) for item in known_in_june} == {
        (jordan_icu_assignment.position_record_id, Decimal("0.8000")),
        (jordan_float_assignment.position_record_id, Decimal("0.2000")),
    }

    known_in_july = resolve_bitemporal_facts(
        history,
        identity_of="person_record_id",
        identity_value=JORDAN,
        effective_on=date(2024, 5, 1),
        known_at=utc(2024, 7, 1),
    )
    assert [(item.position_record_id, item.allocation_ratio) for item in known_in_july] == [
        (ICU_POSITION, Decimal("1.0000"))
    ]
    validate_assignment_portfolio(
        known_in_july,
        person_record_id=JORDAN,
        employment_record_id=JORDAN_EMPLOYMENT,
        effective_on=date(2024, 5, 1),
        known_at=utc(2024, 7, 1),
    )
