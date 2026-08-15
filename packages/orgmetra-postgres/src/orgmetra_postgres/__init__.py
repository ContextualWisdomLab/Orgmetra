"""Public API for Orgmetra's purpose-bound PostgreSQL adapter."""

from .context import PurposeContext
from .errors import (
    RepositoryConflictError,
    RepositoryError,
    RepositoryUnavailableError,
)
from .models import AuditEvent, CandidateSnapshot, CandidateWorkerLink, PersonSnapshot
from .repository import PostgresPeopleRepository

__all__ = [
    "AuditEvent",
    "CandidateSnapshot",
    "CandidateWorkerLink",
    "PersonSnapshot",
    "PostgresPeopleRepository",
    "PurposeContext",
    "RepositoryConflictError",
    "RepositoryError",
    "RepositoryUnavailableError",
]
