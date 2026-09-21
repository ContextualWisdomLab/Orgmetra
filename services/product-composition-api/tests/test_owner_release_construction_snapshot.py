from __future__ import annotations

from dataclasses import replace

import pytest

from orgmetra_product_composition import (
    CompositionContractError,
    CompositionRoute,
    OwnerApiRelease,
)

A = "a" * 64
B = "b" * 64
C = "c" * 64


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
        logical_upstream=f"service://{owner.service_id.replace('_', '-')}",
        required=True,
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("service_id", "job_analysis_api"),
        ("openapi_sha256", C),
        ("artifact_sha256", C),
    ),
)
def test_route_rejects_valid_to_valid_owner_release_retarget(
    field: str,
    replacement: str,
) -> None:
    owner = release()
    object.__setattr__(owner, field, replacement)

    with pytest.raises(CompositionContractError, match="construction snapshot"):
        route(owner)


def test_new_owner_release_may_use_a_different_valid_artifact_digest() -> None:
    successor = replace(release(), artifact_sha256=C)

    assert route(successor).owner_release.artifact_sha256 == C
