"""Executable-capability integrity regressions for PostgreSQL Employment-history reads."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_people_api.postgres_employment_history import PostgresEmploymentHistoryReadPort

TENANT_ID = UUID("0198a415-9ab1-7000-8000-000000000001")
PERSON_ID = UUID("0198a415-9ab1-7000-8000-000000000002")
KNOWN_AT = datetime(2026, 9, 14, tzinfo=timezone.utc)


class _Cursor:
    """Provide the minimal DB-API surface for an empty Employment-history read."""

    def __enter__(self) -> _Cursor:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def execute(self, sql: str, parameters: object | None = None) -> None:
        """Accept parameterized statements without side effects."""
        del sql, parameters

    def fetchall(self) -> list[tuple[object, ...]]:
        """Return no Employment-history rows."""
        return []


class _Connection:
    """Provide one deterministic connection context."""

    def __enter__(self) -> _Connection:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def cursor(self) -> _Cursor:
        """Return the deterministic read cursor."""
        return _Cursor()


def test_validated_connection_factory_cannot_be_replaced_after_construction() -> None:
    """The capability accepted at construction must remain the capability used by the read."""
    accepted_calls = 0
    replacement_calls = 0

    def accepted_factory() -> _Connection:
        nonlocal accepted_calls
        accepted_calls += 1
        return _Connection()

    def replacement_factory() -> _Connection:
        nonlocal replacement_calls
        replacement_calls += 1
        raise AssertionError("replacement capability reached Employment-history persistence")

    port = PostgresEmploymentHistoryReadPort(accepted_factory)

    with pytest.raises(AttributeError):
        object.__setattr__(port, "connection_factory", replacement_factory)

    assert port.connection_factory is accepted_factory
    assert port.read_employment_history(
        tenant_record_id=TENANT_ID,
        person_record_id=PERSON_ID,
        known_at=KNOWN_AT,
    ) == ()
    assert accepted_calls == 1
    assert replacement_calls == 0
