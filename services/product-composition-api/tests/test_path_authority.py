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


def owner_release(service_id: str = "people_api") -> OwnerApiRelease:
    return OwnerApiRelease(
        service_id=service_id,
        release_version="v1.2.3",
        openapi_sha256=A,
        artifact_sha256=B,
        release_locator="https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3",
    )


def route(
    route_id: str,
    path_template: str,
    method: str,
    *,
    service_id: str = "people_api",
) -> CompositionRoute:
    return CompositionRoute(
        route_id=route_id,
        path_template=path_template,
        methods=(method,),
        owner_release=owner_release(service_id),
        logical_upstream=f"service://{service_id.replace('_', '-')}",
        required=True,
    )


@pytest.mark.parametrize(
    "path_template",
    (
        "/v1/./people",
        "/v1/people/./{person_record_id}",
    ),
)
def test_route_rejects_complete_dot_segments(path_template: str) -> None:
    with pytest.raises(CompositionContractError, match="canonical versioned API path"):
        CompositionRoute(
            route_id="people_read",
            path_template=path_template,
            methods=("GET",),
            owner_release=owner_release(),
            logical_upstream="service://people-api",
            required=True,
        )


@pytest.mark.parametrize(
    "path_template",
    (
        "/v1/tenants/{record_id}/people/{record_id}",
        "/v1/{scope}/people/{scope}",
    ),
)
def test_route_rejects_repeated_path_template_expression(path_template: str) -> None:
    with pytest.raises(CompositionContractError, match="template expression"):
        CompositionRoute(
            route_id="people_read",
            path_template=path_template,
            methods=("GET",),
            owner_release=owner_release(),
            logical_upstream="service://people-api",
            required=True,
        )


def test_route_set_rejects_same_hierarchy_with_different_template_names_across_methods() -> None:
    routes = (
        route("people_read", "/v1/people/{person_record_id}", "GET"),
        route("people_update", "/v1/people/{worker_record_id}", "PUT"),
    )

    with pytest.raises(CompositionContractError, match="same hierarchy"):
        configuration_sha256(routes)


def test_route_set_allows_same_template_identity_across_distinct_methods() -> None:
    routes = (
        route("people_read", "/v1/people/{person_record_id}", "GET"),
        route("people_update", "/v1/people/{person_record_id}", "PUT"),
    )

    assert len(configuration_sha256(routes)) == 64


def test_route_set_allows_same_owner_concrete_precedence_for_same_method() -> None:
    routes = (
        route("people_current", "/v1/people/current", "GET"),
        route("people_read", "/v1/people/{person_record_id}", "GET"),
    )

    assert len(configuration_sha256(routes)) == 64


def test_route_set_rejects_cross_owner_concrete_template_overlap() -> None:
    routes = (
        route("people_current", "/v1/people/current", "GET"),
        route(
            "job_people_lookup",
            "/v1/people/{person_record_id}",
            "GET",
            service_id="job_analysis_api",
        ),
    )

    with pytest.raises(CompositionContractError, match="path selection"):
        configuration_sha256(routes)


def test_route_set_rejects_cross_owner_concrete_template_overlap_with_disjoint_methods() -> None:
    routes = (
        route("people_current", "/v1/people/current", "GET"),
        route(
            "job_people_update",
            "/v1/people/{person_record_id}",
            "PUT",
            service_id="job_analysis_api",
        ),
    )

    with pytest.raises(CompositionContractError, match="path selection"):
        configuration_sha256(routes)


def test_route_set_rejects_same_owner_concrete_template_with_different_methods() -> None:
    routes = (
        route("people_current", "/v1/people/current", "GET"),
        route("people_update", "/v1/people/{person_record_id}", "PUT"),
    )

    with pytest.raises(CompositionContractError, match="path selection"):
        configuration_sha256(routes)


def test_route_set_rejects_same_owner_ambiguous_templated_overlap() -> None:
    routes = (
        route("people_current", "/v1/{collection}/current", "GET"),
        route("people_read", "/v1/people/{person_record_id}", "GET"),
    )

    with pytest.raises(CompositionContractError, match="path selection"):
        configuration_sha256(routes)


def test_route_set_rejects_ambiguous_templated_overlap_with_disjoint_methods() -> None:
    routes = (
        route("people_current", "/v1/{collection}/current", "GET"),
        route("people_update", "/v1/people/{person_record_id}", "PUT"),
    )

    with pytest.raises(CompositionContractError, match="path selection"):
        configuration_sha256(routes)
