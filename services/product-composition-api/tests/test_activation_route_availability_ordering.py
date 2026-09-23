from __future__ import annotations

from orgmetra_product_composition import (
    ActivationAdmissionEvidence,
    CompositionGeneration,
    CompositionRoute,
    OwnerApiRelease,
    OwnerOperationObservation,
    ReleasedAuthorityEvidence,
    configuration_sha256,
)
from orgmetra_product_composition.route_availability import available_route_ids_for


def _owner(service_id: str, release_version: str, digest_digit: str) -> OwnerApiRelease:
    return OwnerApiRelease(
        service_id=service_id,
        release_version=release_version,
        openapi_sha256=digest_digit * 64,
        artifact_sha256=str((int(digest_digit) + 1) % 10) * 64,
        release_locator=(
            "https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/"
            f"{release_version}"
        ),
    )


def _observation(route: CompositionRoute, digest_digit: str) -> OwnerOperationObservation:
    return OwnerOperationObservation(
        route_id=route.route_id,
        path_template=route.path_template,
        method="GET",
        service_id=route.owner_release.service_id,
        release_version=route.owner_release.release_version,
        openapi_sha256=route.owner_release.openapi_sha256,
        artifact_sha256=route.owner_release.artifact_sha256,
        observation_sha256=digest_digit * 64,
        observed_at_unix_ms=1_000,
        valid_until_unix_ms=2_000,
    )


def test_route_availability_uses_canonical_route_order_not_input_tuple_order() -> None:
    people = _owner("people_api", "v1.2.3", "1")
    workforce = _owner("workforce_validation_api", "v2.0.0", "3")
    routes = (
        CompositionRoute(
            route_id="workforce_validation",
            path_template="/v1/workforce/validation/{validation_id}",
            methods=("GET",),
            owner_release=workforce,
            logical_upstream="service://workforce-validation-api",
            required=False,
        ),
        CompositionRoute(
            route_id="people_get",
            path_template="/v1/people/{person_record_id}",
            methods=("GET",),
            owner_release=people,
            logical_upstream="service://people-api",
            required=True,
        ),
    )
    generation = CompositionGeneration(
        generation_id="generation_reversed_routes",
        routes=routes,
        config_sha256=configuration_sha256(routes),
    )
    evidence = ActivationAdmissionEvidence(
        deployment_id="orgmetra_gateway",
        environment_id="production",
        generation_id=generation.generation_id,
        config_sha256=generation.config_sha256,
        authorization_action="activate",
        authorized_state_sequence=0,
        keyverse_authority=ReleasedAuthorityEvidence(
            authority_id="keyverse",
            release_version="v1.0.0",
            artifact_sha256="5" * 64,
            release_locator="https://github.com/ContextualWisdomLab/keyverse/releases/tag/v1.0.0",
        ),
        orgmetra_authority=ReleasedAuthorityEvidence(
            authority_id="orgmetra",
            release_version="v1.0.0",
            artifact_sha256="6" * 64,
            release_locator="https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.0.0",
        ),
        orgmetra_policy_version_code="composition_activation_v1",
        authorization_decision_sha256="7" * 64,
        owner_operations=(
            _observation(routes[0], "8"),
            _observation(routes[1], "9"),
        ),
        valid_until_unix_ms=2_000,
    )

    assert available_route_ids_for(
        evidence,
        deployment_id="orgmetra_gateway",
        environment_id="production",
        generation=generation,
        authorization_action="activate",
        authorized_state_sequence=0,
        now_unix_ms=1_500,
    ) == ("people_get", "workforce_validation")
