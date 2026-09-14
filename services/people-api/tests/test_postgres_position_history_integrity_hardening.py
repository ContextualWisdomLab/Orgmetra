"""Regression contracts for Position-history PostgreSQL trust boundaries."""

from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_people_api.postgres_position_history import PostgresPositionHistoryReadPort

TENANT = UUID("018d51d2-9ab1-7ac0-8eb1-0a5dc487b9c1")
OTHER_TENANT = UUID("018d51d2-9ab1-7ac0-8eb1-0a5dc487b9d1")
POSITION = UUID("018d51d2-9ab1-7ac0-8eb1-0a5dc487b9c2")
OTHER_POSITION = UUID("018d51d2-9ab1-7ac0-8eb1-0a5dc487b9d2")
KNOWN_AT = datetime(2026, 8, 30, 0, 0, tzinfo=timezone.utc)


class Cursor(AbstractContextManager["Cursor"]):
    def __init__(self) -> None:
        self.executions: list[tuple[str, object | None]] = []

    def __enter__(self) -> "Cursor":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def execute(self, statement: str, parameters: object | None = None) -> None:
        self.executions.append((statement, parameters))

    def fetchall(self) -> list[object]:
        return []


class Connection(AbstractContextManager["Connection"]):
    def __init__(self, *, autocommit: object = False) -> None:
        self.autocommit = autocommit
        self.cursor_calls = 0
        self.cursor_instance = Cursor()

    def __enter__(self) -> "Connection":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def cursor(self) -> Cursor:
        self.cursor_calls += 1
        return self.cursor_instance


class MutatingFactory:
    def __init__(self, tenant_alias: UUID, position_alias: UUID) -> None:
        self.tenant_alias = tenant_alias
        self.position_alias = position_alias
        self.connection = Connection()

    def __call__(self) -> Connection:
        object.__setattr__(self.tenant_alias, "int", OTHER_TENANT.int)
        object.__setattr__(self.position_alias, "int", OTHER_POSITION.int)
        return self.connection


def test_connection_factory_capability_cannot_be_replaced_after_validation() -> None:
    accepted = lambda: Connection()
    replacement = lambda: Connection()
    port = PostgresPositionHistoryReadPort(accepted)

    with pytest.raises(AttributeError):
        object.__setattr__(port, "connection_factory", replacement)

    assert port.connection_factory is accepted


def test_autocommit_connection_fails_before_cursor_access() -> None:
    connection = Connection(autocommit=True)
    port = PostgresPositionHistoryReadPort(lambda: connection)

    with pytest.raises(ValueError, match="autocommit"):
        port.read_position_history(
            tenant_record_id=TENANT,
            position_record_id=POSITION,
            known_at=KNOWN_AT,
        )

    assert connection.cursor_calls == 0


@pytest.mark.parametrize("unproven_mode", [None, 0, "false"])
def test_unproven_transaction_mode_fails_before_cursor_access(unproven_mode: object) -> None:
    connection = Connection(autocommit=unproven_mode)
    port = PostgresPositionHistoryReadPort(lambda: connection)

    with pytest.raises(ValueError, match="autocommit"):
        port.read_position_history(
            tenant_record_id=TENANT,
            position_record_id=POSITION,
            known_at=KNOWN_AT,
        )

    assert connection.cursor_calls == 0


def test_request_uuid_aliases_are_detached_before_connection_acquisition() -> None:
    tenant_alias = UUID(str(TENANT))
    position_alias = UUID(str(POSITION))
    factory = MutatingFactory(tenant_alias, position_alias)
    port = PostgresPositionHistoryReadPort(factory)

    assert port.read_position_history(
        tenant_record_id=tenant_alias,
        position_record_id=position_alias,
        known_at=KNOWN_AT,
    ) == ()

    executions = factory.connection.cursor_instance.executions
    assert executions[1][1] == (str(TENANT),)
    assert executions[2][1][:2] == (TENANT, POSITION)
