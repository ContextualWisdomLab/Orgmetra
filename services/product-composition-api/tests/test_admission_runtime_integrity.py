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


def test_admission_revalidates_generation_after_low_level_route_mutation() -> None:
    owner = release()
    selected_route = route(owner)
    candidate = generation(selected_route)

    object.__setattr__(selected_route, "path_template", "/v1/jobs/{job_id}")

    with pytest.raises(CompositionContractError, match="config_sha256"):
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
