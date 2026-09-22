"""PostgreSQL durability adapter for immutable product-composition generations.

The adapter persists only normalized composition-owned routing authority. It does not
own HR domain truth, Keyverse policy, tenant data, or deployment activation. A
``generation_id`` may be registered repeatedly only when every persisted semantic row
is exactly the same; semantic successors require a new identifier.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any, Callable

from .admission import CompositionGeneration
from .registry import (
    CompositionRegistryError,
    GenerationRecordSet,
    OwnerReleaseRecord,
    RouteMethodRecord,
    RouteRecord,
)

PostgresConnectionFactory = Callable[[], AbstractContextManager[Any]]

_INSERT_GENERATION_SQL = """
INSERT INTO public.product_composition_generation (
    generation_id,
    schema_version,
    config_sha256
)
VALUES (%s, %s, %s)
ON CONFLICT (generation_id) DO NOTHING
RETURNING generation_id
""".strip()

_INSERT_OWNER_RELEASE_SQL = """
INSERT INTO public.product_composition_owner_release (
    generation_id,
    service_id,
    release_version,
    openapi_sha256,
    artifact_sha256,
    release_locator
)
VALUES (%s, %s, %s, %s, %s, %s)
""".strip()

_INSERT_ROUTE_SQL = """
INSERT INTO public.product_composition_route (
    generation_id,
    route_id,
    path_template,
    owner_service_id,
    logical_upstream,
    required
)
VALUES (%s, %s, %s, %s, %s, %s)
""".strip()

_INSERT_ROUTE_METHOD_SQL = """
INSERT INTO public.product_composition_route_method (
    generation_id,
    route_id,
    method
)
VALUES (%s, %s, %s)
""".strip()

_SELECT_GENERATION_SQL = """
SELECT schema_version, config_sha256
FROM public.product_composition_generation
WHERE generation_id = %s
""".strip()

_SELECT_OWNER_RELEASES_SQL = """
SELECT
    service_id,
    release_version,
    openapi_sha256,
    artifact_sha256,
    release_locator
FROM public.product_composition_owner_release
WHERE generation_id = %s
ORDER BY service_id
""".strip()

_SELECT_ROUTES_SQL = """
SELECT
    route_id,
    path_template,
    owner_service_id,
    logical_upstream,
    required
FROM public.product_composition_route
WHERE generation_id = %s
ORDER BY route_id
""".strip()

_SELECT_ROUTE_METHODS_SQL = """
SELECT route_id, method
FROM public.product_composition_route_method
WHERE generation_id = %s
ORDER BY route_id, method
""".strip()

_READ_ONLY_SQL = "SET TRANSACTION READ ONLY"


def _bounded_lookup_generation_id(value: object) -> str:
    """Bound a parameterized lookup key without duplicating domain grammar authority."""
    if type(value) is not str:
        raise CompositionRegistryError("generation_id lookup must be an exact built-in str")
    if not value or len(value) > 64:
        raise CompositionRegistryError("generation_id lookup must contain 1..64 characters")
    return value


@dataclass(frozen=True, slots=True)
class PostgresGenerationRegistry:
    """Atomically persist and reload immutable normalized generation material."""

    connection_factory: PostgresConnectionFactory

    def __post_init__(self) -> None:
        """Reject an unusable database boundary before durability is attempted."""
        if not callable(self.connection_factory):
            raise TypeError("connection_factory must be callable")

    def register(self, records: GenerationRecordSet) -> CompositionGeneration:
        """Persist one generation exactly once, or accept an exact idempotent replay.

        ``INSERT .. ON CONFLICT DO NOTHING`` serializes concurrent attempts on the
        generation primary key. The winner writes all child rows in the same connection
        context/transaction; a loser reloads the committed normalized material and only
        succeeds when it is byte-for-value equivalent to the requested record set.
        """
        if type(records) is not GenerationRecordSet:
            raise CompositionRegistryError("records must be exact GenerationRecordSet evidence")
        restored = records.restore_generation()

        with self.connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    _INSERT_GENERATION_SQL,
                    (records.generation_id, records.schema_version, records.config_sha256),
                )
                inserted = cursor.fetchone()
                if inserted is None:
                    existing = self._load_record_set(cursor, records.generation_id)
                    if existing != records:
                        raise CompositionRegistryError(
                            "generation_id is already bound to different durable material"
                        )
                    existing.restore_generation()
                    return restored

                cursor.executemany(
                    _INSERT_OWNER_RELEASE_SQL,
                    (
                        (
                            records.generation_id,
                            row.service_id,
                            row.release_version,
                            row.openapi_sha256,
                            row.artifact_sha256,
                            row.release_locator,
                        )
                        for row in records.owner_releases
                    ),
                )
                cursor.executemany(
                    _INSERT_ROUTE_SQL,
                    (
                        (
                            records.generation_id,
                            row.route_id,
                            row.path_template,
                            row.owner_service_id,
                            row.logical_upstream,
                            row.required,
                        )
                        for row in records.routes
                    ),
                )
                cursor.executemany(
                    _INSERT_ROUTE_METHOD_SQL,
                    (
                        (records.generation_id, row.route_id, row.method)
                        for row in records.route_methods
                    ),
                )

        return restored

    def load(self, generation_id: str) -> CompositionGeneration | None:
        """Reload durable rows and reconstruct canonical admitted generation semantics."""
        lookup_generation_id = _bounded_lookup_generation_id(generation_id)
        with self.connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(_READ_ONLY_SQL)
                records = self._load_record_set(cursor, lookup_generation_id)
        if records is None:
            return None
        return records.restore_generation()

    @staticmethod
    def _load_record_set(cursor: Any, generation_id: str) -> GenerationRecordSet | None:
        cursor.execute(_SELECT_GENERATION_SQL, (generation_id,))
        generation_row = cursor.fetchone()
        if generation_row is None:
            return None
        schema_version, config_sha256 = generation_row

        cursor.execute(_SELECT_OWNER_RELEASES_SQL, (generation_id,))
        owner_releases = tuple(
            OwnerReleaseRecord(
                service_id=service_id,
                release_version=release_version,
                openapi_sha256=openapi_sha256,
                artifact_sha256=artifact_sha256,
                release_locator=release_locator,
            )
            for (
                service_id,
                release_version,
                openapi_sha256,
                artifact_sha256,
                release_locator,
            ) in cursor.fetchall()
        )

        cursor.execute(_SELECT_ROUTES_SQL, (generation_id,))
        routes = tuple(
            RouteRecord(
                route_id=route_id,
                path_template=path_template,
                owner_service_id=owner_service_id,
                logical_upstream=logical_upstream,
                required=required,
            )
            for (
                route_id,
                path_template,
                owner_service_id,
                logical_upstream,
                required,
            ) in cursor.fetchall()
        )

        cursor.execute(_SELECT_ROUTE_METHODS_SQL, (generation_id,))
        route_methods = tuple(
            RouteMethodRecord(route_id=route_id, method=method)
            for route_id, method in cursor.fetchall()
        )

        return GenerationRecordSet(
            schema_version=schema_version,
            generation_id=generation_id,
            config_sha256=config_sha256,
            owner_releases=owner_releases,
            routes=routes,
            route_methods=route_methods,
        )
