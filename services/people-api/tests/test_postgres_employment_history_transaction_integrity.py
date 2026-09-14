"""Transaction-boundary regressions for PostgreSQL Employment-history reads."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_people_api.postgres_employment_history import PostgresEmploymentHistoryReadPort

TENANT_ID = UUID("0198a415-9ab1-7000-8000-000000000001")
PERSON_ID = UUID("0198a415-9ab1-7000-8000-000000000002")
KNOWN_AT = datetime(2026, 9, 14, tzinfo=timezone.utc)


class _Cursor:
    """Fail if SQL is reached for a connection without a transaction guarantee."""

    def __enter__(self) -> _Cursor:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def execute(self, sql: str, parameters: object | None = None) -> None:
        raise AssertionError(f"SQL executed without a guaranteed transaction: {sql!r} {parameters!r}")


class _Connection:
    """Expose a configurable autocommit contract and record cursor access."""

    def __init__(self, *, autocommit: object) -> None:
        self.autocommit = autocommit
        self.cursor_calls = 0

    def __enter__(self) -> _Connection:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def cursor(self) -> _Cursor:
        self.cursor_calls += 1
        return _Cursor()


@pytest.mark.parametrize("autocommit", [True, None, 0, "false"])
def test_connection_without_exact_non_autocommit_contract_fails_before_cursor_access(
    autocommit: object,
) -> None:
    """Transaction-local read-only and tenant state must never run on an unproven transaction."""
    connection = _Connection(autocommit=autocommit)
    port = PostgresEmploymentHistoryReadPort(lambda: connection)

    with pytest.raises(RuntimeError, match="autocommit disabled"):
        port.read_employment_history(
            tenant_record_id=TENANT_ID,
            person_record_id=PERSON_ID,
            known_at=KNOWN_AT,
        )

    assert connection.cursor_calls == 0
