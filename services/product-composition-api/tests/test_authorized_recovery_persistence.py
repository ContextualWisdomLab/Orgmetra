from __future__ import annotations

from orgmetra_product_composition import (
    ActivationAdmissionEvidence,
    ActivationEvent,
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
        authorization_action="recover",
        authorized_state_sequence=1,
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


def test_recovery_persists_fresh_evidence_only_after_locked_state_recheck(monkeypatch) -> None:
    deployment = DeploymentIdentity("orgmetra_gateway", "production")
    generation = _generation()
    structural = RecoveredActivation(
        event=ActivationEvent(
            deployment=deployment,
            activation_sequence=1,
            generation_id=generation.generation_id,
            previous_generation_id=None,
            event_kind="activate",
            evidence_bundle_sha256="a" * 64,
        ),
        generation=generation,
    )
    evidence = _evidence(generation)
    initial_reads = 0
    locked_rechecks = 0

    class StructuralRegistry:
        def recover_active(self, deployment_arg):
            nonlocal initial_reads
            initial_reads += 1
            assert deployment_arg == deployment
            return structural

        def recover_active_authorized(
            self,
            deployment_arg,
            *,
            expected_activation_sequence,
            expected_generation_id,
            evidence_bundle_sha256,
            evidence_writer,
        ):
            nonlocal locked_rechecks
            locked_rechecks += 1
            assert deployment_arg == deployment
            assert expected_activation_sequence == 1
            assert expected_generation_id == generation.generation_id
            assert evidence_bundle_sha256 == evidence.bundle_sha256()
            assert callable(evidence_writer)
            return structural

    def evidence_provider(deployment_arg, generation_arg, authorization_action, state_sequence):
        assert deployment_arg == deployment
        assert generation_arg == generation
        assert authorization_action == "recover"
        assert state_sequence == 1
        return evidence

    registry = AuthorizationRegistry(
        connection_factory=lambda: None,
        evidence_provider=evidence_provider,
        clock_unix_ms=lambda: 1_500,
    )
    monkeypatch.setattr(registry, "_structural_registry", StructuralRegistry())

    recovered = registry.recover_active(deployment)

    assert recovered is not None
    assert recovered.event == structural.event
    assert recovered.evidence == evidence
    assert initial_reads == 1
    assert locked_rechecks == 1


def test_product_recovery_does_not_reclassify_committed_attestation_with_post_commit_clock(
    monkeypatch,
) -> None:
    deployment = DeploymentIdentity("orgmetra_gateway", "production")
    generation = _generation()
    structural = RecoveredActivation(
        event=ActivationEvent(
            deployment=deployment,
            activation_sequence=1,
            generation_id=generation.generation_id,
            previous_generation_id=None,
            event_kind="activate",
            evidence_bundle_sha256="a" * 64,
        ),
        generation=generation,
    )
    evidence = _evidence(generation)
    clock_reads = 0

    class StructuralRegistry:
        def recover_active(self, deployment_arg):
            assert deployment_arg == deployment
            return structural

        def recover_active_authorized(
            self,
            deployment_arg,
            *,
            expected_activation_sequence,
            expected_generation_id,
            evidence_bundle_sha256,
            evidence_writer,
        ):
            assert deployment_arg == deployment
            assert expected_activation_sequence == 1
            assert expected_generation_id == generation.generation_id
            assert evidence_bundle_sha256 == evidence.bundle_sha256()
            assert callable(evidence_writer)
            return structural

    def evidence_provider(deployment_arg, generation_arg, authorization_action, state_sequence):
        assert deployment_arg == deployment
        assert generation_arg == generation
        assert authorization_action == "recover"
        assert state_sequence == 1
        return evidence

    def clock_unix_ms() -> int:
        nonlocal clock_reads
        clock_reads += 1
        return 1_500 if clock_reads <= 2 else 2_500

    class ProductRecoveryHarness(AuthorizedPostgresActivationRegistry):
        __slots__ = ()

        def _require_runtime_capabilities(self) -> None:
            return None

    registry = ProductRecoveryHarness(
        connection_factory=lambda: None,
        evidence_provider=evidence_provider,
        clock_unix_ms=clock_unix_ms,
    )
    monkeypatch.setattr(registry, "_structural_registry", StructuralRegistry())

    recovered = registry.recover_active(deployment)

    assert recovered is not None
    assert recovered.evidence == evidence
    assert clock_reads == 2
