"""Domain-specific failures raised by Orgmetra's HRIS core."""


class OrgmetraDomainError(ValueError):
    """Base class for invalid or conflicting Orgmetra domain operations."""


class InvalidDomainValueError(OrgmetraDomainError):
    """Raised when a value violates a stable HRIS domain invariant."""


class TemporalAmbiguityError(OrgmetraDomainError):
    """Raised when more than one fact is visible at one bitemporal coordinate."""


class AllocationExceededError(OrgmetraDomainError):
    """Raised when a person's overlapping assignment allocation exceeds one."""


class CandidateWorkerRelinkError(OrgmetraDomainError):
    """Raised when an append-only candidate link targets a different person."""
