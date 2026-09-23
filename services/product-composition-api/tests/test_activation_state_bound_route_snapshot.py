from __future__ import annotations

from typing import cast

import pytest

from orgmetra_product_composition import (
    ActivationAdmissionEvidence,
    ActivationAuthorizationError,
    ActivationEvent,
    AuthorizedPostgresActivationRegistry,
    AuthorizedRecoveredActivation,
    CompositionGeneration,
    CompositionRoute,
    DeploymentIdentity,
    OwnerApiRelease,
    OwnerOperationObservation,
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


def _registry() -> AuthorizedPostgresActivationRegistry:
    def connection_factory():
        raise AssertionError("route snapshot test must not open PostgreSQL directly")

    def evidence_provider(*args):
        raise AssertionError("route snapshot test delegates re-admission to recover_active")

    def clock_unix_ms() -> int:
        raise AssertionError("route snapshot projection must not sample a post-commit clock")

    return AuthorizedPostgresActivationRegistry(
        connection_factory=connection_factory,
        evidence_provider=evidence_provider,
        clock_unix_ms=clock_unix_ms,
    )


def _authorized_recovery(
    deployment: DeploymentIdentity,
    generation: CompositionGeneration,
    evidence: ActivationAdmissionEvidence,
) -> AuthorizedRecoveredActivation:
    return AuthorizedRecoveredActivation(
        event=ActivationEvent(
            deployment=deployment,
            activation_sequence=1,
            generation_id=generation.generation_id,
            previous_generation_id=None,
            event_kind="activate",
            evidence_bundle_sha256="a" * 64,
        ),
        generation=generation,
        evidence=evidence,
    )


def test_route_snapshot_projects_only_after_authorized_recovery_commit(monkeypatch) -> None:
    deployment = DeploymentIdentity("orgmetra_gateway", "production")
    generation = _generation()
    evidence = _required_only_recovery_evidence(generation)
    recovered = _authorized_recovery(deployment, generation, evidence)
    registry = _registry()
    recovery_calls = 0

    def recover_active(self, deployment_arg):
        nonlocal recovery_calls
        recovery_calls += 1
        assert self is registry
        assert deployment_arg == deployment
        return recovered

    monkeypatch.setattr(AuthorizedPostgresActivationRegistry, "recover_active", recover_active)

    snapshot = recover_active_route_snapshot(registry, deployment)

    assert type(snapshot) is RecoveredRouteSnapshot
    assert snapshot.event == recovered.event
    assert snapshot.generation == generation
    assert snapshot.evidence == evidence
    assert snapshot.available_route_ids == ("people_get",)
    assert recovery_calls == 1


def test_route_snapshot_returns_none_when_no_generation_is_active(monkeypatch) -> None:
    deployment = DeploymentIdentity("orgmetra_gateway", "production")
    registry = _registry()

    def recover_active(self, deployment_arg):
        assert self is registry
        assert deployment_arg == deployment
        return None

    monkeypatch.setattr(AuthorizedPostgresActivationRegistry, "recover_active", recover_active)

    assert recover_active_route_snapshot(registry, deployment) is None


def test_route_snapshot_rejects_non_registry_and_noncanonical_recovery_result(monkeypatch) -> None:
    deployment = DeploymentIdentity("orgmetra_gateway", "production")

    with pytest.raises(ActivationAuthorizationError, match="requires exact"):
        recover_active_route_snapshot(
            cast(AuthorizedPostgresActivationRegistry, object()),
            deployment,
        )

    registry = _registry()

    def recover_active(self, deployment_arg):
        assert self is registry
        assert deployment_arg == deployment
        return object()

    monkeypatch.setattr(AuthorizedPostgresActivationRegistry, "recover_active", recover_active)
    with pytest.raises(ActivationAuthorizationError, match="exact AuthorizedRecoveredActivation"):
        recover_active_route_snapshot(registry, deployment)


def test_route_snapshot_value_cannot_be_forged_through_public_constructor() -> None:
    with pytest.raises(ActivationAuthorizationError, match="issued only"):
        RecoveredRouteSnapshot()
