from __future__ import annotations

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


def generation(selected_route: CompositionRoute) -> CompositionGeneration:
    routes = (selected_route,)
    return CompositionGeneration(
        schema_version="orgmetra_gateway_composition.v1",
        generation_id="generation_001",
        config_sha256=configuration_sha256(routes),
        routes=routes,
    )


def test_route_binds_logical_upstream_to_owner_service_identity() -> None:
    owner = release()
    with pytest.raises(CompositionContractError, match="owner service"):
        CompositionRoute(
            route_id="people_history",
            path_template="/v1/tenants/{tenant_record_id}/people/{person_record_id}",
            methods=("GET",),
            owner_release=owner,
            logical_upstream="service://job-analysis-api",
            required=True,
        )


def test_admission_revalidates_generation_after_low_level_route_mutation() -> None:
    owner = release()
    selected_route = route(owner)
    candidate = generation(selected_route)

    object.__setattr__(selected_route, "path_template", "/v1/jobs/{job_id}")

    with pytest.raises(CompositionContractError, match="construction snapshot"):
        admit_generation(candidate, {"people_api": owner})


def test_admission_rejects_post_construction_generation_identity_rewrite() -> None:
    owner = release()
    candidate = generation(route(owner))

    object.__setattr__(candidate, "generation_id", "generation_002")

    with pytest.raises(CompositionContractError, match="construction snapshot"):
        admit_generation(candidate, {"people_api": owner})


def test_admission_rejects_self_consistent_post_construction_generation_retarget() -> None:
    owner = release()
    candidate = generation(route(owner))
    successor_route = CompositionRoute(
        route_id="people_history_v2",
        path_template=(
            "/v1/tenants/{tenant_record_id}/people/"
            "{person_record_id}/employment-history"
        ),
        methods=("GET",),
        owner_release=owner,
        logical_upstream="service://people-api",
        required=True,
    )
    successor_routes = (successor_route,)
    successor_digest = configuration_sha256(successor_routes)

    object.__setattr__(candidate, "routes", successor_routes)
    object.__setattr__(candidate, "config_sha256", successor_digest)

    with pytest.raises(CompositionContractError, match="construction snapshot"):
        admit_generation(candidate, {"people_api": owner})


def test_admission_receipt_route_ids_remain_canonical_after_nonsemantic_route_reorder() -> None:
    owner = release()
    alpha = CompositionRoute(
        route_id="alpha_route",
        path_template="/v1/alpha/{record_id}",
        methods=("GET",),
        owner_release=owner,
        logical_upstream="service://people-api",
        required=True,
    )
    zeta = CompositionRoute(
        route_id="zeta_route",
        path_template="/v1/zeta/{record_id}",
        methods=("GET",),
        owner_release=owner,
        logical_upstream="service://people-api",
        required=True,
    )
    routes = (alpha, zeta)
    candidate = CompositionGeneration(
        schema_version="orgmetra_gateway_composition.v1",
        generation_id="generation_001",
        config_sha256=configuration_sha256(routes),
        routes=routes,
    )

    object.__setattr__(candidate, "routes", (zeta, alpha))

    receipt = admit_generation(candidate, {"people_api": owner})
    assert receipt.admitted_route_ids == ("alpha_route", "zeta_route")


def test_admission_rejects_low_level_generation_route_shape_mutation() -> None:
    owner = release()
    candidate = generation(route(owner))
    object.__setattr__(candidate, "routes", [candidate.routes[0]])
    with pytest.raises(CompositionContractError, match="non-empty exact tuple"):
        admit_generation(candidate, {"people_api": owner})

    candidate = generation(route(owner))
    object.__setattr__(candidate, "routes", (object(),))
    with pytest.raises(CompositionContractError, match="exact CompositionRoute"):
        admit_generation(candidate, {"people_api": owner})


def test_admission_rejects_low_level_route_owner_shape_mutation() -> None:
    owner = release()
    selected_route = route(owner)
    candidate = generation(selected_route)
    object.__setattr__(selected_route, "owner_release", object())

    with pytest.raises(CompositionContractError, match="exact OwnerApiRelease"):
        admit_generation(candidate, {"people_api": owner})


def test_admission_revalidates_shared_owner_release_alias_before_use() -> None:
    owner = release()
    candidate = generation(route(owner))

    object.__setattr__(owner, "release_version", "latest")
    object.__setattr__(
        owner,
        "release_locator",
        "https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/latest",
    )

    with pytest.raises(CompositionContractError, match="immutable release"):
        admit_generation(candidate, {"people_api": owner})
