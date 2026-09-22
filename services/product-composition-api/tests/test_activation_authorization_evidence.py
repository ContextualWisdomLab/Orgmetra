from __future__ import annotations

from contextlib import contextmanager

import pytest

from orgmetra_product_composition import (
    ActivationAdmissionEvidence,
    ActivationAuthorizationError,
    AuthorizedPostgresActivationRegistry,
    CompositionGeneration,
    CompositionRoute,
    DeploymentIdentity,
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


def _evidence(*, valid_until_unix_ms: int = 2_000) -> ActivationAdmissionEvidence:
    generation = _generation()
    route = generation.routes[0]
    owner = route.owner_release
    return ActivationAdmissionEvidence(
        deployment_id="orgmetra_gateway",
        environment_id="production",
        generation_id=generation.generation_id,
        config_sha256=generation.config_sha256,
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
                valid_until_unix_ms=valid_until_unix_ms,
            ),
        ),
        valid_until_unix_ms=valid_until_unix_ms,
    )


def test_activation_evidence_requires_exact_released_authorities_and_operation_coverage() -> None:
    evidence = _evidence()
    generation = _generation()
    evidence.validate_for(
        deployment_id="orgmetra_gateway",
        environment_id="production",
        generation=generation,
        now_unix_ms=1_500,
    )

    missing = ActivationAdmissionEvidence(
        deployment_id=evidence.deployment_id,
        environment_id=evidence.environment_id,
        generation_id=evidence.generation_id,
        config_sha256=evidence.config_sha256,
        keyverse_authority=evidence.keyverse_authority,
        orgmetra_authority=evidence.orgmetra_authority,
        orgmetra_policy_version_code=evidence.orgmetra_policy_version_code,
        authorization_decision_sha256=evidence.authorization_decision_sha256,
        owner_operations=(),
        valid_until_unix_ms=evidence.valid_until_unix_ms,
    )
    with pytest.raises(ActivationAuthorizationError, match="exact owner operation coverage"):
        missing.validate_for(
            deployment_id="orgmetra_gateway",
            environment_id="production",
            generation=generation,
            now_unix_ms=1_500,
        )


def test_activation_evidence_rejects_expired_or_future_observation() -> None:
    generation = _generation()
    with pytest.raises(ActivationAuthorizationError, match="expired"):
        _evidence(valid_until_unix_ms=1_400).validate_for(
            deployment_id="orgmetra_gateway",
            environment_id="production",
            generation=generation,
            now_unix_ms=1_500,
        )

    evidence = _evidence()
    future_observation = OwnerOperationObservation(
        **{
            **evidence.owner_operations[0].__dict__,
            "observed_at_unix_ms": 1_600,
        }
    )
    future = ActivationAdmissionEvidence(
        deployment_id=evidence.deployment_id,
        environment_id=evidence.environment_id,
        generation_id=evidence.generation_id,
        config_sha256=evidence.config_sha256,
        keyverse_authority=evidence.keyverse_authority,
        orgmetra_authority=evidence.orgmetra_authority,
        orgmetra_policy_version_code=evidence.orgmetra_policy_version_code,
        authorization_decision_sha256=evidence.authorization_decision_sha256,
        owner_operations=(future_observation,),
        valid_until_unix_ms=evidence.valid_until_unix_ms,
    )
    with pytest.raises(ActivationAuthorizationError, match="future"):
        future.validate_for(
            deployment_id="orgmetra_gateway",
            environment_id="production",
            generation=generation,
            now_unix_ms=1_500,
        )


def test_authorized_registry_obtains_external_evidence_before_structural_activation(monkeypatch) -> None:
    generation = _generation()
    deployment = DeploymentIdentity("orgmetra_gateway", "production")
    order: list[str] = []

    class GenerationRegistry:
        def load(self, generation_id: str):
            order.append("load_generation")
            assert generation_id == generation.generation_id
            return generation

    class StructuralRegistry:
        def activate(self, deployment_arg, *, generation_id: str, expected_previous_sequence: int):
            order.append("structural_activate")
            assert deployment_arg == deployment
            assert generation_id == generation.generation_id
            assert expected_previous_sequence == 0
            return object()

    def evidence_provider(deployment_arg, generation_arg):
        order.append("external_evidence")
        assert deployment_arg == deployment
        assert generation_arg == generation
        return _evidence()

    registry = AuthorizedPostgresActivationRegistry(
        connection_factory=lambda: None,
        evidence_provider=evidence_provider,
        clock_unix_ms=lambda: 1_500,
    )
    monkeypatch.setattr(registry, "_generation_registry", GenerationRegistry())
    monkeypatch.setattr(registry, "_structural_registry", StructuralRegistry())

    registry.activate(
        deployment,
        generation_id=generation.generation_id,
        expected_previous_sequence=0,
    )

    assert order == ["load_generation", "external_evidence", "structural_activate"]
