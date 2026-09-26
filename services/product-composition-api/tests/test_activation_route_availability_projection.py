from __future__ import annotations

from typing import cast

import pytest

from orgmetra_product_composition import (
    ActivationAdmissionEvidence,
    ActivationAuthorizationError,
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


def _generation() -> CompositionGeneration:
    people = _owner("people_api", "v1.2.3", "1")
    workforce = _owner("workforce_validation_api", "v2.0.0", "3")
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
            route_id="workforce_validation",
            path_template="/v1/workforce/validation/{validation_id}",
            methods=("GET", "POST"),
            owner_release=workforce,
            logical_upstream="service://workforce-validation-api",
            required=False,
        ),
    )
    return CompositionGeneration(
        schema_version="orgmetra_gateway_composition.v1",
        generation_id="generation_optional",
        routes=routes,
        config_sha256=configuration_sha256(routes),
    )


def _authority(authority_id: str, digest: str) -> ReleasedAuthorityEvidence:
    repository = "keyverse" if authority_id == "keyverse" else "Orgmetra"
    return ReleasedAuthorityEvidence(
        authority_id=authority_id,
        release_version="v1.0.0",
        artifact_sha256=digest * 64,
        release_locator=(
            f"https://github.com/ContextualWisdomLab/{repository}/releases/tag/v1.0.0"
        ),
    )


def _observation(route: CompositionRoute, method: str, digest: str) -> OwnerOperationObservation:
    owner = route.owner_release
    return OwnerOperationObservation(
        route_id=route.route_id,
        path_template=route.path_template,
        method=method,
        service_id=owner.service_id,
        release_version=owner.release_version,
        openapi_sha256=owner.openapi_sha256,
        artifact_sha256=owner.artifact_sha256,
        observation_sha256=digest * 64,
        observed_at_unix_ms=1_000,
        valid_until_unix_ms=2_000,
    )


def _evidence(
    generation: CompositionGeneration,
    owner_operations: tuple[OwnerOperationObservation, ...],
) -> ActivationAdmissionEvidence:
    return ActivationAdmissionEvidence(
        deployment_id="orgmetra_gateway",
        environment_id="production",
        generation_id=generation.generation_id,
        config_sha256=generation.config_sha256,
        authorization_action="activate",
        authorized_state_sequence=0,
        keyverse_authority=_authority("keyverse", "5"),
        orgmetra_authority=_authority("orgmetra", "6"),
        orgmetra_policy_version_code="composition_activation_v1",
        authorization_decision_sha256="7" * 64,
        owner_operations=owner_operations,
        valid_until_unix_ms=2_000,
    )


def _available_route_ids(
    evidence: ActivationAdmissionEvidence,
    generation: CompositionGeneration,
    *,
    now_unix_ms: int = 1_500,
) -> tuple[str, ...]:
    return available_route_ids_for(
        evidence,
        deployment_id="orgmetra_gateway",
        environment_id="production",
        generation=generation,
        authorization_action="activate",
        authorized_state_sequence=0,
        now_unix_ms=now_unix_ms,
    )


def test_route_availability_excludes_unobserved_optional_route() -> None:
    generation = _generation()
    required_route = generation.routes[0]
    evidence = _evidence(generation, (_observation(required_route, "GET", "8"),))

    assert _available_route_ids(evidence, generation) == ("people_get",)


def test_route_availability_includes_optional_route_only_after_complete_observation() -> None:
    generation = _generation()
    required_route, optional_route = generation.routes
    evidence = _evidence(
        generation,
        (
            _observation(required_route, "GET", "8"),
            _observation(optional_route, "GET", "9"),
            _observation(optional_route, "POST", "4"),
        ),
    )

    assert _available_route_ids(evidence, generation) == (
        "people_get",
        "workforce_validation",
    )


def test_route_availability_reuses_current_evidence_freshness_and_coverage_gate() -> None:
    generation = _generation()
    required_route, optional_route = generation.routes
    partial = _evidence(
        generation,
        (
            _observation(required_route, "GET", "8"),
            _observation(optional_route, "GET", "9"),
        ),
    )

    with pytest.raises(ActivationAuthorizationError, match="optional route.*absent or complete"):
        _available_route_ids(partial, generation)

    required_only = _evidence(generation, (_observation(required_route, "GET", "8"),))
    with pytest.raises(ActivationAuthorizationError, match="evidence is expired"):
        _available_route_ids(required_only, generation, now_unix_ms=2_000)


def test_route_availability_rejects_non_evidence_values_before_projection() -> None:
    generation = _generation()

    with pytest.raises(ActivationAuthorizationError, match="exact ActivationAdmissionEvidence"):
        _available_route_ids(cast(ActivationAdmissionEvidence, object()), generation)
