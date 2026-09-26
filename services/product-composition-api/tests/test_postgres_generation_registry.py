from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import pytest

from orgmetra_product_composition import (
    CompositionGeneration,
    CompositionRoute,
    OwnerApiRelease,
    admit_generation,
    configuration_sha256,
)
from orgmetra_product_composition.postgres_registry import PostgresGenerationRegistry
from orgmetra_product_composition.registry import (
    CompositionRegistryError,
    GenerationRecordSet,
)


class ScriptedCursor:
    def __init__(self, fetches: list[object]) -> None:
        self.fetches = list(fetches)
        self.executed: list[tuple[str, object | None]] = []
        self.executed_many: list[tuple[str, tuple[tuple[object, ...], ...]]] = []

    def __enter__(self) -> "ScriptedCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, statement: str, params: object | None = None) -> None:
        self.executed.append((statement, params))

    def executemany(self, statement: str, rows) -> None:
        materialized = tuple(tuple(row) for row in rows)
        self.executed_many.append((statement, materialized))

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
        self.entered = 0
        self.exited = 0

    def __enter__(self) -> "ScriptedConnection":
        self.entered += 1
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.exited += 1
        return None

    def cursor(self) -> ScriptedCursor:
        return self._cursor


def _owner() -> OwnerApiRelease:
    return OwnerApiRelease(
        service_id="people_api",
        release_version="v1.2.3",
        openapi_sha256="1" * 64,
        artifact_sha256="2" * 64,
        release_locator="https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3",
    )


def _records(generation_id: str = "generation_one") -> GenerationRecordSet:
    owner = _owner()
    routes = (
        CompositionRoute(
            route_id="people_get",
            path_template="/v1/people/{person_record_id}",
            methods=("GET", "HEAD"),
            owner_release=owner,
            logical_upstream="service://people-api",
            required=True,
        ),
    )
    generation = CompositionGeneration(
        schema_version="orgmetra_gateway_composition.v1",
        generation_id=generation_id,
        routes=routes,
        config_sha256=configuration_sha256(routes),
    )
    receipt = admit_generation(
        generation,
        observed_owner_releases={"people_api": _owner()},
    )
    return GenerationRecordSet.from_admitted(generation, receipt)


def _factory(connection: ScriptedConnection):
    @contextmanager
    def factory():
        with connection as opened:
            yield opened

    return factory


def _stored_rows(records: GenerationRecordSet) -> list[object]:
    owner = records.owner_releases[0]
    route = records.routes[0]
    methods = records.route_methods
    return [
        (records.schema_version, records.config_sha256),
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
                route.route_id,
                route.path_template,
                route.owner_service_id,
                route.logical_upstream,
                route.required,
            )
        ],
        [(row.route_id, row.method) for row in methods],
    ]


def test_register_inserts_one_atomic_normalized_generation() -> None:
    records = _records()
    cursor = ScriptedCursor(fetches=[(records.generation_id,)])
    connection = ScriptedConnection(cursor)
    registry = PostgresGenerationRegistry(_factory(connection))

    restored = registry.register(records)

    assert restored == records.restore_generation()
    assert connection.entered == 1
    assert connection.exited == 1
    assert len(cursor.executed) == 1
    assert "ON CONFLICT (generation_id) DO NOTHING" in cursor.executed[0][0]
    assert len(cursor.executed_many) == 3
    assert [len(rows) for _, rows in cursor.executed_many] == [1, 1, 2]


def test_register_is_idempotent_only_for_exact_existing_material() -> None:
    records = _records()
    cursor = ScriptedCursor(fetches=[None, *_stored_rows(records)])
    registry = PostgresGenerationRegistry(_factory(ScriptedConnection(cursor)))

    restored = registry.register(records)

    assert restored == records.restore_generation()
    assert len(cursor.executed_many) == 0


def test_register_rejects_generation_id_reassignment() -> None:
    records = _records()
    cursor = ScriptedCursor(
        fetches=[None, (records.schema_version, "f" * 64), [], [], []]
    )
    registry = PostgresGenerationRegistry(_factory(ScriptedConnection(cursor)))

    with pytest.raises(CompositionRegistryError, match="generation_id is already bound"):
        registry.register(records)


def test_load_reconstructs_and_revalidates_durable_rows() -> None:
    records = _records()
    cursor = ScriptedCursor(fetches=_stored_rows(records))
    registry = PostgresGenerationRegistry(_factory(ScriptedConnection(cursor)))

    restored = registry.load(records.generation_id)

    assert restored == records.restore_generation()
    assert "SET TRANSACTION READ ONLY" in cursor.executed[0][0]


def test_load_returns_none_for_unknown_generation() -> None:
    cursor = ScriptedCursor(fetches=[None])
    registry = PostgresGenerationRegistry(_factory(ScriptedConnection(cursor)))

    assert registry.load("generation_missing") is None


def test_load_rejects_partial_or_tampered_durable_state() -> None:
    records = _records()
    owner_rows = _stored_rows(records)[1]
    route_rows = _stored_rows(records)[2]
    cursor = ScriptedCursor(
        fetches=[
            (records.schema_version, records.config_sha256),
            owner_rows,
            route_rows,
            [],
        ]
    )
    registry = PostgresGenerationRegistry(_factory(ScriptedConnection(cursor)))

    with pytest.raises(CompositionRegistryError, match="at least one route method"):
        registry.load(records.generation_id)


def test_registry_requires_exact_record_set_and_callable_factory() -> None:
    with pytest.raises(TypeError, match="connection_factory"):
        PostgresGenerationRegistry(None)  # type: ignore[arg-type]

    registry = PostgresGenerationRegistry(_factory(ScriptedConnection(ScriptedCursor([]))))
    with pytest.raises(CompositionRegistryError, match="exact GenerationRecordSet"):
        registry.register(object())  # type: ignore[arg-type]


def test_migration_defines_append_only_normalized_registry() -> None:
    migration = (
        Path(__file__).resolve().parents[3]
        / "database"
        / "migrations"
        / "0018_product_composition_generation_registry.sql"
    ).read_text(encoding="utf-8")

    for table in (
        "product_composition_generation",
        "product_composition_owner_release",
        "product_composition_route",
        "product_composition_route_method",
    ):
        assert f"CREATE TABLE public.{table}" in migration
        assert f"CREATE TRIGGER {table}_append_only_guard" in migration

    assert "FOREIGN KEY (generation_id, owner_service_id)" in migration
    assert "FOREIGN KEY (generation_id, route_id)" in migration
    assert "CHECK (config_sha256 ~ '^[0-9a-f]{64}$')" in migration
