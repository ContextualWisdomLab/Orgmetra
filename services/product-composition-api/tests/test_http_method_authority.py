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


def release(service_id: str) -> OwnerApiRelease:
    return OwnerApiRelease(
        service_id=service_id,
        release_version="v1.2.3",
        openapi_sha256=A,
        artifact_sha256=B,
        release_locator="https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3",
    )


def route(*, route_id: str, service_id: str, methods: tuple[str, ...]) -> CompositionRoute:
    return CompositionRoute(
        route_id=route_id,
        path_template="/v1/people/{person_record_id}",
        methods=methods,
        owner_release=release(service_id),
        logical_upstream=f"service://{service_id.replace('_', '-')}",
        required=True,
    )


def generation(*routes: CompositionRoute) -> CompositionGeneration:
    return CompositionGeneration(
        schema_version="orgmetra_gateway_composition.v1",
        generation_id="generation_001",
        config_sha256=configuration_sha256(routes),
        routes=routes,
    )


def test_generation_rejects_get_head_authority_split_across_owners() -> None:
    get_route = route(
        route_id="people_get",
        service_id="people_api",
        methods=("GET",),
    )
    head_route = route(
        route_id="people_head",
        service_id="job_analysis_api",
        methods=("HEAD",),
    )

    with pytest.raises(CompositionContractError, match="method/path authority"):
        generation(get_route, head_route)


def test_one_route_may_own_get_and_head_together() -> None:
    combined = route(
        route_id="people_read",
        service_id="people_api",
        methods=("GET", "HEAD"),
    )

    candidate = generation(combined)

    assert candidate.routes == (combined,)
