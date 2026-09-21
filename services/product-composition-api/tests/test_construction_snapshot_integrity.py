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
