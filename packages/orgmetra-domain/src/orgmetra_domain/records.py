"""Core HRIS records that preserve distinct person, employment, and position facts."""

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
    """Represent a durable HR person independently from login credentials."""

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
