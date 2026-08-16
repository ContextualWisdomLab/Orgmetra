"""Core HRIS records with stable anchors and separately versioned facts."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from .errors import InvalidDomainValueError, OrganizationCycleError
from .temporal import BitemporalPeriod, resolve_bitemporal_facts_by_identity


def _require_non_blank(value: str, field_name: str) -> str:
    """Return a normalized non-blank value or raise a domain validation error."""

    normalized = value.strip()
    if not normalized:
        raise InvalidDomainValueError(f"{field_name} must not be blank")
    return normalized


@dataclass(frozen=True, slots=True)
class PersonRecord:
    """Represent the durable HR person anchor without mutable attributes.

    Names and other descriptive facts are intentionally stored in versioned
    records so retroactive corrections never rewrite the durable identity.
    """

    person_record_id: UUID


@dataclass(frozen=True, slots=True)
class PersonNameRecord:
    """Represent one effective and system-recorded version of a person's name."""

    person_name_record_id: UUID
    person_record_id: UUID
    display_name: str
    period: BitemporalPeriod

    def __post_init__(self) -> None:
        """Normalize and validate the human-readable display name."""

        object.__setattr__(
            self, "display_name", _require_non_blank(self.display_name, "display_name")
        )


@dataclass(frozen=True, slots=True)
class EmploymentRecord:
    """Represent the durable employment relationship without mutable status.

    Status and effective dates live on ``EmploymentVersionRecord`` so a
    retroactive correction does not look like a second employment.
    """

    employment_record_id: UUID
    person_record_id: UUID


@dataclass(frozen=True, slots=True)
class EmploymentVersionRecord:
    """Represent one bitemporal status version of a durable employment."""

    employment_version_id: UUID
    employment_record_id: UUID
    employment_status_code: str
    period: BitemporalPeriod

    def __post_init__(self) -> None:
        """Normalize and validate the employment status code."""

        object.__setattr__(
            self,
            "employment_status_code",
            _require_non_blank(self.employment_status_code, "employment_status_code"),
        )


@dataclass(frozen=True, slots=True)
class OrganizationUnitRecord:
    """Represent a durable organizational identity without mutable attributes."""

    organization_unit_id: UUID


@dataclass(frozen=True, slots=True)
class OrganizationUnitVersionRecord:
    """Represent one bitemporal descriptive version of an organization unit.

    ``organization_unit_id`` is the durable identity referenced by positions.
    The version owns mutable name, type, and parent facts so retroactive
    corrections preserve both business time and Orgmetra's knowledge history.
    """

    organization_unit_version_id: UUID
    organization_unit_id: UUID
    unit_name: str
    organization_type_code: str
    period: BitemporalPeriod
    parent_organization_unit_id: UUID | None = None

    def __post_init__(self) -> None:
        """Normalize organization facts and reject an immediate self-parent."""

        object.__setattr__(self, "unit_name", _require_non_blank(self.unit_name, "unit_name"))
        object.__setattr__(
            self,
            "organization_type_code",
            _require_non_blank(self.organization_type_code, "organization_type_code"),
        )
        if self.parent_organization_unit_id == self.organization_unit_id:
            raise InvalidDomainValueError(
                "parent_organization_unit_id must reference another organization unit"
            )


@dataclass(frozen=True, slots=True)
class JobProfileRecord:
    """Represent a durable enterprise job identity without mutable attributes."""

    job_profile_id: UUID


@dataclass(frozen=True, slots=True)
class JobProfileVersionRecord:
    """Represent one bitemporal definition of work for a durable job profile."""

    job_profile_version_id: UUID
    job_profile_id: UUID
    job_title: str
    job_family_code: str
    job_version_code: str
    period: BitemporalPeriod

    def __post_init__(self) -> None:
        """Normalize and validate the job title, family, and version code."""

        object.__setattr__(
            self, "job_title", _require_non_blank(self.job_title, "job_title")
        )
        object.__setattr__(
            self,
            "job_family_code",
            _require_non_blank(self.job_family_code, "job_family_code"),
        )
        object.__setattr__(
            self,
            "job_version_code",
            _require_non_blank(self.job_version_code, "job_version_code"),
        )


@dataclass(frozen=True, slots=True)
class PositionRecord:
    """Represent a durable organizational seat that instantiates a job profile.

    Status and effective dates live on ``PositionVersionRecord`` so a
    retroactive correction does not look like a new seat.
    """

    position_record_id: UUID
    organization_unit_id: UUID
    job_profile_id: UUID


@dataclass(frozen=True, slots=True)
class PositionVersionRecord:
    """Represent one bitemporal status version of a durable position."""

    position_version_id: UUID
    position_record_id: UUID
    position_status_code: str
    period: BitemporalPeriod

    def __post_init__(self) -> None:
        """Normalize and validate the position status code."""

        object.__setattr__(
            self,
            "position_status_code",
            _require_non_blank(self.position_status_code, "position_status_code"),
        )


def validate_organization_hierarchy(
    versions: Iterable[OrganizationUnitVersionRecord],
    *,
    effective_on: date,
    known_at: datetime,
) -> None:
    """Reject a visible parent cycle such as A→B→A.

    Immediate self-parenting is already rejected at construction. Review the
    parent links and close the superseded recorded interval before saving.
    """

    visible = resolve_bitemporal_facts_by_identity(
        versions,
        effective_on=effective_on,
        known_at=known_at,
        identity_of=lambda version: version.organization_unit_id,
    )
    parents = {
        unit_id: version.parent_organization_unit_id
        for unit_id, version in visible.items()
    }
    for start in parents:
        seen: set[UUID] = set()
        current: UUID | None = start
        while current is not None:
            if current in seen:
                raise OrganizationCycleError(
                    "organization hierarchy contains a cycle; review parent links "
                    "and close the superseded recorded interval"
                )
            seen.add(current)
            current = parents.get(current)
