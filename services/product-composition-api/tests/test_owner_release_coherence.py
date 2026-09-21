from __future__ import annotations

import pytest

from orgmetra_product_composition import (
    CompositionContractError,
    CompositionGeneration,
    CompositionRoute,
    OwnerApiRelease,
    configuration_sha256,
)

A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64


def owner_release(version: str, openapi_sha256: str, artifact_sha256: str) -> OwnerApiRelease:
    return OwnerApiRelease(
        service_id="people_api",
        release_version=version,
        openapi_sha256=openapi_sha256,
        artifact_sha256=artifact_sha256,
        release_locator=(
            "https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/" + version
        ),
    )


def route(route_id: str, path: str, owner: OwnerApiRelease) -> CompositionRoute:
    return CompositionRoute(
        route_id=route_id,
        path_template=path,
        methods=("GET",),
        owner_release=owner,
        logical_upstream="service://people-api",
        required=True,
    )


def generation(*routes: CompositionRoute) -> CompositionGeneration:
    return CompositionGeneration(
        schema_version="orgmetra_gateway_composition.v1",
        generation_id="generation_001",
        config_sha256=configuration_sha256(routes),
        routes=routes,
    )


def test_generation_rejects_two_release_identities_for_one_owner_service() -> None:
    release_v1 = owner_release("v1.2.3", A, B)
    release_v2 = owner_release("v1.2.4", C, D)
    routes = (
        route("people_history", "/v1/people/{person_record_id}", release_v1),
        route("people_search", "/v1/people-search/{query_id}", release_v2),
    )

    with pytest.raises(CompositionContractError, match="one exact release"):
        generation(*routes)


def test_generation_allows_one_exact_release_reused_across_owner_routes() -> None:
    release_v1 = owner_release("v1.2.3", A, B)
    routes = (
        route("people_history", "/v1/people/{person_record_id}", release_v1),
        route("people_search", "/v1/people-search/{query_id}", release_v1),
    )

    candidate = generation(*routes)

    assert candidate.routes == routes
