from dataclasses import replace

import pytest

from orgmetra_product_composition import (
    CompositionContractError,
    CompositionGeneration,
    CompositionRoute,
    OwnerApiRelease,
    admit_generation,
    configuration_sha256,
)
from orgmetra_product_composition.registry import (
    CompositionRegistryError,
    GenerationRecordSet,
    OwnerReleaseRecord,
    RouteMethodRecord,
    RouteRecord,
)


def _owner(
    service_id: str = "people_api",
    *,
    version: str = "v1.2.3",
    openapi_sha256: str = "1" * 64,
    artifact_sha256: str = "2" * 64,
) -> OwnerApiRelease:
    return OwnerApiRelease(
        service_id=service_id,
        release_version=version,
        openapi_sha256=openapi_sha256,
        artifact_sha256=artifact_sha256,
        release_locator=(
            "https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/" + version
        ),
    )


def _routes(owner: OwnerApiRelease | None = None) -> tuple[CompositionRoute, ...]:
    selected_owner = owner or _owner()
    return (
        CompositionRoute(
            route_id="people_get",
            path_template="/v1/people/{person_record_id}",
            methods=("GET", "HEAD"),
            owner_release=selected_owner,
            logical_upstream="service://people-api",
            required=True,
        ),
        CompositionRoute(
            route_id="people_list",
            path_template="/v1/people",
            methods=("GET",),
            owner_release=selected_owner,
            logical_upstream="service://people-api",
            required=False,
        ),
    )


def _generation(generation_id: str = "generation_one") -> CompositionGeneration:
    routes = _routes()
    return CompositionGeneration(
        generation_id=generation_id,
        routes=routes,
        config_sha256=configuration_sha256(routes),
    )


def _admitted_generation():
    generation = _generation()
    receipt = admit_generation(
        generation,
        observed_owner_releases={"people_api": _owner()},
    )
    return generation, receipt


def _record_set() -> GenerationRecordSet:
    generation, receipt = _admitted_generation()
    return GenerationRecordSet.from_admitted(generation, receipt)


def _counterfeit_generation(
    source: CompositionGeneration,
    *,
    routes: tuple[CompositionRoute, ...] | None = None,
    config_sha256: str | None = None,
) -> CompositionGeneration:
    candidate = object.__new__(CompositionGeneration)
    object.__setattr__(candidate, "schema_version", source.schema_version)
    object.__setattr__(candidate, "generation_id", source.generation_id)
    object.__setattr__(candidate, "routes", routes if routes is not None else source.routes)
    object.__setattr__(
        candidate,
        "config_sha256",
        config_sha256 if config_sha256 is not None else source.config_sha256,
    )
    return candidate


def test_admitted_generation_projects_to_normalized_reconstructable_records() -> None:
    generation, receipt = _admitted_generation()

    records = GenerationRecordSet.from_admitted(generation, receipt)

    assert records.schema_version == "orgmetra_gateway_composition.v1"
    assert records.generation_id == "generation_one"
    assert records.config_sha256 == generation.config_sha256
    assert records.owner_releases == (
        OwnerReleaseRecord(
            service_id="people_api",
            release_version="v1.2.3",
            openapi_sha256="1" * 64,
            artifact_sha256="2" * 64,
            release_locator=(
                "https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3"
            ),
        ),
    )
    assert records.routes == (
        RouteRecord(
            route_id="people_get",
            path_template="/v1/people/{person_record_id}",
            owner_service_id="people_api",
            logical_upstream="service://people-api",
            required=True,
        ),
        RouteRecord(
            route_id="people_list",
            path_template="/v1/people",
            owner_service_id="people_api",
            logical_upstream="service://people-api",
            required=False,
        ),
    )
    assert records.route_methods == (
        RouteMethodRecord(route_id="people_get", method="GET"),
        RouteMethodRecord(route_id="people_get", method="HEAD"),
        RouteMethodRecord(route_id="people_list", method="GET"),
    )

    restored = records.restore_generation()
    assert restored.schema_version == generation.schema_version
    assert restored.generation_id == generation.generation_id
    assert restored.config_sha256 == generation.config_sha256
    assert restored.routes == generation.routes


def test_projection_requires_exact_generation_type() -> None:
    _, receipt = _admitted_generation()

    with pytest.raises(CompositionRegistryError, match="exact CompositionGeneration"):
        GenerationRecordSet.from_admitted(object(), receipt)  # type: ignore[arg-type]


def test_projection_requires_exact_receipt_type() -> None:
    generation = _generation()

    with pytest.raises(CompositionRegistryError, match="exact AdmissionReceipt"):
        GenerationRecordSet.from_admitted(generation, object())  # type: ignore[arg-type]


def test_projection_revalidates_canonical_receipt_before_persistence() -> None:
    generation, receipt = _admitted_generation()
    object.__setattr__(receipt, "admitted_route_ids", ("people_get",))

    with pytest.raises(CompositionContractError, match="canonical issuance state"):
        GenerationRecordSet.from_admitted(generation, receipt)


def test_projection_rejects_receipt_for_different_generation_id() -> None:
    _, receipt = _admitted_generation()
    other = _generation("generation_two")

    with pytest.raises(CompositionRegistryError, match="generation_id"):
        GenerationRecordSet.from_admitted(other, receipt)


def test_projection_rejects_receipt_configuration_mismatch() -> None:
    generation, receipt = _admitted_generation()
    counterfeit = _counterfeit_generation(generation, config_sha256="0" * 64)

    with pytest.raises(CompositionRegistryError, match="config_sha256"):
        GenerationRecordSet.from_admitted(counterfeit, receipt)


def test_projection_rejects_receipt_route_set_mismatch() -> None:
    generation, receipt = _admitted_generation()
    counterfeit = _counterfeit_generation(generation, routes=(generation.routes[0],))

    with pytest.raises(CompositionRegistryError, match="route set"):
        GenerationRecordSet.from_admitted(counterfeit, receipt)


def test_projection_rejects_split_owner_release_even_on_counterfeit_generation() -> None:
    generation, receipt = _admitted_generation()
    fresh_routes = list(_routes())
    object.__setattr__(
        fresh_routes[1],
        "owner_release",
        _owner(
            version="v1.2.4",
            openapi_sha256="3" * 64,
            artifact_sha256="4" * 64,
        ),
    )
    counterfeit = _counterfeit_generation(generation, routes=tuple(fresh_routes))

    with pytest.raises(CompositionRegistryError, match="one exact owner release"):
        GenerationRecordSet.from_admitted(counterfeit, receipt)


def test_restore_requires_exact_owner_release_tuple() -> None:
    records = _record_set()
    corrupted = replace(records, owner_releases=list(records.owner_releases))  # type: ignore[arg-type]

    with pytest.raises(CompositionRegistryError, match="owner release rows must be an exact tuple"):
        corrupted.restore_generation()


def test_restore_requires_exact_route_tuple() -> None:
    records = _record_set()
    corrupted = replace(records, routes=list(records.routes))  # type: ignore[arg-type]

    with pytest.raises(CompositionRegistryError, match="route rows must be an exact tuple"):
        corrupted.restore_generation()


def test_restore_requires_exact_route_method_tuple() -> None:
    records = _record_set()
    corrupted = replace(records, route_methods=list(records.route_methods))  # type: ignore[arg-type]

    with pytest.raises(CompositionRegistryError, match="route method rows must be an exact tuple"):
        corrupted.restore_generation()


def test_restore_rejects_non_owner_release_record_value() -> None:
    records = _record_set()
    corrupted = replace(records, owner_releases=(object(),))  # type: ignore[arg-type]

    with pytest.raises(CompositionRegistryError, match="exact OwnerReleaseRecord"):
        corrupted.restore_generation()


def test_restore_rejects_duplicate_owner_release_service_id() -> None:
    records = _record_set()
    corrupted = replace(
        records,
        owner_releases=records.owner_releases + records.owner_releases,
    )

    with pytest.raises(CompositionRegistryError, match="duplicate owner release"):
        corrupted.restore_generation()


def test_restore_rejects_non_route_record_value() -> None:
    records = _record_set()
    corrupted = replace(records, routes=(object(),))  # type: ignore[arg-type]

    with pytest.raises(CompositionRegistryError, match="exact RouteRecord"):
        corrupted.restore_generation()


def test_restore_rejects_duplicate_route_id() -> None:
    records = _record_set()
    corrupted = replace(records, routes=records.routes + (records.routes[0],))

    with pytest.raises(CompositionRegistryError, match="duplicate route_id"):
        corrupted.restore_generation()


def test_restore_rejects_stored_configuration_digest_reassignment() -> None:
    records = _record_set()
    corrupted = replace(records, config_sha256="0" * 64)

    with pytest.raises(CompositionRegistryError, match="configuration digest"):
        corrupted.restore_generation()


def test_restore_rejects_route_without_durable_owner_release() -> None:
    records = _record_set()
    corrupted = replace(records, owner_releases=())

    with pytest.raises(CompositionRegistryError, match="owner release"):
        corrupted.restore_generation()


def test_restore_rejects_non_route_method_record_value() -> None:
    records = _record_set()
    corrupted = replace(records, route_methods=(object(),))  # type: ignore[arg-type]

    with pytest.raises(CompositionRegistryError, match="exact RouteMethodRecord"):
        corrupted.restore_generation()


def test_restore_rejects_method_row_without_route() -> None:
    records = _record_set()
    corrupted = replace(
        records,
        route_methods=records.route_methods
        + (RouteMethodRecord(route_id="missing_route", method="GET"),),
    )

    with pytest.raises(CompositionRegistryError, match="reference one durable route"):
        corrupted.restore_generation()


def test_restore_rejects_duplicate_route_method_rows() -> None:
    records = _record_set()
    corrupted = replace(
        records,
        route_methods=records.route_methods + (records.route_methods[0],),
    )

    with pytest.raises(CompositionRegistryError, match="duplicate route method"):
        corrupted.restore_generation()


def test_restore_rejects_route_without_method_rows() -> None:
    records = _record_set()
    corrupted = replace(
        records,
        route_methods=tuple(
            method for method in records.route_methods if method.route_id != "people_list"
        ),
    )

    with pytest.raises(CompositionRegistryError, match="route method"):
        corrupted.restore_generation()


def test_restore_wraps_invalid_stored_owner_contract() -> None:
    records = _record_set()
    invalid_owner = replace(records.owner_releases[0], openapi_sha256="not-a-digest")
    corrupted = replace(records, owner_releases=(invalid_owner,))

    with pytest.raises(CompositionRegistryError, match="violates the composition contract"):
        corrupted.restore_generation()
