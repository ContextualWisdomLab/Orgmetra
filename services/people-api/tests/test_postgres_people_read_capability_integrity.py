"""Executable-capability integrity regressions for PostgreSQL People reads."""

from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest

from orgmetra_people_api.postgres import PostgresPeopleReadPort

TENANT = UUID("0198a412-6000-7000-8000-000000000001")
PERSON = UUID("0198a412-6000-7000-8000-000000000010")
EFFECTIVE_ON = date(2026, 9, 9)


class _Cursor:
    """Provide the minimal DB-API surface for an empty authorized read."""

    def __enter__(self) -> _Cursor:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def execute(self, sql: str, parameters: tuple[object, ...] | None = None) -> None:
        """Accept the adapter's parameterized statements without side effects."""

    def fetchmany(self, size: int) -> list[tuple[object, ...]]:
        """Return no People rows."""
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
    """The capability validated at construction must be the capability used for the read."""
    accepted_calls = 0
    replacement_calls = 0

    def accepted_factory() -> _Connection:
        nonlocal accepted_calls
        accepted_calls += 1
        return _Connection()

    def replacement_factory() -> _Connection:
        nonlocal replacement_calls
        replacement_calls += 1
        raise AssertionError("replacement capability reached People persistence")

    port = PostgresPeopleReadPort(accepted_factory)

    with pytest.raises(AttributeError):
        object.__setattr__(port, "connection_factory", replacement_factory)

    assert port.connection_factory is accepted_factory
    assert (
        port.read_worker(
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            effective_on=EFFECTIVE_ON,
        )
        is None
    )
    assert accepted_calls == 1
    assert replacement_calls == 0
