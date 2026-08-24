"""Immutable employment, absence, organization, position, and assignment facts."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from orgmetra_hris_kernel.intervals import DateInterval, RecordedInterval

IDENTITY_FIELDS = frozenset(
    {
        "tenant_record_id",
        "employment_record_id",
        "employment_absence_record_id",
        "person_record_id",
        "organization_unit_id",
        "position_record_id",
        "assignment_record_id",
        "employment_record_version_id",
        "employment_absence_version_id",
        "organization_unit_version_id",
        "position_record_version_id",
    }
)


@dataclass(frozen=True, slots=True)
class EmploymentVersion:
    """One recorded version of a durable employment relationship."""

    tenant_record_id: UUID
    employment_record_id: UUID
    employment_record_version_id: UUID
    person_record_id: UUID
    employment_status_code: str
    effective: DateInterval
    recorded: RecordedInterval
    employment_concurrency_code: str = "exclusive"


@dataclass(frozen=True, slots=True)
class EmploymentAbsenceVersion:
    """One reason-free recorded version of an Employment absence period.

    The fact intentionally records *that* one Employment is absent, not why.
    Sensitive case, medical, family, statutory, or free-form leave details belong
    behind a separate purpose-bound case boundary rather than this workforce fact.
    """

    tenant_record_id: UUID
    employment_absence_record_id: UUID
    employment_absence_version_id: UUID
    employment_record_id: UUID
    person_record_id: UUID
    absence_status_code: str
    effective: DateInterval
    recorded: RecordedInterval


@dataclass(frozen=True, slots=True)
class OrganizationUnitVersion:
    """One recorded parent-link version of a durable organization unit."""

    tenant_record_id: UUID
    organization_unit_id: UUID
    organization_unit_version_id: UUID
    parent_organization_unit_id: UUID | None
    effective: DateInterval
    recorded: RecordedInterval


@dataclass(frozen=True, slots=True)
class PositionVersion:
    """One recorded version of a durable position seat."""

    tenant_record_id: UUID
    position_record_id: UUID
    position_record_version_id: UUID
    position_status_code: str
    effective: DateInterval
    recorded: RecordedInterval


@dataclass(frozen=True, slots=True)
class AssignmentFact:
    """One recorded assignment of a person, through one employment, to a position."""

    tenant_record_id: UUID
    assignment_record_id: UUID
    employment_record_id: UUID
    person_record_id: UUID
    position_record_id: UUID
    allocation_ratio: Decimal
    effective: DateInterval
    recorded: RecordedInterval
