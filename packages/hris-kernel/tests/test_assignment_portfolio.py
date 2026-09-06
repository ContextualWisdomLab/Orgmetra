"""Assignment portfolio and employment-coverage tests."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from orgmetra_hris_kernel import (
    AssignmentFact,
    AssignmentPortfolioError,
    EmploymentCoverageError,
    validate_assignment_employment_coverage,
    validate_assignment_portfolio,
)

from .conftest import (
    FLOAT_POSITION,
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

FOREIGN_TENANT = UUID("20000000-0000-7000-8000-000000000101")


def test_portfolio_accepts_split_icu_and_float_allocations(
    jordan_icu_assignment,
    jordan_float_assignment,
) -> None:
    """A 0.8000 / 0.2000 split is a legal multiple-membership assignment."""
    validate_assignment_portfolio(
        [jordan_icu_assignment, jordan_float_assignment],
        tenant_record_id=TENANT,
        person_record_id=JORDAN,
        employment_record_id=JORDAN_EMPLOYMENT,
        effective_on=date(2024, 5, 1),
        known_at=utc(2024, 5, 1),
    )


def test_portfolio_rejects_allocation_above_one_for_one_employment(
    jordan_icu_assignment,
    jordan_float_assignment,
) -> None:
    """HR must reduce one allocation before saving a second full-time assignment."""
    extra = replace(
        jordan_float_assignment,
        assignment_record_id=UUID("10000000-0000-7000-8000-000000000303"),
        allocation_ratio=Decimal("0.3000"),
    )
    with pytest.raises(AssignmentPortfolioError, match="1.0000"):
        validate_assignment_portfolio(
            [jordan_icu_assignment, jordan_float_assignment, extra],
            tenant_record_id=TENANT,
            person_record_id=JORDAN,
            employment_record_id=JORDAN_EMPLOYMENT,
            effective_on=date(2024, 5, 1),
            known_at=utc(2024, 5, 1),
        )


def test_portfolio_ignores_another_person_and_another_employment(
    jordan_icu_assignment,
) -> None:
    """Riley's full-time ICU seat does not consume Jordan's allocation budget."""
    riley = AssignmentFact(
        tenant_record_id=jordan_icu_assignment.tenant_record_id,
        assignment_record_id=UUID("10000000-0000-7000-8000-000000000304"),
        employment_record_id=RILEY_EMPLOYMENT,
        person_record_id=RILEY,
        position_record_id=ICU_POSITION,
        allocation_ratio=Decimal("1.0000"),
        effective=effective(date(2024, 3, 1)),
        recorded=recorded(utc(2024, 3, 1, 16)),
        assignment_category_code="legacy_unspecified",
    )
    validate_assignment_portfolio(
        [jordan_icu_assignment, riley],
        tenant_record_id=TENANT,
        person_record_id=JORDAN,
        employment_record_id=JORDAN_EMPLOYMENT,
        effective_on=date(2024, 5, 1),
        known_at=utc(2024, 5, 1),
    )


def test_portfolio_ignores_same_ids_from_another_tenant(jordan_icu_assignment) -> None:
    """A foreign tenant cannot consume this tenant's employment allocation budget."""
    foreign = replace(
        jordan_icu_assignment,
        tenant_record_id=FOREIGN_TENANT,
        assignment_record_id=UUID("20000000-0000-7000-8000-000000000301"),
        allocation_ratio=Decimal("0.8000"),
    )
    validate_assignment_portfolio(
        [jordan_icu_assignment, foreign],
        tenant_record_id=TENANT,
        person_record_id=JORDAN,
        employment_record_id=JORDAN_EMPLOYMENT,
        effective_on=date(2024, 5, 1),
        known_at=utc(2024, 5, 1),
    )


def test_portfolio_rejects_non_positive_or_oversized_ratio(jordan_icu_assignment) -> None:
    """Each assignment row must stay inside (0, 1.0000]."""
    zero = replace(jordan_icu_assignment, allocation_ratio=Decimal("0"))
    huge = replace(jordan_icu_assignment, allocation_ratio=Decimal("1.0001"))
    with pytest.raises(AssignmentPortfolioError, match="allocation_ratio"):
        validate_assignment_portfolio(
            [zero],
            tenant_record_id=TENANT,
            person_record_id=JORDAN,
            employment_record_id=JORDAN_EMPLOYMENT,
            effective_on=date(2024, 5, 1),
            known_at=utc(2024, 5, 1),
        )
    with pytest.raises(AssignmentPortfolioError, match="allocation_ratio"):
        validate_assignment_portfolio(
            [huge],
            tenant_record_id=TENANT,
            person_record_id=JORDAN,
            employment_record_id=JORDAN_EMPLOYMENT,
            effective_on=date(2024, 5, 1),
            known_at=utc(2024, 5, 1),
        )



def test_portfolio_rejects_ungoverned_assignment_categories(
    jordan_icu_assignment,
) -> None:
    """HR must choose a governed string category before saving an assignment."""
    invalid_type = replace(jordan_icu_assignment, assignment_category_code=1)
    invalid_code = replace(jordan_icu_assignment, assignment_category_code="lead")

    for invalid in (invalid_type, invalid_code):
        with pytest.raises(AssignmentPortfolioError, match="classification"):
            validate_assignment_portfolio(
                [invalid],
                tenant_record_id=TENANT,
                person_record_id=JORDAN,
                employment_record_id=JORDAN_EMPLOYMENT,
                effective_on=date(2024, 5, 1),
                known_at=utc(2024, 5, 1),
            )


def test_portfolio_rejects_two_visible_primary_assignments(
    jordan_icu_assignment,
    jordan_float_assignment,
) -> None:
    """HR must keep one primary and mark simultaneous additional work secondary."""
    primary_icu = replace(jordan_icu_assignment, assignment_category_code="primary")
    primary_float = replace(
        jordan_float_assignment,
        assignment_category_code="primary",
    )

    with pytest.raises(AssignmentPortfolioError, match="two visible primary"):
        validate_assignment_portfolio(
            [primary_icu, primary_float],
            tenant_record_id=TENANT,
            person_record_id=JORDAN,
            employment_record_id=JORDAN_EMPLOYMENT,
            effective_on=date(2024, 5, 1),
            known_at=utc(2024, 5, 1),
        )


def test_assignment_requires_covering_active_employment(
    jordan_icu_assignment,
    jordan_active_employment,
) -> None:
    """Do not assign a worker on days their employment is not active."""
    validate_assignment_employment_coverage(
        jordan_icu_assignment,
        [jordan_active_employment],
        known_at=utc(2024, 5, 1),
    )
    closed = replace(
        jordan_active_employment,
        effective=effective(date(2024, 3, 1), date(2024, 4, 1)),
    )
    with pytest.raises(EmploymentCoverageError, match="employment"):
        validate_assignment_employment_coverage(
            jordan_icu_assignment,
            [closed],
            known_at=utc(2024, 5, 1),
        )


def test_assignment_allows_leave_but_rejects_terminated_employment(
    jordan_icu_assignment,
    jordan_active_employment,
) -> None:
    """Leave preserves staffing coverage, while termination ends it."""
    leave = replace(jordan_active_employment, employment_status_code="leave")
    validate_assignment_employment_coverage(
        jordan_icu_assignment,
        [leave],
        known_at=utc(2024, 5, 1),
    )
    terminated = replace(jordan_active_employment, employment_status_code="terminated")
    with pytest.raises(EmploymentCoverageError, match="employment"):
        validate_assignment_employment_coverage(
            jordan_icu_assignment,
            [terminated],
            known_at=utc(2024, 5, 1),
        )


def test_assignment_rejects_foreign_tenant_employment_coverage(
    jordan_icu_assignment,
    jordan_active_employment,
) -> None:
    """An employment in another tenant cannot authorize this tenant's assignment."""
    foreign = replace(jordan_active_employment, tenant_record_id=FOREIGN_TENANT)
    with pytest.raises(EmploymentCoverageError, match="employment"):
        validate_assignment_employment_coverage(
            jordan_icu_assignment,
            [foreign],
            known_at=utc(2024, 5, 1),
        )


def test_assignment_rejects_person_employment_mismatch(
    jordan_icu_assignment,
    jordan_active_employment,
) -> None:
    """An assignment cannot borrow another worker's employment identity."""
    mismatched = replace(jordan_icu_assignment, person_record_id=RILEY)
    with pytest.raises(EmploymentCoverageError, match="person"):
        validate_assignment_employment_coverage(
            mismatched,
            [jordan_active_employment],
            known_at=utc(2024, 5, 1),
        )


def test_assignment_finite_range_is_covered_by_adjacent_employment_versions(
    jordan_icu_assignment,
    jordan_active_employment,
) -> None:
    """Two adjacent employment versions can cover one assignment without a gap."""
    first = replace(
        jordan_active_employment,
        effective=effective(date(2024, 3, 1), date(2024, 4, 1)),
    )
    second = replace(
        jordan_active_employment,
        employment_record_version_id=UUID("10000000-0000-7000-8000-000000000205"),
        effective=effective(date(2024, 4, 1)),
    )
    bounded = replace(
        jordan_icu_assignment,
        effective=effective(date(2024, 3, 1), date(2024, 5, 1)),
    )
    validate_assignment_employment_coverage(
        bounded,
        [first, second],
        known_at=utc(2024, 5, 1),
    )
    still_open = replace(
        jordan_icu_assignment,
        effective=effective(date(2024, 3, 1)),
    )
    validate_assignment_employment_coverage(
        still_open,
        [first, second],
        known_at=utc(2024, 5, 1),
    )
    finite_cover = replace(
        jordan_active_employment,
        effective=effective(date(2024, 3, 1), date(2024, 6, 1)),
    )
    validate_assignment_employment_coverage(
        bounded,
        [finite_cover],
        known_at=utc(2024, 5, 1),
    )


def test_assignment_ignores_unrelated_employment_when_checking_coverage(
    jordan_icu_assignment,
    jordan_active_employment,
) -> None:
    """Coverage uses only the employment named on the assignment."""
    riley_employment = replace(
        jordan_active_employment,
        employment_record_id=RILEY_EMPLOYMENT,
        person_record_id=RILEY,
        employment_record_version_id=UUID("10000000-0000-7000-8000-000000000204"),
    )
    validate_assignment_employment_coverage(
        jordan_icu_assignment,
        [riley_employment, jordan_active_employment],
        known_at=utc(2024, 5, 1),
    )
    assert FLOAT_POSITION != ICU_POSITION
