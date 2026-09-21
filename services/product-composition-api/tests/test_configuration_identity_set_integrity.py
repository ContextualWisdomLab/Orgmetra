from __future__ import annotations

import pytest

from orgmetra_product_composition import (
    CompositionContractError,
    CompositionRoute,
    OwnerApiRelease,
    configuration_sha256,
)

A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64


def owner_release(
    service_id: str = "people_api",
    *,
    version: str = "v1.2.3",
    openapi_sha256: str = A,
    artifact_sha256: str = B,
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


def route(
    route_id: str,
    path: str,
    *,
    service_id: str = "people_api",
    owner: OwnerApiRelease | None = None,
) -> CompositionRoute:
    selected_owner = owner or owner_release(service_id)
    return CompositionRoute(
        route_id=route_id,
        path_template=path,
        methods=("GET",),
        owner_release=selected_owner,
        logical_upstream=f"service://{service_id.replace('_', '-')}",
        required=True,
    )


def test_configuration_identity_rejects_duplicate_route_id_before_hashing() -> None:
    routes = (
        route("people_lookup", "/v1/people/{person_record_id}"),
        route("people_lookup", "/v1/people-search/{query_id}"),
    )

    with pytest.raises(CompositionContractError, match="route_id values must be unique"):
        configuration_sha256(routes)


def test_configuration_identity_rejects_split_owner_release_before_hashing() -> None:
    release_v1 = owner_release()
    release_v2 = owner_release(
        version="v1.2.4",
        openapi_sha256=C,
        artifact_sha256=D,
    )
    routes = (
        route("people_lookup", "/v1/people/{person_record_id}", owner=release_v1),
        route("people_search", "/v1/people-search/{query_id}", owner=release_v2),
    )

    with pytest.raises(CompositionContractError, match="one exact release"):
        configuration_sha256(routes)


def test_configuration_identity_rejects_same_hierarchy_alias_before_hashing() -> None:
    routes = (
        route("person_by_id", "/v1/people/{person_record_id}"),
        route(
            "person_by_subject",
            "/v1/people/{subject_id}",
            service_id="job_analysis_api",
        ),
    )

    with pytest.raises(CompositionContractError, match="same hierarchy"):
        configuration_sha256(routes)
