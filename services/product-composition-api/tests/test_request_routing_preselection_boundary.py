from __future__ import annotations

import pytest

from orgmetra_product_composition import (
    ActivationAdmissionEvidence,
    ActivationEvent,
    AuthorizedPostgresActivationRegistry,
    AuthorizedRecoveredActivation,
    CompositionGeneration,
    CompositionMethodNotAllowedError,
    CompositionRoute,
    CompositionRouteNotFoundError,
    DeploymentIdentity,
    OwnerApiRelease,
    OwnerOperationObservation,
    ReleasedAuthorityEvidence,
    configuration_sha256,
    current_route_id_for_request,
)
from orgmetra_product_composition.serving_snapshot import _issue_route_snapshot


def _authority(authority_id: str, digit: str) -> ReleasedAuthorityEvidence:
    repository = "keyverse" if authority_id == "keyverse" else "Orgmetra"
    return ReleasedAuthorityEvidence(
        authority_id=authority_id,
        release_version="v1.0.0",
        artifact_sha256=digit * 64,
        release_locator=(
            f"https://github.com/ContextualWisdomLab/{repository}/releases/tag/v1.0.0"
        ),
    )


def _fixture():
    owner = OwnerApiRelease(
        service_id="people_api",
        release_version="v1.2.3",
        openapi_sha256="1" * 64,
        artifact_sha256="2" * 64,
        release_locator="https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3",
    )
    route = CompositionRoute(
        route_id="people_record",
        path_template="/v1/people/{person_record_id}",
        methods=("GET",),
        owner_release=owner,
        logical_upstream="service://people-api",
        required=True,
    )
    generation = CompositionGeneration(
        schema_version="orgmetra_gateway_composition.v1",
        generation_id="generation_request_preselection",
        routes=(route,),
        config_sha256=configuration_sha256((route,)),
    )
    deployment = DeploymentIdentity("orgmetra_gateway", "production")
    evidence = ActivationAdmissionEvidence(
        deployment_id=deployment.deployment_id,
        environment_id=deployment.environment_id,
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
    event = ActivationEvent(
        deployment=deployment,
        activation_sequence=1,
        generation_id=generation.generation_id,
        previous_generation_id=None,
        event_kind="activate",
        evidence_bundle_sha256="a" * 64,
    )
    snapshot = _issue_route_snapshot(
        AuthorizedRecoveredActivation(
            event=event,
            generation=generation,
            evidence=evidence,
            recovery_sequence=1,
        )
    )

    def connection_factory():
        raise AssertionError(
            "declared path/method rejection must not cross the PostgreSQL currentness boundary"
        )

    def evidence_provider(*args):
        raise AssertionError("request routing must not reacquire external evidence")

    def clock_unix_ms() -> int:
        raise AssertionError("request routing must not use a process-local clock")

    registry = AuthorizedPostgresActivationRegistry(
        connection_factory=connection_factory,
        evidence_provider=evidence_provider,
        clock_unix_ms=clock_unix_ms,
    )
    return registry, deployment, snapshot


def test_unknown_declared_path_is_rejected_before_postgres_currentness() -> None:
    registry, deployment, snapshot = _fixture()

    with pytest.raises(CompositionRouteNotFoundError):
        current_route_id_for_request(
            registry,
            deployment,
            snapshot,
            method="GET",
            request_path="/v1/jobs/job_123",
        )


def test_undeclared_method_is_rejected_before_postgres_currentness() -> None:
    registry, deployment, snapshot = _fixture()

    with pytest.raises(CompositionMethodNotAllowedError):
        current_route_id_for_request(
            registry,
            deployment,
            snapshot,
            method="POST",
            request_path="/v1/people/person_123",
        )
