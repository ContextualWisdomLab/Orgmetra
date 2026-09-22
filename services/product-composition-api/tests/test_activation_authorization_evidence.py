from __future__ import annotations

from pathlib import Path

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
from orgmetra_product_composition.activation_authorization import _persist_activation_evidence


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


def _evidence(
    *,
    valid_until_unix_ms: int = 2_000,
    authorization_action: str = "activate",
    authorized_state_sequence: int = 0,
) -> ActivationAdmissionEvidence:
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
        authorization_action="activate",
        authorized_state_sequence=0,
        now_unix_ms=1_500,
    )

    missing = ActivationAdmissionEvidence(
        deployment_id=evidence.deployment_id,
        environment_id=evidence.environment_id,
        generation_id=evidence.generation_id,
        config_sha256=evidence.config_sha256,
        authorization_action=evidence.authorization_action,
        authorized_state_sequence=evidence.authorized_state_sequence,
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
            authorization_action="activate",
            authorized_state_sequence=0,
            now_unix_ms=1_500,
        )


def test_activation_evidence_rejects_expired_or_future_observation() -> None:
    generation = _generation()
    with pytest.raises(ActivationAuthorizationError, match="expired"):
        _evidence(valid_until_unix_ms=1_400).validate_for(
            deployment_id="orgmetra_gateway",
            environment_id="production",
            generation=generation,
            authorization_action="activate",
            authorized_state_sequence=0,
            now_unix_ms=1_500,
        )

    evidence = _evidence()
    current = evidence.owner_operations[0]
    future_observation = OwnerOperationObservation(
        route_id=current.route_id,
        path_template=current.path_template,
        method=current.method,
        service_id=current.service_id,
        release_version=current.release_version,
        openapi_sha256=current.openapi_sha256,
        artifact_sha256=current.artifact_sha256,
        observation_sha256=current.observation_sha256,
        observed_at_unix_ms=1_600,
        valid_until_unix_ms=current.valid_until_unix_ms,
    )
    future = ActivationAdmissionEvidence(
        deployment_id=evidence.deployment_id,
        environment_id=evidence.environment_id,
        generation_id=evidence.generation_id,
        config_sha256=evidence.config_sha256,
        authorization_action=evidence.authorization_action,
        authorized_state_sequence=evidence.authorized_state_sequence,
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
            authorization_action="activate",
            authorized_state_sequence=0,
            now_unix_ms=1_500,
        )


def test_authorized_registry_persists_evidence_inside_structural_activation(monkeypatch) -> None:
    generation = _generation()
    deployment = DeploymentIdentity("orgmetra_gateway", "production")
    evidence = _evidence()
    order: list[str] = []

    class GenerationRegistry:
        def load(self, generation_id: str):
            order.append("load_generation")
            assert generation_id == generation.generation_id
            return generation

    class StructuralRegistry:
        def activate_authorized(
            self,
            deployment_arg,
            *,
            generation_id: str,
            expected_previous_sequence: int,
            evidence_bundle_sha256: str,
            evidence_writer,
        ):
            order.append("structural_activate_authorized")
            assert deployment_arg == deployment
            assert generation_id == generation.generation_id
            assert expected_previous_sequence == 0
            assert evidence_bundle_sha256 == evidence.bundle_sha256()
            assert callable(evidence_writer)
            return object()

    def evidence_provider(deployment_arg, generation_arg, authorization_action, state_sequence):
        order.append("external_evidence")
        assert deployment_arg == deployment
        assert generation_arg == generation
        assert authorization_action == "activate"
        assert state_sequence == 0
        return evidence

    def clock_unix_ms() -> int:
        order.append("freshness_check")
        return 1_500

    registry = AuthorizedPostgresActivationRegistry(
        connection_factory=lambda: None,
        evidence_provider=evidence_provider,
        clock_unix_ms=clock_unix_ms,
    )
    monkeypatch.setattr(registry, "_generation_registry", GenerationRegistry())
    monkeypatch.setattr(registry, "_structural_registry", StructuralRegistry())

    registry.activate(
        deployment,
        generation_id=generation.generation_id,
        expected_previous_sequence=0,
    )

    assert order == [
        "load_generation",
        "external_evidence",
        "freshness_check",
        "structural_activate_authorized",
    ]


class EvidenceCursor:
    def __init__(self, *, root_row, observation_rows) -> None:
        self.root_row = root_row
        self.observation_rows = observation_rows
        self.statements: list[str] = []
        self._fetchone_values = [None, root_row]

    def execute(self, statement: str, params=None) -> None:
        self.statements.append(statement)

    def fetchone(self):
        return self._fetchone_values.pop(0)

    def fetchall(self):
        return list(self.observation_rows)


def test_transaction_evidence_writer_verifies_exact_durable_material() -> None:
    evidence = _evidence()
    cursor = EvidenceCursor(
        root_row=evidence._root_row(),
        observation_rows=evidence._observation_rows(),
    )

    _persist_activation_evidence(cursor, evidence)

    statements = "\n".join(cursor.statements)
    assert "product_composition_activation_evidence" in statements
    assert "product_composition_activation_owner_observation" in statements


def test_transaction_evidence_writer_rejects_digest_collision_material() -> None:
    evidence = _evidence()
    wrong_root = list(evidence._root_row())
    wrong_root[-1] = 9_999
    cursor = EvidenceCursor(
        root_row=tuple(wrong_root),
        observation_rows=evidence._observation_rows(),
    )

    with pytest.raises(ActivationAuthorizationError, match="different durable root material"):
        _persist_activation_evidence(cursor, evidence)


def test_activation_migration_binds_evidence_and_checks_wall_clock_expiry_at_event_insert() -> None:
    migration = (
        Path(__file__).resolve().parents[3]
        / "database"
        / "migrations"
        / "0019_product_composition_activation_registry.sql"
    ).read_text(encoding="utf-8")

    assert "CREATE TABLE product_composition_activation_evidence" in migration
    assert "CREATE TABLE product_composition_activation_owner_observation" in migration
    assert "evidence_bundle_sha256" in migration
    assert "authorization_action" in migration
    assert "authorized_state_sequence" in migration
    assert "authorization_decision_sha256" in migration
    assert "keyverse_release_version" in migration
    assert "orgmetra_policy_version_code" in migration
    assert "clock_timestamp()" in migration
    assert "activation authorization evidence is expired" in migration
