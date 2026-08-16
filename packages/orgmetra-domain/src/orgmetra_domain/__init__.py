"""Public domain API for Orgmetra's bitemporal people and assignment core."""

from .assignment import AssignmentRecord, validate_assignment_portfolio
from .candidate import CandidateWorkerLink, CandidateWorkerRegistry
from .errors import (
    AllocationExceededError,
    CandidateWorkerRelinkError,
    InvalidDomainValueError,
    OrgmetraDomainError,
)
from .records import (
    EmploymentRecord,
    JobProfileRecord,
    JobProfileVersionRecord,
    OrganizationUnitRecord,
    OrganizationUnitVersionRecord,
    PersonNameRecord,
    PersonRecord,
    PositionRecord,
)
from .temporal import BitemporalPeriod

__all__ = [
    "AllocationExceededError",
    "AssignmentRecord",
    "BitemporalPeriod",
    "CandidateWorkerLink",
    "CandidateWorkerRegistry",
    "CandidateWorkerRelinkError",
    "EmploymentRecord",
    "InvalidDomainValueError",
    "JobProfileRecord",
    "JobProfileVersionRecord",
    "OrganizationUnitRecord",
    "OrganizationUnitVersionRecord",
    "OrgmetraDomainError",
    "PersonNameRecord",
    "PersonRecord",
    "PositionRecord",
    "validate_assignment_portfolio",
]
