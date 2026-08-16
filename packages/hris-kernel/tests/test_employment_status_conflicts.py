"""Employment coverage must fail closed on contradictory visible status facts."""

from dataclasses import replace
from datetime import date
from uuid import UUID

import pytest

from orgmetra_hris_kernel import (
    EmploymentCoverageError,
    validate_assignment_employment_coverage,
)

from .conftest import effective, recorded, utc


def test_assignment_rejects_simultaneously_visible_active_and_terminated_versions(
    jordan_icu_assignment,
    jordan_active_employment,
) -> None:
    """A contradictory terminal status cannot be filtered away as if it never existed."""
    terminated = replace(
        jordan_active_employment,
        employment_record_version_id=UUID("10000000-0000-7000-8000-000000000202"),
        employment_status_code="terminated",
    )

    with pytest.raises(EmploymentCoverageError, match="employment"):
        validate_assignment_employment_coverage(
            jordan_icu_assignment,
            [jordan_active_employment, terminated],
            known_at=utc(2024, 5, 1),
        )


def test_assignment_accepts_adjacent_active_then_leave_coverage(
    jordan_icu_assignment,
    jordan_active_employment,
) -> None:
    """A legitimate status transition remains valid when each day has one visible status."""
    assignment = replace(
        jordan_icu_assignment,
        effective=effective(date(2024, 3, 1), date(2024, 7, 1)),
    )
    active = replace(
        jordan_active_employment,
        effective=effective(date(2024, 3, 1), date(2024, 6, 1)),
    )
    leave = replace(
        jordan_active_employment,
        employment_record_version_id=UUID("10000000-0000-7000-8000-000000000203"),
        employment_status_code="leave",
        effective=effective(date(2024, 6, 1), date(2024, 7, 1)),
        recorded=recorded(utc(2024, 5, 20)),
    )

    validate_assignment_employment_coverage(
        assignment,
        [active, leave],
        known_at=utc(2024, 6, 15),
    )
