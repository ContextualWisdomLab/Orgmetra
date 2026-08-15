"""Exercise fail-closed identity conflicts hidden by row-level security."""

from __future__ import annotations

from contextlib import nullcontext
from datetime import date
from typing import Any
from uuid import uuid4

import pytest

from orgmetra_postgres import (
    PostgresPeopleRepository,
    PurposeContext,
    RepositoryConflictError,
)


class _QueryResult:
    """Return one scripted row from a fake database query."""

    def __init__(self, row: tuple[Any, ...] | None) -> None:
        self._row = row

    def fetchone(self) -> tuple[Any, ...] | None:
        """Return the row configured for this query."""

        return self._row


class _ScriptedConnection:
    """Provide the minimal connection protocol used by the repository."""

    def __init__(self, rows: list[tuple[Any, ...] | None]) -> None:
        self._rows = iter(rows)

    def __enter__(self) -> _ScriptedConnection:
        """Enter the fake connection context."""

        return self

    def __exit__(self, *_args: object) -> None:
        """Leave the fake connection context without suppressing failures."""

        return None

    def transaction(self) -> nullcontext[_ScriptedConnection]:
        """Return a no-op transaction context for deterministic unit tests."""

        return nullcontext(self)

    def execute(self, statement: str, _parameters: object) -> _QueryResult:
        """Return no row for tenant binding and then scripted query rows."""

        if "set_config" in statement:
            return _QueryResult(None)
        return _QueryResult(next(self._rows))


def _context() -> PurposeContext:
    """Create one complete immutable purpose context."""

    return PurposeContext(
        tenant_reference=uuid4(),
        actor_reference=uuid4(),
        purpose_code="integration_test",
        correlation_reference=uuid4(),
    )


def _repository(*rows: tuple[Any, ...] | None) -> PostgresPeopleRepository:
    """Create a repository whose write conflict is invisible to the tenant."""

    connection = _ScriptedConnection(list(rows))
    return PostgresPeopleRepository(
        "postgresql://scripted/orgmetra",
        connect_factory=lambda *_args, **_kwargs: connection,  # type: ignore[arg-type]
    )


def test_hidden_tenant_identity_conflict_fails_closed() -> None:
    repository = _repository(None, None)

    with pytest.raises(RepositoryConflictError, match="different data"):
        repository.create_tenant(_context(), "Hidden Tenant")


def test_hidden_person_identity_conflict_fails_closed() -> None:
    repository = _repository(None, None)

    with pytest.raises(RepositoryConflictError, match="different data"):
        repository.create_person(
            _context(),
            person_record_id=uuid4(),
            display_name="Hidden Person",
            effective_from=date(2026, 8, 15),
        )


def test_hidden_candidate_identity_conflict_fails_closed() -> None:
    repository = _repository(None, None)

    with pytest.raises(RepositoryConflictError, match="different data"):
        repository.create_candidate(
            _context(),
            candidate_profile_id=uuid4(),
            application_status_code="applied",
        )


def test_hidden_candidate_link_conflict_fails_closed() -> None:
    repository = _repository(None, None)

    with pytest.raises(RepositoryConflictError, match="different worker"):
        repository.link_candidate_to_worker(
            _context(),
            candidate_profile_id=uuid4(),
            person_record_id=uuid4(),
        )
