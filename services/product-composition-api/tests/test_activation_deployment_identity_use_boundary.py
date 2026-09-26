from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import pytest

from orgmetra_product_composition import (
    ActivationEvent,
    ActivationRegistryError,
    DeploymentIdentity,
)
from orgmetra_product_composition.activation import PostgresActivationRegistry


class _Cursor:
    def __init__(self) -> None:
        self.executions: list[tuple[str, object]] = []

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, statement: str, params: object = None) -> None:
        self.executions.append((statement, params))

    def fetchone(self) -> None:
        return None


class _Connection:
    def __init__(self, cursor: _Cursor) -> None:
        self._cursor = cursor

    def cursor(self) -> _Cursor:
        return self._cursor


def test_structural_recovery_uses_detached_deployment_coordinates_after_connection_callback() -> None:
    """Connection acquisition must not retarget which deployment the durable read addresses."""

    deployment = DeploymentIdentity("orgmetra_gateway", "production")
    cursor = _Cursor()

    @contextmanager
    def connection_factory() -> Iterator[_Connection]:
        object.__setattr__(deployment, "environment_id", "staging")
        yield _Connection(cursor)

    registry = PostgresActivationRegistry(connection_factory)

    assert registry.recover_active(deployment) is None
    assert cursor.executions[-1][1] == ("orgmetra_gateway", "production")


def test_activation_event_revalidates_nested_deployment_identity() -> None:
    """A retargeted deployment value must not be accepted as nested durable event authority."""

    deployment = DeploymentIdentity("orgmetra_gateway", "production")
    object.__setattr__(deployment, "environment_id", "staging")

    with pytest.raises(ActivationRegistryError, match="construction snapshot"):
        ActivationEvent(
            deployment=deployment,
            activation_sequence=1,
            generation_id="generation_one",
            previous_generation_id=None,
            event_kind="activate",
            evidence_bundle_sha256="a" * 64,
        )
