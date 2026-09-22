from __future__ import annotations

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


def _generation() -> CompositionGeneration:
    owner = OwnerApiRelease(
        service_id="people_api",
        release_version="v1.2.3",
        openapi_sha256="1" * 64,
        artifact_sha256="2" * 64,
        release_locator="https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3",
    )
    route = CompositionRoute(
        route_id="people_get",
        path_template="/v1/people/{person_record_id}",
        methods=("GET",),
        owner_release=owner,
        logical_upstream="service://people-api",
        required=True,
    )
    routes = (route,)
    return CompositionGeneration(
        generation_id="generation_one",
        routes=routes,
        config_sha256=configuration_sha256(routes),
    )


def _authority(authority_id: str, release_version: str, digest: str) -> ReleasedAuthorityEvidence:
    repository = "keyverse" if authority_id == "keyverse" else "Orgmetra"
    return ReleasedAuthorityEvidence(
        authority_id=authority_id,
        release_version=release_version,
        artifact_sha256=digest,
        release_locator=(
            f"https://github.com/ContextualWisdomLab/{repository}/releases/tag/{release_version}"
        ),
    )


def _evidence() -> tuple[ActivationAdmissionEvidence, CompositionGeneration]:
    generation = _generation()
    route = generation.routes[0]
    owner = route.owner_release
    evidence = ActivationAdmissionEvidence(
        deployment_id="orgmetra_gateway",
        environment_id="production",
        generation_id=generation.generation_id,
        config_sha256=generation.config_sha256,
        authorization_action="activate",
        authorized_state_sequence=0,
        keyverse_authority=_authority("keyverse", "v1.0.0", "3" * 64),
        orgmetra_authority=_authority("orgmetra", "v1.0.0", "4" * 64),
        orgmetra_policy_version_code="composition_activation_v1",
        authorization_decision_sha256="5" * 64,
        owner_operations=(
            OwnerOperationObservation(
                route_id=route.route_id,
                path_template=route.path_template,
                method="GET",
                service_id=owner.service_id,
                release_version=owner.release_version,
                openapi_sha256=owner.openapi_sha256,
                artifact_sha256=owner.artifact_sha256,
                observation_sha256="6" * 64,
                observed_at_unix_ms=1_000,
                valid_until_unix_ms=2_000,
            ),
        ),
        valid_until_unix_ms=2_000,
    )
    return evidence, generation


def _validate(evidence: ActivationAdmissionEvidence, generation: CompositionGeneration) -> None:
    evidence.validate_for(
        deployment_id="orgmetra_gateway",
        environment_id="production",
        generation=generation,
        authorization_action="activate",
        authorized_state_sequence=0,
        now_unix_ms=1_500,
    )


def test_released_authority_cannot_be_valid_to_valid_retargeted_after_construction() -> None:
    evidence, generation = _evidence()
    authority = evidence.keyverse_authority
    object.__setattr__(authority, "release_version", "v1.0.1")
    object.__setattr__(authority, "artifact_sha256", "7" * 64)
    object.__setattr__(
        authority,
        "release_locator",
        "https://github.com/ContextualWisdomLab/keyverse/releases/tag/v1.0.1",
    )

    with pytest.raises(ActivationAuthorizationError, match="construction snapshot"):
        _validate(evidence, generation)


def test_owner_observation_cannot_be_valid_to_valid_retargeted_after_construction() -> None:
    evidence, generation = _evidence()
    object.__setattr__(evidence.owner_operations[0], "observation_sha256", "7" * 64)

    with pytest.raises(ActivationAuthorizationError, match="construction snapshot"):
        _validate(evidence, generation)


def test_activation_evidence_cannot_be_valid_to_valid_retargeted_after_construction() -> None:
    evidence, generation = _evidence()
    object.__setattr__(evidence, "authorization_decision_sha256", "8" * 64)

    with pytest.raises(ActivationAuthorizationError, match="construction snapshot"):
        _validate(evidence, generation)
