"""Unit tests for purpose validation and database failure translation."""

from __future__ import annotations

from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg.errors import InsufficientPrivilege

from orgmetra_postgres import (
    PostgresPeopleRepository,
    PurposeContext,
    RepositoryAuthorizationError,
    RepositoryUnavailableError,
)


def _context(**overrides: object) -> PurposeContext:
    values: dict[str, object] = {
        "tenant_reference": uuid4(),
        "actor_reference": uuid4(),
        "purpose_code": "  workforce_admin  ",
        "correlation_reference": uuid4(),
        "decision_reference": None,
        "evidence_reference": "  evidence://case/1  ",
    }
    values.update(overrides)
    return PurposeContext(**values)  # type: ignore[arg-type]


def test_context_normalizes_bounded_text() -> None:
    context = _context()

    assert context.purpose_code == "workforce_admin"
    assert context.evidence_reference == "evidence://case/1"
    assert isinstance(context.tenant_reference, UUID)


@pytest.mark.parametrize(
    "value",
    ["", "   ", "x" * 65, "HR_Admin", "hr-admin", "café", "hr\nadmin"],
)
def test_context_rejects_invalid_purpose(value: str) -> None:
    with pytest.raises(ValueError, match="purpose_code"):
        _context(purpose_code=value)


@pytest.mark.parametrize(
    "value",
    ["", "   ", "x" * 513, "evidence://사례/1", "evidence://case/\n1", "bad\x7fref"],
)
def test_context_rejects_invalid_evidence_reference(value: str) -> None:
    with pytest.raises(ValueError, match="evidence_reference"):
        _context(evidence_reference=value)


def test_context_accepts_omitted_evidence_reference() -> None:
    assert _context(evidence_reference=None).evidence_reference is None


def test_repository_rejects_empty_dsn() -> None:
    with pytest.raises(ValueError, match="dsn"):
        PostgresPeopleRepository("   ")


def test_repository_translates_connection_failure() -> None:
    def unavailable_connection(*_args: object, **_kwargs: object) -> object:
        raise psycopg.OperationalError("database unavailable")

    repository = PostgresPeopleRepository(
        "postgresql://example.invalid/orgmetra",
        connect_factory=unavailable_connection,  # type: ignore[arg-type]
    )

    with pytest.raises(RepositoryUnavailableError, match="could not complete"):
        repository.get_person(_context(), uuid4())


def test_repository_translates_base_psycopg_error() -> None:
    """Translate the documented Psycopg root ``Error`` without import aliases."""

    def failed_connection(*_args: object, **_kwargs: object) -> object:
        raise psycopg.Error("generic database failure")

    repository = PostgresPeopleRepository(
        "postgresql://example.invalid/orgmetra",
        connect_factory=failed_connection,  # type: ignore[arg-type]
    )

    with pytest.raises(RepositoryUnavailableError, match="could not complete"):
        repository.get_person(_context(), uuid4())


def test_repository_translates_authorization_failure() -> None:
    def denied_connection(*_args: object, **_kwargs: object) -> object:
        raise InsufficientPrivilege("database role denied")

    repository = PostgresPeopleRepository(
        "postgresql://example.invalid/orgmetra",
        connect_factory=denied_connection,  # type: ignore[arg-type]
    )

    with pytest.raises(RepositoryAuthorizationError, match="denied"):
        repository.get_person(_context(), uuid4())
