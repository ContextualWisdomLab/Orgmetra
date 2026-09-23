from __future__ import annotations

from contextlib import contextmanager

import pytest

from orgmetra_product_composition import (
    ActivationAdmissionEvidence,
    ActivationAuthorizationError,
    ActivationConflictError,
    ActivationEvent,
    AuthorizedPostgresActivationRegistry,
    AuthorizedRecoveredActivation,
    CompositionGeneration,
    CompositionRoute,
    DeploymentIdentity,
    OwnerApiRelease,
    OwnerOperationObservation,
    ReleasedAuthorityEvidence,
    configuration_sha256,
    current_route_ids_for_snapshot,
)
from orgmetra_product_composition.serving_snapshot import _issue_route_snapshot


class _Cursor:
    def __init__(self, row):
        self.row = row
        self.executions: list[tuple[str, tuple[object, ...]]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql: str, parameters: tuple[object, ...]) -> None:
        self.executions.append((sql, parameters))

    def fetchone(self):
        return self.row


class _Connection:
    def __init__(self, cursor: _Cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self._cursor


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


def _snapshot():
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
        generation_id="generation_serving_recovery_attestation",
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
    return deployment, snapshot


def _current_row(
    snapshot,
    *,
    recovered_at_unix_ms=1_250,
    now_unix_ms=1_500,
    recovery_clock_rewound=False,
):
    event = snapshot.event
    return (
        event.activation_sequence,
        event.generation_id,
        event.previous_generation_id,
        event.event_kind,
        event.evidence_bundle_sha256,
        snapshot.recovery_sequence,
        snapshot.evidence.bundle_sha256(),
        recovered_at_unix_ms,
        now_unix_ms,
        recovery_clock_rewound,
    )


def _registry(row):
    cursor = _Cursor(row)

    @contextmanager
    def connection_factory():
        yield _Connection(cursor)

    def evidence_provider(*args):
        raise AssertionError("serving currentness must not reacquire external evidence")

    def clock_unix_ms() -> int:
        raise AssertionError("serving currentness must use PostgreSQL wall clock")

    registry = AuthorizedPostgresActivationRegistry(
        connection_factory=connection_factory,
        evidence_provider=evidence_provider,
        clock_unix_ms=clock_unix_ms,
    )
    return registry, cursor


def test_current_route_ids_require_the_exact_snapshot_recovery_attestation_to_still_exist() -> None:
    deployment, snapshot = _snapshot()
    registry, cursor = _registry(_current_row(snapshot))

    assert current_route_ids_for_snapshot(registry, deployment, snapshot) == ("people_get",)
    assert len(cursor.executions) == 1
    sql, parameters = cursor.executions[0]
    assert "public.product_composition_recovery_attestation" in sql
    assert "recovery_attestation.recovery_sequence = %s" in sql
    assert "serving_clock AS MATERIALIZED" in sql
    assert (
        "serving_clock.observed_at < recovery_attestation.recovered_at AS recovery_clock_rewound"
        in sql
    )
    assert parameters == (
        deployment.deployment_id,
        deployment.environment_id,
        snapshot.recovery_sequence,
        snapshot.evidence.bundle_sha256(),
    )


def test_current_route_ids_reject_database_restore_that_lost_the_recovery_attestation() -> None:
    deployment, snapshot = _snapshot()
    row = list(_current_row(snapshot))
    row[5] = None
    row[6] = None
    row[7] = None
    row[9] = None
    registry, _ = _registry(tuple(row))

    with pytest.raises(ActivationConflictError, match="recovery attestation"):
        current_route_ids_for_snapshot(registry, deployment, snapshot)


def test_current_route_ids_reject_same_digest_from_another_recovery_sequence() -> None:
    deployment, snapshot = _snapshot()
    row = list(_current_row(snapshot))
    row[5] = snapshot.recovery_sequence + 1
    registry, _ = _registry(tuple(row))

    with pytest.raises(ActivationConflictError, match="recovery attestation"):
        current_route_ids_for_snapshot(registry, deployment, snapshot)


def test_current_route_ids_reject_database_wall_clock_rewind_before_recovery_commit() -> None:
    deployment, snapshot = _snapshot()
    registry, _ = _registry(
        _current_row(snapshot, recovered_at_unix_ms=1_600, now_unix_ms=1_500)
    )

    with pytest.raises(ActivationAuthorizationError, match="behind recovery attestation"):
        current_route_ids_for_snapshot(registry, deployment, snapshot)


def test_current_route_ids_reject_submillisecond_database_wall_clock_rewind() -> None:
    deployment, snapshot = _snapshot()
    registry, _ = _registry(
        _current_row(
            snapshot,
            recovered_at_unix_ms=1_500,
            now_unix_ms=1_500,
            recovery_clock_rewound=True,
        )
    )

    with pytest.raises(ActivationAuthorizationError, match="behind recovery attestation"):
        current_route_ids_for_snapshot(registry, deployment, snapshot)
