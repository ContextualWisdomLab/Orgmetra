"""Stable error types exposed by the Orgmetra PostgreSQL adapter."""


class RepositoryError(RuntimeError):
    """Base class for errors raised by the persistence adapter."""


class RepositoryConflictError(RepositoryError):
    """Indicate that an immutable identity conflicts with existing data."""


class RepositoryUnavailableError(RepositoryError):
    """Indicate that PostgreSQL could not complete the requested operation."""
