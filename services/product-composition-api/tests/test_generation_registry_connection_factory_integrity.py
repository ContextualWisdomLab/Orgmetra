from __future__ import annotations

import gc
import weakref

import pytest

from orgmetra_product_composition import (
    CompositionGeneration,
    CompositionRoute,
    OwnerApiRelease,
    admit_generation,
    configuration_sha256,
)
from orgmetra_product_composition.postgres_registry import PostgresGenerationRegistry
from orgmetra_product_composition.registry import CompositionRegistryError, GenerationRecordSet


def _records() -> GenerationRecordSet:
    """Build one valid admitted record set without opening a database connection."""

    owner = OwnerApiRelease(
        service_id="people_api",
        release_version="v1.2.3",
        openapi_sha256="1" * 64,
        artifact_sha256="2" * 64,
        release_locator="https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3",
    )
    routes = (
        CompositionRoute(
            route_id="people_get",
            path_template="/v1/people/{person_record_id}",
            methods=("GET",),
            owner_release=owner,
            logical_upstream="service://people-api",
            required=True,
        ),
    )
    generation = CompositionGeneration(
        generation_id="generation_one",
        routes=routes,
        config_sha256=configuration_sha256(routes),
    )
    receipt = admit_generation(
        generation,
        observed_owner_releases={"people_api": owner},
    )
    return GenerationRecordSet.from_admitted(generation, receipt)


def _retargeted_registry() -> tuple[PostgresGenerationRegistry, object, list[int]]:
    """Return a registry whose live field no longer matches its admitted factory."""

    def admitted_factory() -> None:
        raise AssertionError("admitted factory is not reached after detected drift")

    replacement_calls = [0]

    def replacement_factory() -> None:
        replacement_calls[0] += 1
        raise AssertionError("unadmitted generation connection factory executed")

    registry = PostgresGenerationRegistry(admitted_factory)  # type: ignore[arg-type]
    expected_factory = registry.connection_factory
    object.__setattr__(registry, "connection_factory", replacement_factory)
    return registry, expected_factory, replacement_calls


def test_generation_load_rejects_explicit_factory_drift_before_replacement_executes() -> None:
    """A caller-pinned factory must remain the factory used by the durable load."""

    registry, expected_factory, replacement_calls = _retargeted_registry()

    with pytest.raises(CompositionRegistryError, match="expected PostgreSQL connection factory"):
        registry.load("generation_one", _connection_factory=expected_factory)

    assert replacement_calls == [0]


def test_generation_load_rejects_construction_factory_drift_before_default_use() -> None:
    """Public load must not redefine its admitted factory from a mutated live field."""

    registry, _, replacement_calls = _retargeted_registry()

    with pytest.raises(CompositionRegistryError, match="construction snapshot"):
        registry.load("generation_one")

    assert replacement_calls == [0]


def test_generation_register_rejects_construction_factory_drift_before_use() -> None:
    """Public register must reject factory retargeting before any replacement DB call."""

    registry, _, replacement_calls = _retargeted_registry()

    with pytest.raises(CompositionRegistryError, match="construction snapshot"):
        registry.register(_records())

    assert replacement_calls == [0]


def test_generation_factory_identity_guard_does_not_root_registry_cycle() -> None:
    """Construction evidence must not keep a registry/factory callback cycle alive."""

    class Factory:
        registry: PostgresGenerationRegistry | None = None

        def __call__(self) -> None:
            raise AssertionError("factory is not executed in this lifetime contract")

    factory = Factory()
    registry = PostgresGenerationRegistry(factory)  # type: ignore[arg-type]
    factory.registry = registry
    registry_reference = weakref.ref(registry)
    factory_reference = weakref.ref(factory)

    del registry
    del factory
    gc.collect()

    assert registry_reference() is None
    assert factory_reference() is None


def test_generation_factory_identity_requires_non_rooting_witness() -> None:
    """Fail closed when a callable cannot provide weak-reference identity evidence."""

    class NonWeakFactory:
        __slots__ = ()

        def __call__(self) -> None:
            raise AssertionError("non-weak factory must be rejected at construction")

    with pytest.raises(TypeError, match="weak-reference identity"):
        PostgresGenerationRegistry(NonWeakFactory())  # type: ignore[arg-type]
