from __future__ import annotations

import gc
import weakref

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


def test_external_evidence_provider_cannot_retarget_runtime_clock_after_construction() -> None:
    evidence, generation = _evidence()
    deployment = DeploymentIdentity(
        deployment_id="orgmetra_gateway",
        environment_id="production",
    )
    holder: dict[str, AuthorizedPostgresActivationRegistry] = {}

    def provider(*_args: object) -> ActivationAdmissionEvidence:
        holder["registry"].clock_unix_ms = lambda: 1_500
        return evidence

    registry = AuthorizedPostgresActivationRegistry(
        connection_factory=lambda: None,
        evidence_provider=provider,
        clock_unix_ms=lambda: 2_500,
    )
    holder["registry"] = registry

    with pytest.raises(ActivationAuthorizationError, match="construction snapshot"):
        registry._obtain_evidence(
            deployment,
            generation,
            authorization_action="activate",
            authorized_state_sequence=0,
        )


def test_runtime_capability_snapshot_keeps_non_reusable_identity_witness() -> None:
    """A collected admitted capability stays invalid even if a later address is reused."""

    class Clock:
        def __call__(self) -> int:
            return 1_500

    clock = Clock()
    admitted_clock = weakref.ref(clock)
    registry = AuthorizedPostgresActivationRegistry(
        connection_factory=lambda: None,
        evidence_provider=lambda *_args: None,  # type: ignore[return-value]
        clock_unix_ms=clock,
    )

    registry.clock_unix_ms = Clock()
    del clock
    gc.collect()

    assert admitted_clock() is None
    with pytest.raises(ActivationAuthorizationError, match="construction snapshot"):
        registry._require_runtime_capabilities()


def test_runtime_capability_snapshot_does_not_root_registry_through_provider_cycle() -> None:
    """Identity evidence must not turn a callback cycle into process-lifetime retention."""

    class Provider:
        registry: AuthorizedPostgresActivationRegistry | None = None

        def __call__(self, *_args: object) -> ActivationAdmissionEvidence:
            raise AssertionError("provider is not executed in this lifetime contract")

    provider = Provider()
    registry = AuthorizedPostgresActivationRegistry(
        connection_factory=lambda: None,
        evidence_provider=provider,
        clock_unix_ms=lambda: 1_500,
    )
    provider.registry = registry
    registry_reference = weakref.ref(registry)
    provider_reference = weakref.ref(provider)

    del registry
    del provider
    gc.collect()

    assert registry_reference() is None
    assert provider_reference() is None


def test_runtime_capabilities_must_support_non_rooting_identity_evidence() -> None:
    """Fail closed when a callable cannot provide a weak-reference identity witness."""

    class NonWeakClock:
        __slots__ = ()

        def __call__(self) -> int:
            return 1_500

    with pytest.raises(TypeError, match="clock_unix_ms must support weak-reference identity"):
        AuthorizedPostgresActivationRegistry(
            connection_factory=lambda: None,
            evidence_provider=lambda *_args: None,  # type: ignore[return-value]
            clock_unix_ms=NonWeakClock(),
        )
