from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import pytest

from orgmetra_product_composition import (
    ActivationConflictError,
    ActivationRegistryError,
    CompositionRoute,
    DeploymentIdentity,
    OwnerApiRelease,
    configuration_sha256,
)
from orgmetra_product_composition.activation import PostgresActivationRegistry


class ScriptedCursor:
    def __init__(self, fetches: list[object]) -> None:
        self.fetches = list(fetches)
        self.executed: list[tuple[str, object | None]] = []

    def __enter__(self) -> "ScriptedCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, statement: str, params: object | None = None) -> None:
        self.executed.append((statement, params))

    def fetchone(self):
        if not self.fetches:
            raise AssertionError("unexpected fetchone")
        value = self.fetches.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    def fetchall(self):
        if not self.fetches:
            raise AssertionError("unexpected fetchall")
        value = self.fetches.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class ScriptedConnection:
    def __init__(self, cursor: ScriptedCursor) -> None:
        self._cursor = cursor

    def __enter__(self) -> "ScriptedConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def cursor(self) -> ScriptedCursor:
        return self._cursor


def _factory(connection: ScriptedConnection):
    @contextmanager
    def factory():
        with connection as opened:
            yield opened

    return factory


def _deployment() -> DeploymentIdentity:
    return DeploymentIdentity(deployment_id="orgmetra_gateway", environment_id="production")


def _generation_rows(generation_id: str) -> list[object]:
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
    config = configuration_sha256((route,))
    return [
        ("orgmetra_gateway_composition.v1", config),
        [
            (
                "people_api",
                "v1.2.3",
                "1" * 64,
                "2" * 64,
                "https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3",
            )
        ],
        [
            (
                "people_get",
                "/v1/people/{person_record_id}",
                "people_api",
                "service://people-api",
                True,
            )
        ],
        [("people_get", "GET")],
    ]


def test_deployment_identity_is_explicit_canonical_and_nonempty() -> None:
    assert _deployment().deployment_id == "orgmetra_gateway"
    with pytest.raises(ActivationRegistryError, match="deployment_id"):
        DeploymentIdentity(deployment_id="Orgmetra-Gateway", environment_id="production")
    with pytest.raises(ActivationRegistryError, match="environment_id"):
        DeploymentIdentity(deployment_id="orgmetra_gateway", environment_id="")


def test_activate_locks_deployment_revalidates_generation_and_appends_next_event() -> None:
    fetches: list[object] = [
        ("orgmetra_gateway", "production"),
        None,
        *_generation_rows("generation_one"),
        (1,),
    ]
    cursor = ScriptedCursor(fetches)
    registry = PostgresActivationRegistry(_factory(ScriptedConnection(cursor)))

    event = registry.activate(
        _deployment(),
        generation_id="generation_one",
        expected_previous_sequence=0,
    )

    assert event.activation_sequence == 1
    assert event.generation_id == "generation_one"
    assert event.previous_generation_id is None
    assert event.event_kind == "activate"
    assert event.evidence_bundle_sha256 is None
    statements = "\n".join(statement for statement, _ in cursor.executed)
    assert "FOR UPDATE" in statements
    assert "product_composition_activation_event" in statements


def test_activate_rejects_stale_expected_sequence_before_target_write() -> None:
    cursor = ScriptedCursor(
        [
            ("orgmetra_gateway", "production"),
            (3, "generation_current", "activate", "generation_previous", None),
        ]
    )
    registry = PostgresActivationRegistry(_factory(ScriptedConnection(cursor)))

    with pytest.raises(ActivationConflictError, match="expected previous activation sequence"):
        registry.activate(
            _deployment(),
            generation_id="generation_next",
            expected_previous_sequence=2,
        )

    assert not any(
        "INSERT INTO public.product_composition_activation_event" in sql
        for sql, _ in cursor.executed
    )


def test_activate_rejects_unknown_or_partial_target_generation() -> None:
    cursor = ScriptedCursor(
        [
            ("orgmetra_gateway", "production"),
            None,
            None,
        ]
    )
    registry = PostgresActivationRegistry(_factory(ScriptedConnection(cursor)))

    with pytest.raises(ActivationRegistryError, match="persisted generation"):
        registry.activate(
            _deployment(),
            generation_id="generation_missing",
            expected_previous_sequence=0,
        )


def test_activate_rejects_noop_same_generation_transition() -> None:
    cursor = ScriptedCursor(
        [
            ("orgmetra_gateway", "production"),
            (4, "generation_current", "activate", "generation_previous", None),
        ]
    )
    registry = PostgresActivationRegistry(_factory(ScriptedConnection(cursor)))

    with pytest.raises(ActivationConflictError, match="already active"):
        registry.activate(
            _deployment(),
            generation_id="generation_current",
            expected_previous_sequence=4,
        )


def test_rollback_requires_target_to_have_prior_activation_and_revalidates_it() -> None:
    fetches: list[object] = [
        ("orgmetra_gateway", "production"),
        (2, "generation_two", "activate", "generation_one", None),
        (1,),
        *_generation_rows("generation_one"),
        (3,),
    ]
    cursor = ScriptedCursor(fetches)
    registry = PostgresActivationRegistry(_factory(ScriptedConnection(cursor)))

    event = registry.rollback(
        _deployment(),
        generation_id="generation_one",
        expected_previous_sequence=2,
    )

    assert event.activation_sequence == 3
    assert event.event_kind == "rollback"
    assert event.previous_generation_id == "generation_two"
    assert event.generation_id == "generation_one"
    assert event.evidence_bundle_sha256 is None


def test_rollback_rejects_generation_never_active_on_deployment() -> None:
    cursor = ScriptedCursor(
        [
            ("orgmetra_gateway", "production"),
            (2, "generation_two", "activate", "generation_one", None),
            None,
        ]
    )
    registry = PostgresActivationRegistry(_factory(ScriptedConnection(cursor)))

    with pytest.raises(ActivationRegistryError, match="previously active"):
        registry.rollback(
            _deployment(),
            generation_id="generation_other",
            expected_previous_sequence=2,
        )


def test_recover_active_uses_one_repeatable_read_snapshot_and_reconstructs_generation() -> None:
    cursor = ScriptedCursor(
        [
            (7, "generation_one", "activate", "generation_zero", "a" * 64),
            *_generation_rows("generation_one"),
        ]
    )
    registry = PostgresActivationRegistry(_factory(ScriptedConnection(cursor)))

    recovered = registry.recover_active(_deployment())

    assert recovered is not None
    assert recovered.event.activation_sequence == 7
    assert recovered.event.generation_id == recovered.generation.generation_id
    assert recovered.event.evidence_bundle_sha256 == "a" * 64
    assert "REPEATABLE READ READ ONLY" in cursor.executed[0][0]


def test_recover_active_returns_none_when_deployment_has_no_event() -> None:
    cursor = ScriptedCursor([None])
    registry = PostgresActivationRegistry(_factory(ScriptedConnection(cursor)))

    assert registry.recover_active(_deployment()) is None


def test_activation_registry_rejects_invalid_factory_sequence_and_generation_key() -> None:
    with pytest.raises(TypeError, match="connection_factory"):
        PostgresActivationRegistry(None)  # type: ignore[arg-type]

    registry = PostgresActivationRegistry(_factory(ScriptedConnection(ScriptedCursor([]))))
    with pytest.raises(ActivationRegistryError, match="expected_previous_sequence"):
        registry.activate(
            _deployment(), generation_id="generation_one", expected_previous_sequence=-1
        )
    with pytest.raises(ActivationRegistryError, match="generation_id"):
        registry.activate(_deployment(), generation_id="", expected_previous_sequence=0)


def test_activation_migration_is_append_only_and_generation_bound() -> None:
    migration = (
        Path(__file__).resolve().parents[3]
        / "database"
        / "migrations"
        / "0019_product_composition_activation_registry.sql"
    ).read_text(encoding="utf-8")

    assert "CREATE TABLE public.product_composition_deployment" in migration
    assert "CREATE TABLE public.product_composition_activation_event" in migration
    assert "REFERENCES public.product_composition_generation(generation_id)" in migration
    assert "CREATE TRIGGER product_composition_deployment_append_only_guard" in migration
    assert "CREATE TRIGGER product_composition_activation_event_append_only_guard" in migration
    assert "activation_sequence > 0" in migration
    assert "event_kind IN ('activate', 'rollback')" in migration
