"""Public API for Orgmetra's purpose-bound PostgreSQL adapter."""

from .context import PurposeContext
from .errors import (
    RepositoryAuthorizationError,
    RepositoryConflictError,
    RepositoryError,
    RepositoryUnavailableError,
)
from .models import (
    AuditEvent,
    CandidateSnapshot,
    CandidateWorkerLink,
    EmploymentSnapshot,
    PersonSnapshot,
)
from .repository import PostgresPeopleRepository

__all__ = [
    "AuditEvent",
    "CandidateSnapshot",
    "CandidateWorkerLink",
    "EmploymentSnapshot",
    "PersonSnapshot",
    "PostgresPeopleRepository",
    "PurposeContext",
    "RepositoryAuthorizationError",
    "RepositoryConflictError",
    "RepositoryError",
    "RepositoryUnavailableError",
]
