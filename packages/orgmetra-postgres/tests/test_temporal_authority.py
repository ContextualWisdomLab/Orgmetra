"""Regression tests for database-owned system-recorded time."""

from __future__ import annotations

import inspect

from orgmetra_postgres import PostgresPeopleRepository


def test_create_person_has_no_caller_owned_recorded_time_parameter() -> None:
    """Keep knowledge time outside the externally callable repository command."""

    parameters = inspect.signature(PostgresPeopleRepository.create_person).parameters
    assert "recorded_at" not in parameters


def test_create_person_sql_uses_database_clock_without_caller_fallback() -> None:
    """Require the mutation implementation to source recorded time from PostgreSQL."""

    source = inspect.getsource(PostgresPeopleRepository.create_person)
    assert "COALESCE" not in source
    assert "recorded_at" not in source
    assert "now()" in source
