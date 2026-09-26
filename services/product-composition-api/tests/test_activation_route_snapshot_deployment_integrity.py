from __future__ import annotations

import pytest

from orgmetra_product_composition import (
    ActivationAdmissionEvidence,
    ActivationAuthorizationError,
    ActivationEvent,
    AuthorizedRecoveredActivation,
    CompositionGeneration,
    CompositionRoute,
    DeploymentIdentity,
    OwnerApiRelease,
    OwnerOperationObservation,
    ReleasedAuthorityEvidence,
    configuration_sha256,
)
from orgmetra_product_composition.serving_snapshot import _issue_route_snapshot


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


def _issued_snapshot():
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
    generation = CompositionGeneration(
        schema_version="orgmetra_gateway_composition.v1",
        generation_id="generation_deployment_binding",
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
    return _issue_route_snapshot(
        AuthorizedRecoveredActivation(
            event=event,
            generation=generation,
            evidence=evidence,
            recovery_sequence=1,
        )
    )


def test_route_snapshot_rejects_equivalent_deployment_object_replacement() -> None:
    """Deployment identity replacement must not preserve issued snapshot authority."""

    snapshot = _issued_snapshot()
    original = snapshot.event.deployment
    replacement = DeploymentIdentity(
        original.deployment_id,
        original.environment_id,
    )
    object.__setattr__(snapshot.event, "deployment", replacement)

    with pytest.raises(ActivationAuthorizationError, match="issuance snapshot"):
        _ = snapshot.available_route_ids


def test_route_snapshot_rejects_same_deployment_object_field_retarget() -> None:
    """Low-level mutation of the issued deployment coordinate must fail before use."""

    snapshot = _issued_snapshot()
    deployment = snapshot.event.deployment
    object.__setattr__(deployment, "deployment_id", "other_gateway")

    with pytest.raises(ActivationAuthorizationError, match="DeploymentIdentity"):
        _ = snapshot.available_route_ids
