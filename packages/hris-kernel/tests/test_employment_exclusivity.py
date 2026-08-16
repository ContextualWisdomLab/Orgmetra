"""Memorial Hospital cases for exclusive versus concurrent employment."""

from dataclasses import replace
from datetime import date
from uuid import UUID

import pytest

from orgmetra_hris_kernel import (
    EmploymentExclusivityError,
    validate_person_employment_exclusivity,
)

from .conftest import (
    JORDAN,
    JORDAN_EMPLOYMENT,
    RILEY,
    RILEY_EMPLOYMENT,
    TENANT,
    effective,
    utc,
)

FOREIGN_TENANT = UUID("20000000-0000-7000-8000-000000000101")


def test_second_exclusive_job_is_rejected_while_rn_employment_is_open(
    jordan_active_employment,
) -> None:
    """Jordan cannot hold two exclusive jobs on the same days."""
    clinic = replace(
        jordan_active_employment,
        employment_record_id=RILEY_EMPLOYMENT,
        employment_record_version_id=UUID("10000000-0000-7000-8000-000000000221"),
        effective=effective(date(2024, 4, 1)),
        employment_concurrency_code="exclusive",
    )
    with pytest.raises(EmploymentExclusivityError, match="exclusive"):
        validate_person_employment_exclusivity(
            [jordan_active_employment, clinic],
            tenant_record_id=TENANT,
            person_record_id=JORDAN,
            known_at=utc(2024, 4, 15),
        )


def test_foreign_tenant_exclusive_job_does_not_consume_local_slot(
    jordan_active_employment,
) -> None:
    """The same person identifier in another tenant cannot block a local employment."""
    foreign = replace(
        jordan_active_employment,
        tenant_record_id=FOREIGN_TENANT,
        employment_record_id=RILEY_EMPLOYMENT,
        employment_record_version_id=UUID("20000000-0000-7000-8000-000000000221"),
    )
    validate_person_employment_exclusivity(
        [jordan_active_employment, foreign],
        tenant_record_id=TENANT,
        person_record_id=JORDAN,
        known_at=utc(2024, 4, 15),
    )


def test_concurrent_second_job_is_accepted_beside_exclusive_rn(
    jordan_active_employment,
) -> None:
    """A marked concurrent clinic job may overlap the exclusive RN employment."""
    clinic = replace(
        jordan_active_employment,
        employment_record_id=RILEY_EMPLOYMENT,
        employment_record_version_id=UUID("10000000-0000-7000-8000-000000000222"),
        effective=effective(date(2024, 4, 1)),
        employment_concurrency_code="concurrent",
    )
    validate_person_employment_exclusivity(
        [jordan_active_employment, clinic],
        tenant_record_id=TENANT,
        person_record_id=JORDAN,
        known_at=utc(2024, 4, 15),
    )


def test_rehire_after_closed_exclusive_employment_is_accepted(
    jordan_active_employment,
) -> None:
    """A later exclusive employment is legal once the prior exclusive period ends."""
    closed = replace(
        jordan_active_employment,
        effective=effective(date(2024, 3, 1), date(2024, 6, 1)),
    )
    rehire = replace(
        jordan_active_employment,
        employment_record_id=RILEY_EMPLOYMENT,
        employment_record_version_id=UUID("10000000-0000-7000-8000-000000000223"),
        effective=effective(date(2024, 6, 1)),
    )
    validate_person_employment_exclusivity(
        [closed, rehire],
        tenant_record_id=TENANT,
        person_record_id=JORDAN,
        known_at=utc(2024, 6, 15),
    )


def test_unknown_concurrency_code_fails_closed(jordan_active_employment) -> None:
    """HR must choose exclusive or concurrent before the employment can be saved."""
    unknown = replace(jordan_active_employment, employment_concurrency_code="primary")
    with pytest.raises(EmploymentExclusivityError, match="concurrency"):
        validate_person_employment_exclusivity(
            [unknown],
            tenant_record_id=TENANT,
            person_record_id=JORDAN,
            known_at=utc(2024, 4, 15),
        )


def test_two_versions_of_one_exclusive_employment_remain_legal(
    jordan_active_employment,
) -> None:
    """Active-to-leave on the same employment is not a second exclusive job."""
    leave = replace(
        jordan_active_employment,
        employment_record_version_id=UUID("10000000-0000-7000-8000-000000000225"),
        employment_status_code="leave",
        effective=effective(date(2024, 5, 1)),
    )
    first = replace(
        jordan_active_employment,
        effective=effective(date(2024, 3, 1), date(2024, 5, 1)),
    )
    validate_person_employment_exclusivity(
        [first, leave],
        tenant_record_id=TENANT,
        person_record_id=JORDAN,
        known_at=utc(2024, 5, 15),
    )


def test_exclusivity_ignores_another_person(jordan_active_employment) -> None:
    """Riley's exclusive RN job does not consume Jordan's exclusive slot."""
    riley = replace(
        jordan_active_employment,
        employment_record_id=RILEY_EMPLOYMENT,
        person_record_id=RILEY,
        employment_record_version_id=UUID("10000000-0000-7000-8000-000000000224"),
    )
    validate_person_employment_exclusivity(
        [jordan_active_employment, riley],
        tenant_record_id=TENANT,
        person_record_id=JORDAN,
        known_at=utc(2024, 4, 15),
    )
    assert jordan_active_employment.employment_record_id == JORDAN_EMPLOYMENT
