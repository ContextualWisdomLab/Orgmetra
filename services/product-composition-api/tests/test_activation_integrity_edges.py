from __future__ import annotations

from contextlib import contextmanager

import pytest

from orgmetra_product_composition import (
    ActivationEvent,
    ActivationRegistryError,
    CompositionGeneration,
    CompositionRoute,
    DeploymentIdentity,
    OwnerApiRelease,
    RecoveredActivation,
    configuration_sha256,
)
from orgmetra_product_composition.activation import PostgresActivationRegistry


class ScriptedCursor:
    def __init__(self, fetches: list[object]) -> None:
        self.fetches = list(fetches)

    def __enter__(self) -> "ScriptedCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, statement: str, params: object | None = None) -> None:
        return None

    def fetchone(self):
        if not self.fetches:
            raise AssertionError("unexpected fetchone")
        return self.fetches.pop(0)

    def fetchall(self):
        if not self.fetches:
            raise AssertionError("unexpected fetchall")
        return self.fetches.pop(0)


class ScriptedConnection:
    def __init__(self, cursor: ScriptedCursor) -> None:
        self.cursor_value = cursor

    def __enter__(self) -> "ScriptedConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def cursor(self) -> ScriptedCursor:
        return self.cursor_value


def _factory(fetches: list[object]):
    @contextmanager
    def factory():
        with ScriptedConnection(ScriptedCursor(fetches)) as connection:
            yield connection

    return factory


def _deployment() -> DeploymentIdentity:
    return DeploymentIdentity("orgmetra_gateway", "production")


def _generation(generation_id: str = "generation_one") -> CompositionGeneration:
    owner = OwnerApiRelease(
        service_id="people_api",
        release_version="v1.2.3",
        openapi_sha256="1" * 64,
        artifact_sha256="2" * 64,
        release_locator="https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3",
    )
    route = CompositionRoute(
        route_id="people_get",
        path_template="/v1/people/{person_record_id}",
        methods=("GET",),
        owner_release=owner,
        logical_upstream="service://people-api",
        required=True,
    )
    routes = (route,)
    return CompositionGeneration(
        generation_id=generation_id,
        routes=routes,
        config_sha256=configuration_sha256(routes),
    )


def test_activation_event_rejects_invalid_shapes() -> None:
    deployment = _deployment()
    with pytest.raises(ActivationRegistryError, match="DeploymentIdentity"):
        ActivationEvent(object(), 1, "generation_one", None, "activate")  # type: ignore[arg-type]
    with pytest.raises(ActivationRegistryError, match="activation_sequence"):
        ActivationEvent(deployment, 0, "generation_one", None, "activate")
    with pytest.raises(ActivationRegistryError, match="generation_id"):
        ActivationEvent(deployment, 1, "Generation-One", None, "activate")
    with pytest.raises(ActivationRegistryError, match="previous_generation_id"):
        ActivationEvent(deployment, 2, "generation_two", "Generation-One", "activate")
    with pytest.raises(ActivationRegistryError, match="event_kind"):
        ActivationEvent(deployment, 1, "generation_one", None, "delete")  # type: ignore[arg-type]
    with pytest.raises(ActivationRegistryError, match="first activation"):
        ActivationEvent(deployment, 1, "generation_two", "generation_one", "activate")
    with pytest.raises(ActivationRegistryError, match="successor activation"):
        ActivationEvent(deployment, 2, "generation_two", None, "activate")


def test_recovered_activation_requires_exact_matching_values() -> None:
    deployment = _deployment()
    generation = _generation()
    event = ActivationEvent(deployment, 1, "generation_one", None, "activate")
    assert RecoveredActivation(event, generation).generation == generation

    with pytest.raises(ActivationRegistryError, match="ActivationEvent"):
        RecoveredActivation(object(), generation)  # type: ignore[arg-type]
    with pytest.raises(ActivationRegistryError, match="CompositionGeneration"):
        RecoveredActivation(event, object())  # type: ignore[arg-type]
    with pytest.raises(ActivationRegistryError, match="must agree"):
        RecoveredActivation(event, _generation("generation_two"))


def test_registry_rejects_non_identity_deployment_and_failed_lock() -> None:
    registry = PostgresActivationRegistry(_factory([]))
    with pytest.raises(ActivationRegistryError, match="DeploymentIdentity"):
        registry.activate(
            object(),  # type: ignore[arg-type]
            generation_id="generation_one",
            expected_previous_sequence=0,
        )

    registry = PostgresActivationRegistry(_factory([("other", "production")]))
    with pytest.raises(ActivationRegistryError, match="deployment lock"):
        registry.activate(_deployment(), generation_id="generation_one", expected_previous_sequence=0)


def test_rollback_rejects_first_transition() -> None:
    registry = PostgresActivationRegistry(
        _factory([("orgmetra_gateway", "production"), None])
    )
    with pytest.raises(ActivationRegistryError, match="previously active"):
        registry.rollback(
            _deployment(), generation_id="generation_one", expected_previous_sequence=0
        )


def test_activation_rejects_unexpected_insert_receipt() -> None:
    generation = _generation()
    owner = generation.routes[0].owner_release
    fetches: list[object] = [
        ("orgmetra_gateway", "production"),
        None,
        (generation.schema_version, generation.config_sha256),
        [
            (
                owner.service_id,
                owner.release_version,
                owner.openapi_sha256,
                owner.artifact_sha256,
                owner.release_locator,
            )
        ],
        [
            (
                generation.routes[0].route_id,
                generation.routes[0].path_template,
                owner.service_id,
                generation.routes[0].logical_upstream,
                generation.routes[0].required,
            )
        ],
        [(generation.routes[0].route_id, "GET")],
        None,
    ]
    registry = PostgresActivationRegistry(_factory(fetches))
    with pytest.raises(ActivationRegistryError, match="did not return expected"):
        registry.activate(
            _deployment(), generation_id="generation_one", expected_previous_sequence=0
        )


def test_activation_wraps_tampered_generation_reconstruction() -> None:
    generation = _generation()
    owner = generation.routes[0].owner_release
    fetches: list[object] = [
        ("orgmetra_gateway", "production"),
        None,
        (generation.schema_version, "f" * 64),
        [
            (
                owner.service_id,
                owner.release_version,
                owner.openapi_sha256,
                owner.artifact_sha256,
                owner.release_locator,
            )
        ],
        [
            (
                generation.routes[0].route_id,
                generation.routes[0].path_template,
                owner.service_id,
                generation.routes[0].logical_upstream,
                generation.routes[0].required,
            )
        ],
        [(generation.routes[0].route_id, "GET")],
    ]
    registry = PostgresActivationRegistry(_factory(fetches))
    with pytest.raises(ActivationRegistryError, match="canonical reconstruction"):
        registry.activate(
            _deployment(), generation_id="generation_one", expected_previous_sequence=0
        )
