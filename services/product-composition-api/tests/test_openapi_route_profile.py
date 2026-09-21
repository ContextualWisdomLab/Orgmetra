from __future__ import annotations

from pathlib import Path

import pytest

from orgmetra_product_composition import (
    CompositionContractError,
    CompositionRoute,
    OwnerApiRelease,
)

A = "a" * 64
B = "b" * 64
ROOT = Path(__file__).resolve().parents[3]
README = Path(__file__).resolve().parents[1] / "README.md"


def owner_release() -> OwnerApiRelease:
    return OwnerApiRelease(
        service_id="people_api",
        release_version="v1.2.3",
        openapi_sha256=A,
        artifact_sha256=B,
        release_locator="https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3",
    )


def route(*, path_template: str, method: str) -> CompositionRoute:
    return CompositionRoute(
        route_id="people_read",
        path_template=path_template,
        methods=(method,),
        owner_release=owner_release(),
        logical_upstream="service://people-api",
        required=True,
    )


@pytest.mark.parametrize(
    "path_template",
    (
        "/v1/people/{person_record_id}.json",
        "/v1/people/~current",
        "/v1/people/%70erson",
    ),
)
def test_product_route_profile_rejects_openapi_paths_outside_its_bounded_subset(
    path_template: str,
) -> None:
    with pytest.raises(CompositionContractError, match="canonical versioned API path"):
        route(path_template=path_template, method="GET")


@pytest.mark.parametrize(
    "path_template",
    (
        "/v1/people/{person__record_id}",
        "/v1/people/{person_record_id_}",
    ),
)
def test_product_route_profile_rejects_noncanonical_snake_case_template_names(
    path_template: str,
) -> None:
    with pytest.raises(CompositionContractError, match="lower snake_case"):
        route(path_template=path_template, method="GET")


@pytest.mark.parametrize("method", ("QUERY", "TRACE"))
def test_product_route_profile_rejects_openapi_methods_not_admitted_by_orgmetra(
    method: str,
) -> None:
    with pytest.raises(CompositionContractError, match="not an admitted HTTP method"):
        route(path_template="/v1/people/{person_record_id}", method=method)


def test_route_profile_documentation_states_the_bounded_contract_explicitly() -> None:
    protected_contract = (ROOT / "docs" / "API_CONTRACT.md").read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")

    assert "Orgmetra APIs use OpenAPI 3.2.0." in protected_contract
    assert "## Supported OpenAPI route profile" in readme
    assert "not a general OpenAPI parser" in readme
    assert "`DELETE`, `GET`, `HEAD`, `OPTIONS`, `PATCH`, `POST`, and `PUT`" in readme
    assert "`TRACE`, `QUERY`, and `additionalOperations`" in readme
