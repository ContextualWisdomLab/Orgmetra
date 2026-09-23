from __future__ import annotations

import pytest

from orgmetra_product_composition import (
    ActivationAdmissionEvidence,
    ActivationAuthorizationError,
    ActivationEvent,
    AuthorizedPostgresActivationRegistry,
    CompositionGeneration,
    CompositionRoute,
    DeploymentIdentity,
    OwnerApiRelease,
    OwnerOperationObservation,
    RecoveredActivation,
    RecoveredRouteSnapshot,
    ReleasedAuthorityEvidence,
    configuration_sha256,
    recover_active_route_snapshot,
)


def _generation() -> CompositionGeneration:
    people = OwnerApiRelease(
        service_id="people_api",
        release_version="v1.2.3",
        openapi_sha256="1" * 64,
        artifact_sha256="2" * 64,
        release_locator="https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3",
    )
    workforce = OwnerApiRelease(
        service_id="workforce_validation_api",
        release_version="v2.0.0",
        openapi_sha256="3" * 64,
        artifact_sha256="4" * 64,
        release_locator="https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v2.0.0",
    )
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
        generation_id="generation_optional",
        routes=routes,
        config_sha256=configuration_sha256(routes),
    )


def _authority(authority_id: str, digest_digit: str) -> ReleasedAuthorityEvidence:
    repository = "keyverse" if authority_id == "keyverse" else "Orgmetra"
    return ReleasedAuthorityEvidence(
        authority_id=authority_id,
        release_version="v1.0.0",
        artifact_sha256=digest_digit * 64,
        release_locator=(
            f"https://github.com/ContextualWisdomLab/{repository}/releases/tag/v1.0.0"
        ),
    )


def _required_only_recovery_evidence(
    generation: CompositionGeneration,
) -> ActivationAdmissionEvidence:
    route = generation.routes[0]
    owner = route.owner_release
    return ActivationAdmissionEvidence(
        deployment_id="orgmetra_gateway",
        environment_id="production",
        generation_id=generation.generation_id,
        config_sha256=generation.config_sha256,
        authorization_action="recover",
        authorized_state_sequence=1,
        keyverse_authority=_authority("keyverse", "5"),
        orgmetra_authority=_authority("orgmetra", "6"),
        orgmetra_policy_version_code="composition_activation_v1",
        authorization_decision_sha256="7" * 64,
        owner_operations=(
            OwnerOperationObservation(
                route_id=route.route_id,
                path_template=route.path_template,
                method="GET",
                service_id=owner.service_id,
                release_version=owner.release_version,
                openapi_sha256=owner.openapi_sha256,
                artifact_sha256=owner.artifact_sha256,
                observation_sha256="8" * 64,
                observed_at_unix_ms=1_000,
                valid_until_unix_ms=2_000,
            ),
        ),
        valid_until_unix_ms=2_000,
    )


def test_route_snapshot_projects_only_after_locked_recovery_recheck_without_post_commit_clock(
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
    evidence = _required_only_recovery_evidence(generation)
    locked_rechecks = 0
    clock_reads = 0

    class StructuralRegistry:
        def __init__(self, connection_factory):
            self.connection_factory = connection_factory

        def recover_active(self, deployment_arg, *, _connection_factory=None):
            assert deployment_arg == deployment
            assert _connection_factory is self.connection_factory
            return structural

        def recover_active_authorized(
            self,
            deployment_arg,
            *,
            expected_activation_sequence,
            expected_generation_id,
            evidence_bundle_sha256,
            evidence_writer,
            _connection_factory=None,
        ):
            nonlocal locked_rechecks
            locked_rechecks += 1
            assert deployment_arg == deployment
            assert expected_activation_sequence == 1
            assert expected_generation_id == generation.generation_id
            assert evidence_bundle_sha256 == evidence.bundle_sha256()
            assert callable(evidence_writer)
            assert _connection_factory is self.connection_factory
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
        if clock_reads > 2:
            raise AssertionError("state-bound route projection must not sample the clock after commit")
        return 1_500

    class ProductRecoveryHarness(AuthorizedPostgresActivationRegistry):
        __slots__ = ()

        def _require_runtime_capabilities(self) -> None:
            return None

    registry = ProductRecoveryHarness(
        connection_factory=lambda: None,
        evidence_provider=evidence_provider,
        clock_unix_ms=clock_unix_ms,
    )
    monkeypatch.setattr(
        registry,
        "_structural_registry",
        StructuralRegistry(registry.connection_factory),
    )

    snapshot = recover_active_route_snapshot(registry, deployment)

    assert type(snapshot) is RecoveredRouteSnapshot
    assert snapshot.event == structural.event
    assert snapshot.generation == generation
    assert snapshot.evidence == evidence
    assert snapshot.available_route_ids == ("people_get",)
    assert locked_rechecks == 1
    assert clock_reads == 2


def test_route_snapshot_value_cannot_be_forged_through_public_constructor() -> None:
    with pytest.raises(ActivationAuthorizationError, match="issued only"):
        RecoveredRouteSnapshot()
