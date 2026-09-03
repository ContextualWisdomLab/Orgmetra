"""Shared hospital fixtures for realistic employment-truth tests."""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from orgmetra_hris_kernel import (
    AssignmentFact,
    DateInterval,
    EmploymentVersion,
    RecordedInterval,
)

TENANT = UUID("10000000-0000-7000-8000-000000000101")
JORDAN = UUID("10000000-0000-7000-8000-000000000102")
RILEY = UUID("10000000-0000-7000-8000-000000000103")
JORDAN_EMPLOYMENT = UUID("10000000-0000-7000-8000-000000000104")
RILEY_EMPLOYMENT = UUID("10000000-0000-7000-8000-000000000105")
ICU_POSITION = UUID("10000000-0000-7000-8000-000000000106")
FLOAT_POSITION = UUID("10000000-0000-7000-8000-000000000107")


def utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    """Build a UTC instant used as a knowledge cutoff."""
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def recorded(start: datetime, end: datetime | None = None) -> RecordedInterval:
    """Build a recorded-time interval."""
    return RecordedInterval(start=start, end=end)


def effective(start: date, end: date | None = None) -> DateInterval:
    """Build an effective-time interval."""
    return DateInterval(start=start, end=end)


@pytest.fixture
def jordan_active_employment() -> EmploymentVersion:
    """Jordan Hale's open RN employment at Memorial Hospital."""
    return EmploymentVersion(
        tenant_record_id=TENANT,
        employment_record_id=JORDAN_EMPLOYMENT,
        employment_record_version_id=UUID("10000000-0000-7000-8000-000000000201"),
        person_record_id=JORDAN,
        employment_status_code="active",
        effective=effective(date(2024, 3, 1)),
        recorded=recorded(utc(2024, 3, 1, 15)),
    )


@pytest.fixture
def jordan_icu_assignment() -> AssignmentFact:
    """Jordan's original 0.8000 ICU allocation."""
    return AssignmentFact(
        tenant_record_id=TENANT,
        assignment_record_id=UUID("10000000-0000-7000-8000-000000000301"),
        employment_record_id=JORDAN_EMPLOYMENT,
        person_record_id=JORDAN,
        position_record_id=ICU_POSITION,
        allocation_ratio=Decimal("0.8000"),
        effective=effective(date(2024, 3, 1)),
        recorded=recorded(utc(2024, 3, 1, 16)),
        assignment_category_code="legacy_unspecified",
    )


@pytest.fixture
def jordan_float_assignment() -> AssignmentFact:
    """Jordan's original 0.2000 float-pool allocation."""
    return AssignmentFact(
        tenant_record_id=TENANT,
        assignment_record_id=UUID("10000000-0000-7000-8000-000000000302"),
        employment_record_id=JORDAN_EMPLOYMENT,
        person_record_id=JORDAN,
        position_record_id=FLOAT_POSITION,
        allocation_ratio=Decimal("0.2000"),
        effective=effective(date(2024, 3, 1)),
        recorded=recorded(utc(2024, 3, 1, 16)),
        assignment_category_code="legacy_unspecified",
    )
