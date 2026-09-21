from __future__ import annotations

import pytest

from orgmetra_product_composition import (
    CompositionContractError,
    CompositionRoute,
    OwnerApiRelease,
)

A = "a" * 64
B = "b" * 64


def owner_release() -> OwnerApiRelease:
    return OwnerApiRelease(
        service_id="people_api",
        release_version="v1.2.3",
        openapi_sha256=A,
        artifact_sha256=B,
        release_locator="https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3",
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
