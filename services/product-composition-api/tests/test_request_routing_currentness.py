from __future__ import annotations

from contextlib import contextmanager

import pytest

from orgmetra_product_composition import (
    ActivationAdmissionEvidence,
    ActivationEvent,
    AuthorizedPostgresActivationRegistry,
    AuthorizedRecoveredActivation,
    CompositionGeneration,
    CompositionMethodNotAllowedError,
    CompositionRequestError,
    CompositionRoute,
    CompositionRouteNotFoundError,
    CompositionRouteUnavailableError,
    DeploymentIdentity,
    OwnerApiRelease,
    OwnerOperationObservation,
    ReleasedAuthorityEvidence,
    configuration_sha256,
    current_route_id_for_request,
)
from orgmetra_product_composition.serving_snapshot import _issue_route_snapshot


class _Cursor:
    def __init__(self, row: tuple[object, ...]) -> None:
        self.row = row

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql: str, parameters: tuple[object, ...]) -> None:
        assert "product_composition_activation_event" in sql
        assert "product_composition_recovery_attestation" in sql
        assert len(parameters) == 4

    def fetchone(self):
        return self.row


class _Connection:
    def __init__(self, cursor: _Cursor) -> None:
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self._cursor


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


def _fixture(*, concrete_available: bool):
    owner = OwnerApiRelease(
        service_id="people_api",
        release_version="v1.2.3",
        openapi_sha256="1" * 64,
        artifact_sha256="2" * 64,
        release_locator="https://github.com/ContextualWisdomLab/Orgmetra/releases/tag/v1.2.3",
    )
    template = CompositionRoute(
        route_id="people_record",
        path_template="/v1/people/{person_record_id}",
        methods=("GET",),
        owner_release=owner,
        logical_upstream="service://people-api",
        required=True,
    )
    concrete = CompositionRoute(
        route_id="people_current",
        path_template="/v1/people/current",
        methods=("GET",),
        owner_release=owner,
        logical_upstream="service://people-api",
        required=False,
    )
    generation = CompositionGeneration(
        schema_version="orgmetra_gateway_composition.v1",
        generation_id="generation_request_routing",
        routes=(template, concrete),
        config_sha256=configuration_sha256((template, concrete)),
    )
    deployment = DeploymentIdentity("orgmetra_gateway", "production")

    observations = [
        OwnerOperationObservation(
            route_id=template.route_id,
            path_template=template.path_template,
            method="GET",
            service_id=owner.service_id,
            release_version=owner.release_version,
            openapi_sha256=owner.openapi_sha256,
            artifact_sha256=owner.artifact_sha256,
            observation_sha256="8" * 64,
            observed_at_unix_ms=1_000,
            valid_until_unix_ms=2_000,
        )
    ]
    if concrete_available:
        observations.append(
            OwnerOperationObservation(
                route_id=concrete.route_id,
                path_template=concrete.path_template,
                method="GET",
                service_id=owner.service_id,
                release_version=owner.release_version,
                openapi_sha256=owner.openapi_sha256,
                artifact_sha256="2" * 64,
                observation_sha256="9" * 64,
                observed_at_unix_ms=1_000,
                valid_until_unix_ms=2_000,
            )
        )

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
        owner_operations=tuple(observations),
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
    row = (
        event.activation_sequence,
        event.generation_id,
        event.previous_generation_id,
        event.event_kind,
        event.evidence_bundle_sha256,
        snapshot.recovery_sequence,
        evidence.bundle_sha256(),
        snapshot.recovery_sequence,
        1_250,
        1_500,
        False,
    )
    cursor = _Cursor(row)

    @contextmanager
    def connection_factory():
        yield _Connection(cursor)

    def evidence_provider(*args):
        raise AssertionError("request routing must not reacquire external evidence")

    def clock_unix_ms() -> int:
        raise AssertionError("request routing must use serving PostgreSQL currentness")

    registry = AuthorizedPostgresActivationRegistry(
        connection_factory=connection_factory,
        evidence_provider=evidence_provider,
        clock_unix_ms=clock_unix_ms,
    )
    return registry, deployment, snapshot


def test_unavailable_concrete_route_does_not_fall_through_to_available_template() -> None:
    registry, deployment, snapshot = _fixture(concrete_available=False)

    with pytest.raises(CompositionRouteUnavailableError):
        current_route_id_for_request(
            registry,
            deployment,
            snapshot,
            method="GET",
            request_path="/v1/people/current",
        )


def test_available_concrete_route_wins_over_template() -> None:
    registry, deployment, snapshot = _fixture(concrete_available=True)

    assert current_route_id_for_request(
        registry,
        deployment,
        snapshot,
        method="GET",
        request_path="/v1/people/current",
    ) == "people_current"


def test_template_route_matches_one_canonical_path_segment() -> None:
    registry, deployment, snapshot = _fixture(concrete_available=False)

    assert current_route_id_for_request(
        registry,
        deployment,
        snapshot,
        method="GET",
        request_path="/v1/people/person_123",
    ) == "people_record"


def test_method_mismatch_does_not_fall_through_or_invent_owner_method() -> None:
    registry, deployment, snapshot = _fixture(concrete_available=True)

    with pytest.raises(CompositionMethodNotAllowedError):
        current_route_id_for_request(
            registry,
            deployment,
            snapshot,
            method="POST",
            request_path="/v1/people/current",
        )


def test_unknown_path_is_distinct_from_unavailable_declared_route() -> None:
    registry, deployment, snapshot = _fixture(concrete_available=False)

    with pytest.raises(CompositionRouteNotFoundError):
        current_route_id_for_request(
            registry,
            deployment,
            snapshot,
            method="GET",
            request_path="/v1/jobs/job_123",
        )


@pytest.mark.parametrize(
    ("method", "request_path"),
    [
        ("GET", "/v1/people/../person_123"),
        ("GET", "/v1/people/person%2F123"),
        ("GET", "/v1/people/person_123?expand=job"),
    ],
)
def test_request_routing_rejects_noncanonical_transport_inputs(method: str, request_path: str) -> None:
    registry, deployment, snapshot = _fixture(concrete_available=False)

    with pytest.raises(CompositionRequestError):
        current_route_id_for_request(
            registry,
            deployment,
            snapshot,
            method=method,
            request_path=request_path,
        )
