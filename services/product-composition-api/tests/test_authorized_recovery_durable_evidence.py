from __future__ import annotations

import pytest

from orgmetra_product_composition import (
    ActivationAdmissionEvidence,
    ActivationAuthorizationError,
    ActivationEvent,
    ActivationRegistryError,
    AuthorizedPostgresActivationRegistry,
    CompositionGeneration,
    CompositionRoute,
    DeploymentIdentity,
    OwnerApiRelease,
    OwnerOperationObservation,
    RecoveredActivation,
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


def test_activation_event_rejects_invalid_durable_evidence_digest() -> None:
    with pytest.raises(ActivationRegistryError, match="evidence_bundle_sha256"):
        ActivationEvent(
            deployment=DeploymentIdentity("orgmetra_gateway", "production"),
            activation_sequence=1,
            generation_id="generation_one",
            previous_generation_id=None,
            event_kind="activate",
            evidence_bundle_sha256="not_a_digest",
        )


def test_authorized_recovery_rejects_structural_event_without_durable_evidence(monkeypatch) -> None:
    deployment = DeploymentIdentity("orgmetra_gateway", "production")
    generation = _generation()
    structural = RecoveredActivation(
        event=ActivationEvent(
            deployment=deployment,
            activation_sequence=1,
            generation_id=generation.generation_id,
            previous_generation_id=None,
            event_kind="activate",
        ),
        generation=generation,
    )
    provider_calls = 0

    class StructuralRegistry:
        def recover_active(self, deployment_arg):
            assert deployment_arg == deployment
            return structural

    def evidence_provider(deployment_arg, generation_arg):
        nonlocal provider_calls
        provider_calls += 1
        assert deployment_arg == deployment
        assert generation_arg == generation
        return _evidence(generation)

    registry = AuthorizedPostgresActivationRegistry(
        connection_factory=lambda: None,
        evidence_provider=evidence_provider,
        clock_unix_ms=lambda: 1_500,
    )
    monkeypatch.setattr(registry, "_structural_registry", StructuralRegistry())

    with pytest.raises(ActivationAuthorizationError, match="durable authorization evidence"):
        registry.recover_active(deployment)

    assert provider_calls == 0


def test_authorized_recovery_preserves_durable_evidence_identity_and_fresh_re_admission(
    monkeypatch,
) -> None:
    deployment = DeploymentIdentity("orgmetra_gateway", "production")
    generation = _generation()
    durable_evidence_sha256 = "a" * 64
    structural = RecoveredActivation(
        event=ActivationEvent(
            deployment=deployment,
            activation_sequence=1,
            generation_id=generation.generation_id,
            previous_generation_id=None,
            event_kind="activate",
            evidence_bundle_sha256=durable_evidence_sha256,
        ),
        generation=generation,
    )
    evidence = _evidence(generation)
    provider_calls = 0
    structural_reads = 0

    class StructuralRegistry:
        def recover_active(self, deployment_arg):
            nonlocal structural_reads
            structural_reads += 1
            assert deployment_arg == deployment
            return structural

    def evidence_provider(deployment_arg, generation_arg):
        nonlocal provider_calls
        provider_calls += 1
        assert deployment_arg == deployment
        assert generation_arg == generation
        return evidence

    registry = AuthorizedPostgresActivationRegistry(
        connection_factory=lambda: None,
        evidence_provider=evidence_provider,
        clock_unix_ms=lambda: 1_500,
    )
    monkeypatch.setattr(registry, "_structural_registry", StructuralRegistry())

    recovered = registry.recover_active(deployment)

    assert recovered is not None
    assert recovered.event.evidence_bundle_sha256 == durable_evidence_sha256
    assert recovered.evidence == evidence
    assert provider_calls == 1
    assert structural_reads == 2
