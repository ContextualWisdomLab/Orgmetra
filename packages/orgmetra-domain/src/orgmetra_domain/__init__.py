"""Public domain API for Orgmetra's bitemporal people and assignment core."""

from .assignment import (
    AssignmentRecord,
    validate_assignment_employment_coverage,
    validate_assignment_portfolio,
    validate_assignment_portfolio_history,
)
from .candidate import CandidateWorkerLink, CandidateWorkerRegistry
from .errors import (
    AllocationExceededError,
    CandidateWorkerRelinkError,
    InvalidDomainValueError,
    OrganizationCycleError,
    OrgmetraDomainError,
    PositionAssignmentConflictError,
    TemporalAmbiguityError,
)
from .records import (
    EmploymentRecord,
    EmploymentVersionRecord,
    JobProfileRecord,
    JobProfileVersionRecord,
    OrganizationUnitRecord,
    OrganizationUnitVersionRecord,
    PersonNameRecord,
    PersonRecord,
    PositionRecord,
    PositionVersionRecord,
    validate_organization_hierarchy,
)
from .temporal import (
    BitemporalPeriod,
    resolve_bitemporal_fact,
    resolve_bitemporal_facts_by_identity,
)

__all__ = [
    "AllocationExceededError",
    "AssignmentRecord",
    "BitemporalPeriod",
    "CandidateWorkerLink",
    "CandidateWorkerRegistry",
    "CandidateWorkerRelinkError",
    "EmploymentRecord",
    "EmploymentVersionRecord",
    "InvalidDomainValueError",
    "JobProfileRecord",
    "JobProfileVersionRecord",
    "OrganizationCycleError",
    "OrganizationUnitRecord",
    "OrganizationUnitVersionRecord",
    "OrgmetraDomainError",
    "PersonNameRecord",
    "PersonRecord",
    "PositionAssignmentConflictError",
    "PositionRecord",
    "PositionVersionRecord",
    "TemporalAmbiguityError",
    "resolve_bitemporal_fact",
    "resolve_bitemporal_facts_by_identity",
    "validate_assignment_employment_coverage",
    "validate_assignment_portfolio",
    "validate_assignment_portfolio_history",
    "validate_organization_hierarchy",
]
