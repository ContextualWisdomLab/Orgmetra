from __future__ import annotations

from orgmetra_product_composition import (
    CompositionGeneration,
    CompositionRoute,
    OwnerApiRelease,
    admit_generation,
    configuration_sha256,
)
from orgmetra_product_composition.registry import GenerationRecordSet


def _owner(service_id: str, version: str, digest_seed: str) -> OwnerApiRelease:
    return OwnerApiRelease(
        service_id=service_id,
        release_version=version,
        openapi_sha256=digest_seed * 64,
        artifact_sha256=("f" if digest_seed != "f" else "e") * 64,
        release_locator=(
            "https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/" + version
        ),
    )


def test_required_admission_can_persist_declared_optional_route_when_owner_is_unavailable() -> None:
    people = _owner("people_api", "v1.2.3", "1")
    workforce = _owner("workforce_validation_api", "v2.0.0", "2")
    routes = (
        CompositionRoute(
            route_id="people_get",
            path_template="/v1/people/{person_record_id}",
            methods=("GET",),
            owner_release=people,
            logical_upstream="service://people-api",
            required=True,
        ),
        CompositionRoute(
            route_id="validation_read",
            path_template="/v1/validation/studies/{study_id}",
            methods=("GET",),
            owner_release=workforce,
            logical_upstream="service://workforce-validation-api",
            required=False,
        ),
    )
    generation = CompositionGeneration(
        generation_id="generation_optional_owner_unavailable",
        routes=routes,
        config_sha256=configuration_sha256(routes),
    )
    receipt = admit_generation(
        generation,
        observed_owner_releases={"people_api": people},
    )

    assert receipt.required_routes_admitted is True
    assert receipt.admitted_route_ids == ("people_get",)
    assert receipt.unavailable_optional_route_ids == ("validation_read",)

    records = GenerationRecordSet.from_admitted(generation, receipt)

    assert tuple(route.route_id for route in records.routes) == (
        "people_get",
        "validation_read",
    )
    assert records.restore_generation() == generation
