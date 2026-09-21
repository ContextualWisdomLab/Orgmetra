from __future__ import annotations

import gc

import pytest

from orgmetra_product_composition import (
    CompositionContractError,
    CompositionGeneration,
    CompositionRoute,
    OwnerApiRelease,
    admit_generation,
    configuration_sha256,
)

A = "a" * 64
B = "b" * 64


def release() -> OwnerApiRelease:
    return OwnerApiRelease(
        service_id="people_api",
        release_version="v1.2.3",
        openapi_sha256=A,
        artifact_sha256=B,
        release_locator="https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3",
    )


def route(owner: OwnerApiRelease) -> CompositionRoute:
    return CompositionRoute(
        route_id="people_history",
        path_template="/v1/tenants/{tenant_record_id}/people/{person_record_id}",
        methods=("GET",),
        owner_release=owner,
        logical_upstream="service://people-api",
        required=True,
    )


def summary_route(owner: OwnerApiRelease) -> CompositionRoute:
    return CompositionRoute(
        route_id="people_summary",
        path_template="/v1/tenants/{tenant_record_id}/people",
        methods=("GET",),
        owner_release=owner,
        logical_upstream="service://people-api",
        required=True,
    )


def test_configuration_digest_rejects_low_level_mutated_owner_before_materialization() -> None:
    owner = release()
    selected_route = route(owner)
    object.__setattr__(owner, "release_version", "latest")
    object.__setattr__(
        owner,
        "release_locator",
        "https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/latest",
    )

    with pytest.raises(CompositionContractError, match="immutable release"):
        configuration_sha256((selected_route,))


def test_configuration_digest_rejects_low_level_mutated_route_before_materialization() -> None:
    selected_route = route(release())
    object.__setattr__(selected_route, "logical_upstream", "service://job-analysis-api")

    with pytest.raises(CompositionContractError, match="owner service"):
        configuration_sha256((selected_route,))


def test_generation_rejects_nested_drift_at_construction_boundary() -> None:
    owner = release()
    selected_route = route(owner)
    valid_digest = configuration_sha256((selected_route,))
    object.__setattr__(selected_route, "logical_upstream", "service://job-analysis-api")

    with pytest.raises(CompositionContractError, match="owner service"):
        CompositionGeneration(
            schema_version="orgmetra_gateway_composition.v1",
            generation_id="generation_001",
            config_sha256=valid_digest,
            routes=(selected_route,),
        )


def test_generation_id_allows_concurrent_views_of_the_same_semantic_generation() -> None:
    selected_route = route(release())
    routes = (selected_route,)
    digest = configuration_sha256(routes)

    first = CompositionGeneration(
        schema_version="orgmetra_gateway_composition.v1",
        generation_id="generation_lineage_probe",
        config_sha256=digest,
        routes=routes,
    )
    second = CompositionGeneration(
        schema_version="orgmetra_gateway_composition.v1",
        generation_id="generation_lineage_probe",
        config_sha256=digest,
        routes=routes,
    )

    assert first.config_sha256 == second.config_sha256 == digest


def test_generation_id_rejects_concurrent_semantic_reuse() -> None:
    owner = release()
    first_route = route(owner)
    second_route = summary_route(owner)
    first_routes = (first_route,)
    second_routes = (second_route,)
    first_digest = configuration_sha256(first_routes)
    second_digest = configuration_sha256(second_routes)
    assert first_digest != second_digest

    first = CompositionGeneration(
        schema_version="orgmetra_gateway_composition.v1",
        generation_id="generation_lineage_conflict",
        config_sha256=first_digest,
        routes=first_routes,
    )

    with pytest.raises(CompositionContractError, match="generation_id.*different configuration"):
        CompositionGeneration(
            schema_version="orgmetra_gateway_composition.v1",
            generation_id="generation_lineage_conflict",
            config_sha256=second_digest,
            routes=second_routes,
        )

    assert first.config_sha256 == first_digest


def test_live_admission_receipt_keeps_generation_lineage_bound() -> None:
    owner = release()
    first_routes = (route(owner),)
    second_routes = (summary_route(owner),)
    first_digest = configuration_sha256(first_routes)
    second_digest = configuration_sha256(second_routes)
    generation_id = "generation_receipt_lineage"

    candidate = CompositionGeneration(
        schema_version="orgmetra_gateway_composition.v1",
        generation_id=generation_id,
        config_sha256=first_digest,
        routes=first_routes,
    )
    receipt = admit_generation(candidate, {"people_api": owner})
    assert receipt.required_routes_admitted is True

    del candidate
    gc.collect()

    with pytest.raises(CompositionContractError, match="generation_id.*different configuration"):
        CompositionGeneration(
            schema_version="orgmetra_gateway_composition.v1",
            generation_id=generation_id,
            config_sha256=second_digest,
            routes=second_routes,
        )

    assert receipt.required_routes_admitted is True

    del receipt
    gc.collect()

    successor = CompositionGeneration(
        schema_version="orgmetra_gateway_composition.v1",
        generation_id=generation_id,
        config_sha256=second_digest,
        routes=second_routes,
    )
    assert successor.config_sha256 == second_digest


def test_live_admission_receipt_revalidates_its_source_generation() -> None:
    owner = release()
    selected_route = route(owner)
    candidate = CompositionGeneration(
        schema_version="orgmetra_gateway_composition.v1",
        generation_id="generation_receipt_source",
        config_sha256=configuration_sha256((selected_route,)),
        routes=(selected_route,),
    )
    receipt = admit_generation(candidate, {"people_api": owner})

    object.__setattr__(
        selected_route,
        "path_template",
        "/v1/tenants/{tenant_record_id}/people/{person_record_id}/retargeted",
    )

    with pytest.raises(CompositionContractError, match="config_sha256"):
        _ = receipt.required_routes_admitted


def test_generation_id_live_lineage_is_not_durable_after_last_view_is_released() -> None:
    owner = release()
    first_routes = (route(owner),)
    second_routes = (summary_route(owner),)
    first_digest = configuration_sha256(first_routes)
    second_digest = configuration_sha256(second_routes)
    generation_id = "generation_lineage_ephemeral"

    first = CompositionGeneration(
        schema_version="orgmetra_gateway_composition.v1",
        generation_id=generation_id,
        config_sha256=first_digest,
        routes=first_routes,
    )
    assert first.config_sha256 == first_digest

    del first
    gc.collect()

    successor = CompositionGeneration(
        schema_version="orgmetra_gateway_composition.v1",
        generation_id=generation_id,
        config_sha256=second_digest,
        routes=second_routes,
    )
    assert successor.config_sha256 == second_digest
