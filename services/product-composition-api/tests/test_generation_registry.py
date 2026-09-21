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


def _owner(service_id: str = "people_api") -> OwnerApiRelease:
    return OwnerApiRelease(
        service_id=service_id,
        release_version="v1.2.3",
        openapi_sha256="1" * 64,
        artifact_sha256="2" * 64,
        release_locator=(
            "https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3"
        ),
    )


def _generation() -> CompositionGeneration:
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
        CompositionRoute(
            route_id="people_list",
            path_template="/v1/people",
            methods=("GET",),
            owner_release=owner,
            logical_upstream="service://people-api",
            required=False,
        ),
    )
    return CompositionGeneration(
        generation_id="generation_one",
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


def test_projection_revalidates_canonical_receipt_before_persistence() -> None:
    generation, receipt = _admitted_generation()
    object.__setattr__(receipt, "admitted_route_ids", ("people_get",))

    with pytest.raises(CompositionContractError, match="canonical issuance state"):
        GenerationRecordSet.from_admitted(generation, receipt)


def test_restore_rejects_stored_configuration_digest_reassignment() -> None:
    generation, receipt = _admitted_generation()
    records = GenerationRecordSet.from_admitted(generation, receipt)
    corrupted = replace(records, config_sha256="0" * 64)

    with pytest.raises(CompositionRegistryError, match="configuration digest"):
        corrupted.restore_generation()


def test_restore_rejects_route_without_durable_owner_release() -> None:
    generation, receipt = _admitted_generation()
    records = GenerationRecordSet.from_admitted(generation, receipt)
    corrupted = replace(records, owner_releases=())

    with pytest.raises(CompositionRegistryError, match="owner release"):
        corrupted.restore_generation()


def test_restore_rejects_duplicate_route_method_rows() -> None:
    generation, receipt = _admitted_generation()
    records = GenerationRecordSet.from_admitted(generation, receipt)
    corrupted = replace(
        records,
        route_methods=records.route_methods + (records.route_methods[0],),
    )

    with pytest.raises(CompositionRegistryError, match="duplicate route method"):
        corrupted.restore_generation()


def test_restore_rejects_route_without_method_rows() -> None:
    generation, receipt = _admitted_generation()
    records = GenerationRecordSet.from_admitted(generation, receipt)
    corrupted = replace(
        records,
        route_methods=tuple(
            method for method in records.route_methods if method.route_id != "people_list"
        ),
    )

    with pytest.raises(CompositionRegistryError, match="route method"):
        corrupted.restore_generation()
