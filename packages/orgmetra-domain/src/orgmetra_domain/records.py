"""Core HRIS records with stable anchors and separately versioned facts."""

from dataclasses import dataclass
from uuid import UUID

from .errors import InvalidDomainValueError
from .temporal import BitemporalPeriod


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
    """Represent one effective-dated employment relationship for a person."""

    employment_record_id: UUID
    person_record_id: UUID
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
    """Represent one bitemporal version of an organizational unit.

    The stable ``organization_unit_id`` can be reused by successive versions
    while name, type, parent relationship, and bitemporal period describe the
    fact that was effective in the business and known by Orgmetra at that time.
    """

    organization_unit_id: UUID
    organization_unit_name: str
    organization_type_code: str
    period: BitemporalPeriod
    parent_organization_unit_id: UUID | None = None

    def __post_init__(self) -> None:
        """Normalize and validate organization display and classification values."""

        object.__setattr__(
            self,
            "organization_unit_name",
            _require_non_blank(self.organization_unit_name, "organization_unit_name"),
        )
        object.__setattr__(
            self,
            "organization_type_code",
            _require_non_blank(self.organization_type_code, "organization_type_code"),
        )


@dataclass(frozen=True, slots=True)
class JobProfileRecord:
    """Represent one bitemporal version of an enterprise job definition.

    Jobs describe work independently of organizational seats. Positions refer
    to the stable ``job_profile_id`` while title and family remain correctable
    through effective-time and system-recorded-time versions.
    """

    job_profile_id: UUID
    job_title: str
    job_family_code: str
    period: BitemporalPeriod

    def __post_init__(self) -> None:
        """Normalize and validate the job title and family classification."""

        object.__setattr__(
            self, "job_title", _require_non_blank(self.job_title, "job_title")
        )
        object.__setattr__(
            self,
            "job_family_code",
            _require_non_blank(self.job_family_code, "job_family_code"),
        )


@dataclass(frozen=True, slots=True)
class PositionRecord:
    """Represent an organizational seat that instantiates a versioned job profile."""

    position_record_id: UUID
    organization_unit_id: UUID
    job_profile_id: UUID
    position_status_code: str
    period: BitemporalPeriod

    def __post_init__(self) -> None:
        """Normalize and validate the position status code."""

        object.__setattr__(
            self,
            "position_status_code",
            _require_non_blank(self.position_status_code, "position_status_code"),
        )
