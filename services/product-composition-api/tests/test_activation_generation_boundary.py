from __future__ import annotations

import pytest

from orgmetra_product_composition import (
    ActivationAdmissionEvidence,
    CompositionContractError,
    CompositionGeneration,
    CompositionRoute,
    DeploymentIdentity,
    OwnerApiRelease,
    OwnerOperationObservation,
    ReleasedAuthorityEvidence,
    configuration_sha256,
)
from orgmetra_product_composition.activation_authorization import (
    AuthorizedPostgresActivationRegistry as AuthorizationRegistry,
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


def _authority(authority_id: str, digest: str) -> ReleasedAuthorityEvidence:
    repository = "keyverse" if authority_id == "keyverse" else "Orgmetra"
    return ReleasedAuthorityEvidence(
        authority_id=authority_id,
        release_version="v1.0.0",
        artifact_sha256=digest,
        release_locator=(
            f"https://github.com/ContextualWisdomLab/{repository}/releases/tag/v1.0.0"
        ),
    )


def _evidence(generation: CompositionGeneration) -> ActivationAdmissionEvidence:
    route = generation.routes[0]
    owner = route.owner_release
    return ActivationAdmissionEvidence(
        deployment_id="orgmetra_gateway",
        environment_id="production",
        generation_id=generation.generation_id,
        config_sha256=generation.config_sha256,
        authorization_action="activate",
        authorized_state_sequence=0,
        keyverse_authority=_authority("keyverse", "3" * 64),
        orgmetra_authority=_authority("orgmetra", "4" * 64),
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


def test_external_evidence_provider_cannot_retarget_loaded_generation(monkeypatch) -> None:
    generation = _generation()
    deployment = DeploymentIdentity("orgmetra_gateway", "production")

    class GenerationRegistry:
        def load(self, generation_id: str):
            assert generation_id == "generation_one"
            return generation

    class StructuralRegistry:
        def activate_authorized(self, *args, **kwargs):
            raise AssertionError("structural activation must not receive a retargeted generation")

    def retargeting_provider(deployment_arg, generation_arg, authorization_action, state_sequence):
        assert deployment_arg == deployment
        assert generation_arg is generation
        assert authorization_action == "activate"
        assert state_sequence == 0
        object.__setattr__(generation_arg, "generation_id", "generation_two")
        return _evidence(generation_arg)

    registry = AuthorizationRegistry(
        connection_factory=lambda: None,
        evidence_provider=retargeting_provider,
        clock_unix_ms=lambda: 1_500,
    )
    monkeypatch.setattr(registry, "_generation_registry", GenerationRegistry())
    monkeypatch.setattr(registry, "_structural_registry", StructuralRegistry())

    with pytest.raises(CompositionContractError, match="construction snapshot"):
        registry.activate(
            deployment,
            generation_id="generation_one",
            expected_previous_sequence=0,
        )
