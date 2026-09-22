from __future__ import annotations

from pathlib import Path

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


def _evidence(*, authorization_action: str, authorized_state_sequence: int) -> ActivationAdmissionEvidence:
    generation = _generation()
    route = generation.routes[0]
    owner = route.owner_release
    return ActivationAdmissionEvidence(
        deployment_id="orgmetra_gateway",
        environment_id="production",
        generation_id=generation.generation_id,
        config_sha256=generation.config_sha256,
        authorization_action=authorization_action,
        authorized_state_sequence=authorized_state_sequence,
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


def test_activation_evidence_binds_action_and_durable_state_sequence() -> None:
    generation = _generation()
    evidence = _evidence(authorization_action="activate", authorized_state_sequence=0)

    evidence.validate_for(
        deployment_id="orgmetra_gateway",
        environment_id="production",
        generation=generation,
        authorization_action="activate",
        authorized_state_sequence=0,
        now_unix_ms=1_500,
    )

    with pytest.raises(ActivationAuthorizationError, match="authorization action"):
        evidence.validate_for(
            deployment_id="orgmetra_gateway",
            environment_id="production",
            generation=generation,
            authorization_action="rollback",
            authorized_state_sequence=0,
            now_unix_ms=1_500,
        )

    with pytest.raises(ActivationAuthorizationError, match="state sequence"):
        evidence.validate_for(
            deployment_id="orgmetra_gateway",
            environment_id="production",
            generation=generation,
            authorization_action="activate",
            authorized_state_sequence=1,
            now_unix_ms=1_500,
        )


def test_activation_migration_binds_evidence_to_event_kind_and_prior_sequence() -> None:
    migration = (
        Path(__file__).resolve().parents[3]
        / "database"
        / "migrations"
        / "0019_product_composition_activation_registry.sql"
    ).read_text(encoding="utf-8")

    assert "authorization_action text NOT NULL" in migration
    assert "authorized_state_sequence bigint NOT NULL" in migration
    assert "evidence.authorization_action IS DISTINCT FROM NEW.event_kind" in migration
    assert "evidence.authorized_state_sequence IS DISTINCT FROM NEW.activation_sequence - 1" in migration
