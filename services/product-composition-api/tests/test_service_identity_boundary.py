from __future__ import annotations

from orgmetra_product_composition import CompositionRoute, OwnerApiRelease

A = "a" * 64
B = "b" * 64


def test_maximum_service_identifier_remains_routable_through_logical_upstream() -> None:
    service_id = "s" * 64
    owner = OwnerApiRelease(
        service_id=service_id,
        release_version="v1.2.3",
        openapi_sha256=A,
        artifact_sha256=B,
        release_locator="https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3",
    )

    selected_route = CompositionRoute(
        route_id="maximum_service_identity",
        path_template="/v1/people/{person_record_id}",
        methods=("GET",),
        owner_release=owner,
        logical_upstream="service://" + service_id,
        required=True,
    )

    assert selected_route.owner_release.service_id == service_id
    assert selected_route.logical_upstream == "service://" + service_id
