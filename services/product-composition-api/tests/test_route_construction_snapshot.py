from __future__ import annotations

from dataclasses import replace

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


def release(*, service_id: str = "people_api", version: str = "v1.2.3") -> OwnerApiRelease:
    return OwnerApiRelease(
        service_id=service_id,
        release_version=version,
        openapi_sha256=A,
        artifact_sha256=B,
        release_locator=(
            "https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/"
            f"{version}"
        ),
    )


def route(owner: OwnerApiRelease | None = None) -> CompositionRoute:
    selected_owner = owner or release()
    return CompositionRoute(
        route_id="people_history",
        path_template="/v1/tenants/{tenant_record_id}/people/{person_record_id}",
        methods=("GET",),
        owner_release=selected_owner,
        logical_upstream=f"service://{selected_owner.service_id.replace('_', '-')}",
        required=True,
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("route_id", "people_history_v2"),
        (
            "path_template",
            "/v1/tenants/{tenant_record_id}/people/{person_record_id}/history",
        ),
        ("methods", ("POST",)),
        ("required", False),
    ),
)
def test_configuration_identity_rejects_valid_to_valid_route_retarget(
    field: str,
    replacement: object,
) -> None:
    selected_route = route()
    object.__setattr__(selected_route, field, replacement)

    with pytest.raises(CompositionContractError, match="construction snapshot"):
        configuration_sha256((selected_route,))


def test_configuration_identity_rejects_paired_owner_upstream_route_retarget() -> None:
    selected_route = route()
    successor_owner = release(service_id="job_analysis_api", version="v1.2.4")
    object.__setattr__(selected_route, "owner_release", successor_owner)
    object.__setattr__(selected_route, "logical_upstream", "service://job-analysis-api")

    with pytest.raises(CompositionContractError, match="construction snapshot"):
        configuration_sha256((selected_route,))


def test_new_route_may_use_different_valid_semantics() -> None:
    original = route()
    successor_owner = replace(
        original.owner_release,
        release_version="v1.2.4",
        release_locator="https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.4",
        artifact_sha256=C,
    )
    successor = CompositionRoute(
        route_id="people_history_v2",
        path_template="/v1/tenants/{tenant_record_id}/people/{person_record_id}/history",
        methods=("POST",),
        owner_release=successor_owner,
        logical_upstream="service://people-api",
        required=False,
    )

    assert configuration_sha256((original,)) != configuration_sha256((successor,))
