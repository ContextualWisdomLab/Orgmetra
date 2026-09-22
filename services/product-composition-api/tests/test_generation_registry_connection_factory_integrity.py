from __future__ import annotations

import pytest

from orgmetra_product_composition.postgres_registry import PostgresGenerationRegistry
from orgmetra_product_composition.registry import CompositionRegistryError


def test_generation_load_rejects_factory_drift_before_replacement_executes() -> None:
    """A caller-pinned factory must remain the factory used by the durable load."""

    def admitted_factory() -> None:
        raise AssertionError("admitted factory is not reached after detected drift")

    replacement_calls = 0

    def replacement_factory() -> None:
        nonlocal replacement_calls
        replacement_calls += 1
        raise AssertionError("unadmitted generation connection factory executed")

    registry = PostgresGenerationRegistry(admitted_factory)  # type: ignore[arg-type]
    expected_factory = registry.connection_factory
    object.__setattr__(registry, "connection_factory", replacement_factory)

    with pytest.raises(CompositionRegistryError, match="expected PostgreSQL connection factory"):
        registry.load("generation_one", _connection_factory=expected_factory)

    assert replacement_calls == 0
