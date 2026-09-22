"""Durable-row projection for admitted product-composition generations.

The record set is persistence-neutral on purpose: it contains only composition-owned
coordinates that can be normalized into 3NF tables and reconstructed through the
canonical admission value objects. Database durability and activation sequencing are
separate owner steps under #435.
"""

from __future__ import annotations

from dataclasses import dataclass

from .admission import (
    AdmissionReceipt,
    CompositionContractError,
    CompositionGeneration,
    CompositionRoute,
    OwnerApiRelease,
    configuration_sha256,
)


class CompositionRegistryError(CompositionContractError):
    """Reject persisted composition material that cannot reconstruct exact authority."""


@dataclass(frozen=True, slots=True)
class OwnerReleaseRecord:
    """Normalized durable coordinates for one owner release in one generation."""

    service_id: str
    release_version: str
    openapi_sha256: str
    artifact_sha256: str
    release_locator: str


@dataclass(frozen=True, slots=True)
class RouteRecord:
    """Normalized durable route coordinates excluding the multivalued method set."""

    route_id: str
    path_template: str
    owner_service_id: str
    logical_upstream: str
    required: bool


@dataclass(frozen=True, slots=True)
class RouteMethodRecord:
    """One exact declared HTTP method belonging to one durable route."""

    route_id: str
    method: str


@dataclass(frozen=True, slots=True)
class GenerationRecordSet:
    """Reconstructable normalized rows for one admitted composition generation."""

    schema_version: str
    generation_id: str
    config_sha256: str
    owner_releases: tuple[OwnerReleaseRecord, ...]
    routes: tuple[RouteRecord, ...]
    route_methods: tuple[RouteMethodRecord, ...]

    @classmethod
    def from_admitted(
        cls,
        generation: CompositionGeneration,
        receipt: AdmissionReceipt,
    ) -> "GenerationRecordSet":
        """Project one canonically admitted in-process generation into durable row values."""
        if type(generation) is not CompositionGeneration:
            raise CompositionRegistryError(
                "generation must be exact CompositionGeneration evidence"
            )
        if type(receipt) is not AdmissionReceipt:
            raise CompositionRegistryError("receipt must be exact AdmissionReceipt evidence")

        # Access performs the closure-private canonical receipt/source revalidation.
        receipt.required_routes_admitted
        if receipt.generation_id != generation.generation_id:
            raise CompositionRegistryError("receipt generation_id must match generation")
        if receipt.config_sha256 != generation.config_sha256:
            raise CompositionRegistryError("receipt config_sha256 must match generation")

        route_ids = tuple(sorted(route.route_id for route in generation.routes))
        receipt_route_ids = tuple(
            sorted(receipt.admitted_route_ids + receipt.unavailable_optional_route_ids)
        )
        if receipt_route_ids != route_ids:
            raise CompositionRegistryError(
                "receipt admitted/unavailable route set must exactly partition generation"
            )
        unavailable_route_ids = set(receipt.unavailable_optional_route_ids)
        if any(
            route.required and route.route_id in unavailable_route_ids
            for route in generation.routes
        ):
            raise CompositionRegistryError(
                "required generation routes cannot be unavailable in an admission receipt"
            )

        owner_by_service: dict[str, OwnerApiRelease] = {}
        for route in generation.routes:
            existing = owner_by_service.get(route.owner_release.service_id)
            if existing is None:
                owner_by_service[route.owner_release.service_id] = route.owner_release
            elif existing != route.owner_release:
                raise CompositionRegistryError(
                    "one service must have one exact owner release in persisted generation"
                )

        owner_records = tuple(
            OwnerReleaseRecord(
                service_id=owner.service_id,
                release_version=owner.release_version,
                openapi_sha256=owner.openapi_sha256,
                artifact_sha256=owner.artifact_sha256,
                release_locator=owner.release_locator,
            )
            for owner in sorted(owner_by_service.values(), key=lambda item: item.service_id)
        )
        route_records = tuple(
            RouteRecord(
                route_id=route.route_id,
                path_template=route.path_template,
                owner_service_id=route.owner_release.service_id,
                logical_upstream=route.logical_upstream,
                required=route.required,
            )
            for route in sorted(generation.routes, key=lambda item: item.route_id)
        )
        method_records = tuple(
            RouteMethodRecord(route_id=route.route_id, method=method)
            for route in sorted(generation.routes, key=lambda item: item.route_id)
            for method in route.methods
        )
        records = cls(
            schema_version=generation.schema_version,
            generation_id=generation.generation_id,
            config_sha256=generation.config_sha256,
            owner_releases=owner_records,
            routes=route_records,
            route_methods=method_records,
        )
        records.restore_generation()
        return records

    def restore_generation(self) -> CompositionGeneration:
        """Reconstruct and revalidate canonical generation semantics from stored row values."""
        if type(self.owner_releases) is not tuple:
            raise CompositionRegistryError("owner release rows must be an exact tuple")
        if type(self.routes) is not tuple:
            raise CompositionRegistryError("route rows must be an exact tuple")
        if type(self.route_methods) is not tuple:
            raise CompositionRegistryError("route method rows must be an exact tuple")

        owners: dict[str, OwnerApiRelease] = {}
        try:
            for record in self.owner_releases:
                if type(record) is not OwnerReleaseRecord:
                    raise CompositionRegistryError(
                        "owner release rows must contain exact OwnerReleaseRecord values"
                    )
                if record.service_id in owners:
                    raise CompositionRegistryError("duplicate owner release service_id")
                owners[record.service_id] = OwnerApiRelease(
                    service_id=record.service_id,
                    release_version=record.release_version,
                    openapi_sha256=record.openapi_sha256,
                    artifact_sha256=record.artifact_sha256,
                    release_locator=record.release_locator,
                )

            route_rows: dict[str, RouteRecord] = {}
            for record in self.routes:
                if type(record) is not RouteRecord:
                    raise CompositionRegistryError(
                        "route rows must contain exact RouteRecord values"
                    )
                if record.route_id in route_rows:
                    raise CompositionRegistryError("duplicate route_id in durable route rows")
                if record.owner_service_id not in owners:
                    raise CompositionRegistryError(
                        "route row must reference one durable owner release"
                    )
                route_rows[record.route_id] = record

            methods_by_route: dict[str, list[str]] = {route_id: [] for route_id in route_rows}
            method_keys: set[tuple[str, str]] = set()
            for record in self.route_methods:
                if type(record) is not RouteMethodRecord:
                    raise CompositionRegistryError(
                        "route method rows must contain exact RouteMethodRecord values"
                    )
                if record.route_id not in route_rows:
                    raise CompositionRegistryError(
                        "route method row must reference one durable route"
                    )
                key = (record.route_id, record.method)
                if key in method_keys:
                    raise CompositionRegistryError("duplicate route method row")
                method_keys.add(key)
                methods_by_route[record.route_id].append(record.method)

            reconstructed_routes: list[CompositionRoute] = []
            for route_id in sorted(route_rows):
                route_record = route_rows[route_id]
                methods = tuple(sorted(methods_by_route[route_id]))
                if not methods:
                    raise CompositionRegistryError(
                        "every durable route must have at least one route method row"
                    )
                reconstructed_routes.append(
                    CompositionRoute(
                        route_id=route_record.route_id,
                        path_template=route_record.path_template,
                        methods=methods,
                        owner_release=owners[route_record.owner_service_id],
                        logical_upstream=route_record.logical_upstream,
                        required=route_record.required,
                    )
                )

            routes = tuple(reconstructed_routes)
            actual_config_sha256 = configuration_sha256(routes)
            if actual_config_sha256 != self.config_sha256:
                raise CompositionRegistryError(
                    "stored configuration digest does not match reconstructed route material"
                )
            return CompositionGeneration(
                schema_version=self.schema_version,
                generation_id=self.generation_id,
                routes=routes,
                config_sha256=self.config_sha256,
            )
        except CompositionRegistryError:
            raise
        except CompositionContractError as exc:
            raise CompositionRegistryError(
                "stored generation material violates the composition contract"
            ) from exc
