"""Transaction-boundary regressions for governed PostgreSQL People reads."""

from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest

from orgmetra_people_api.postgres import PostgresPeopleReadPort

TENANT = UUID("0198a412-6000-7000-8000-000000000001")
PERSON = UUID("0198a412-6000-7000-8000-000000000010")
EFFECTIVE_ON = date(2026, 9, 14)


class _Cursor:
    """Fail if SQL is reached without a proven transaction contract."""

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
def test_people_read_rejects_unproven_transaction_before_cursor_access(
    autocommit: object,
) -> None:
    """Read-only mode and tenant context must never run outside one transaction."""
    connection = _Connection(autocommit=autocommit)
    port = PostgresPeopleReadPort(lambda: connection)

    with pytest.raises(RuntimeError, match="autocommit disabled"):
        port.read_worker(
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            effective_on=EFFECTIVE_ON,
        )

    assert connection.cursor_calls == 0
