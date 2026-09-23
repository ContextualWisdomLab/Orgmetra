from __future__ import annotations

import gc
from typing import cast
from weakref import ref

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
from orgmetra_product_composition.serving_snapshot import (
    _issue_route_snapshot,
    _record_route_snapshot_integrity,
)


def _generation(generation_id: str = "generation_optional") -> CompositionGeneration:
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
        generation_id=generation_id,
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


def _recovery_evidence(
    generation: CompositionGeneration,
    *,
    action: str = "recover",
    state_sequence: int = 1,
    include_optional: bool = False,
    config_sha256: str | None = None,
) -> ActivationAdmissionEvidence:
    required_route, optional_route = generation.routes
    required_owner = required_route.owner_release
    owner_operations = [
        OwnerOperationObservation(
            route_id=required_route.route_id,
            path_template=required_route.path_template,
            method="GET",
            service_id=required_owner.service_id,
            release_version=required_owner.release_version,
            openapi_sha256=required_owner.openapi_sha256,
            artifact_sha256=required_owner.artifact_sha256,
            observation_sha256="8" * 64,
            observed_at_unix_ms=1_000,
            valid_until_unix_ms=2_000,
        )
    ]
    if include_optional:
        optional_owner = optional_route.owner_release
        for method, digest in (("GET", "9"), ("POST", "4")):
            owner_operations.append(
                OwnerOperationObservation(
                    route_id=optional_route.route_id,
                    path_template=optional_route.path_template,
                    method=method,
                    service_id=optional_owner.service_id,
                    release_version=optional_owner.release_version,
                    openapi_sha256=optional_owner.openapi_sha256,
                    artifact_sha256=optional_owner.artifact_sha256,
                    observation_sha256=digest * 64,
                    observed_at_unix_ms=1_000,
                    valid_until_unix_ms=2_000,
                )
            )
    return ActivationAdmissionEvidence(
        deployment_id="orgmetra_gateway",
        environment_id="production",
        generation_id=generation.generation_id,
        config_sha256=(generation.config_sha256 if config_sha256 is None else config_sha256),
        authorization_action=cast(object, action),
        authorized_state_sequence=state_sequence,
        keyverse_authority=_authority("keyverse", "5"),
        orgmetra_authority=_authority("orgmetra", "6"),
        orgmetra_policy_version_code="composition_activation_v1",
        authorization_decision_sha256="7" * 64,
        owner_operations=tuple(owner_operations),
        valid_until_unix_ms=2_000,
    )


def _event(
    deployment: DeploymentIdentity,
    generation: CompositionGeneration,
    *,
    evidence_bundle_sha256: str | None = "a" * 64,
) -> ActivationEvent:
    return ActivationEvent(
        deployment=deployment,
        activation_sequence=1,
        generation_id=generation.generation_id,
        previous_generation_id=None,
        event_kind="activate",
        evidence_bundle_sha256=evidence_bundle_sha256,
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


def _issue_snapshot(
    monkeypatch,
    *,
    generation: CompositionGeneration | None = None,
    evidence: ActivationAdmissionEvidence | None = None,
    event: ActivationEvent | None = None,
) -> RecoveredRouteSnapshot:
    deployment = DeploymentIdentity("orgmetra_gateway", "production")
    generation_value = _generation() if generation is None else generation
    evidence_value = (
        _recovery_evidence(generation_value) if evidence is None else evidence
    )
    event_value = _event(deployment, generation_value) if event is None else event
    recovered = AuthorizedRecoveredActivation(
        event=event_value,
        generation=generation_value,
        evidence=evidence_value,
        recovery_sequence=1,
    )
    registry = _registry()

    def recover_active(self, deployment_arg):
        assert self is registry
        assert deployment_arg == deployment
        return recovered

    monkeypatch.setattr(AuthorizedPostgresActivationRegistry, "recover_active", recover_active)
    snapshot = recover_active_route_snapshot(registry, deployment)
    assert snapshot is not None
    return snapshot


@pytest.mark.parametrize(
    ("include_optional", "expected_route_ids"),
    [
        (False, ("people_get",)),
        (True, ("people_get", "workforce_validation")),
    ],
)
def test_route_snapshot_projects_recovery_bound_whole_route_coverage(
    monkeypatch,
    include_optional,
    expected_route_ids,
) -> None:
    generation = _generation()
    evidence = _recovery_evidence(generation, include_optional=include_optional)
    snapshot = _issue_snapshot(monkeypatch, generation=generation, evidence=evidence)

    assert type(snapshot) is RecoveredRouteSnapshot
    assert snapshot.event.generation_id == generation.generation_id
    assert snapshot.generation == generation
    assert snapshot.evidence == evidence
    assert snapshot.recovery_sequence == 1
    assert snapshot.available_route_ids == expected_route_ids


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


def test_route_snapshot_requires_committed_recovery_sequence() -> None:
    deployment = DeploymentIdentity("orgmetra_gateway", "production")
    generation = _generation()
    evidence = _recovery_evidence(generation)
    recovered = AuthorizedRecoveredActivation(
        event=_event(deployment, generation),
        generation=generation,
        evidence=evidence,
    )

    with pytest.raises(ActivationAuthorizationError, match="committed recovery attestation sequence"):
        _issue_route_snapshot(recovered)


def test_route_snapshot_value_cannot_be_forged_through_public_constructor() -> None:
    with pytest.raises(ActivationAuthorizationError, match="issued only"):
        RecoveredRouteSnapshot()


def test_route_snapshot_rejects_unissued_raw_object_before_property_access() -> None:
    snapshot = object.__new__(RecoveredRouteSnapshot)
    with pytest.raises(ActivationAuthorizationError, match="not a canonically issued value"):
        _ = snapshot.available_route_ids


def test_route_snapshot_rejects_fully_populated_but_unissued_raw_object(monkeypatch) -> None:
    issued = _issue_snapshot(monkeypatch)
    raw = object.__new__(RecoveredRouteSnapshot)
    object.__setattr__(raw, "_event", issued.event)
    object.__setattr__(raw, "_generation", issued.generation)
    object.__setattr__(raw, "_evidence", issued.evidence)
    object.__setattr__(raw, "_recovery_sequence", issued.recovery_sequence)
    object.__setattr__(raw, "_available_route_ids", issued.available_route_ids)

    with pytest.raises(ActivationAuthorizationError, match="issuance snapshot"):
        _ = raw.available_route_ids


@pytest.mark.parametrize(
    ("field_name", "replacement", "message"),
    [
        ("_event", object(), "exact ActivationEvent"),
        ("_generation", object(), "exact CompositionGeneration"),
        ("_evidence", object(), "exact ActivationAdmissionEvidence"),
        ("_recovery_sequence", True, "recovery sequence"),
        ("_recovery_sequence", 0, "recovery sequence"),
        ("_available_route_ids", ["people_get"], "exact tuple of str"),
        ("_available_route_ids", (object(),), "exact tuple of str"),
    ],
)
def test_route_snapshot_rejects_invalid_nested_types(
    monkeypatch,
    field_name,
    replacement,
    message,
) -> None:
    snapshot = _issue_snapshot(monkeypatch)
    object.__setattr__(snapshot, field_name, replacement)

    with pytest.raises(ActivationAuthorizationError, match=message):
        _ = snapshot.available_route_ids


def test_route_snapshot_rejects_event_generation_retarget(monkeypatch) -> None:
    snapshot = _issue_snapshot(monkeypatch)
    object.__setattr__(snapshot.event, "generation_id", "generation_other")

    with pytest.raises(ActivationAuthorizationError, match="event and generation must agree"):
        _ = snapshot.available_route_ids


def test_route_snapshot_rejects_evidence_generation_retarget(monkeypatch) -> None:
    snapshot = _issue_snapshot(monkeypatch)
    other_generation = _generation("generation_other")
    other_evidence = _recovery_evidence(other_generation)
    object.__setattr__(snapshot, "_evidence", other_evidence)

    with pytest.raises(ActivationAuthorizationError, match="evidence and generation must agree"):
        _ = snapshot.available_route_ids


def test_route_snapshot_rejects_evidence_config_retarget(monkeypatch) -> None:
    generation = _generation()
    snapshot = _issue_snapshot(monkeypatch, generation=generation)
    wrong_config = _recovery_evidence(generation, config_sha256="f" * 64)
    object.__setattr__(snapshot, "_evidence", wrong_config)

    with pytest.raises(ActivationAuthorizationError, match="evidence and generation must agree"):
        _ = snapshot.available_route_ids


def test_route_snapshot_requires_recovery_intent(monkeypatch) -> None:
    generation = _generation()
    snapshot = _issue_snapshot(monkeypatch, generation=generation)
    activate_evidence = _recovery_evidence(generation, action="activate")
    object.__setattr__(snapshot, "_evidence", activate_evidence)

    with pytest.raises(ActivationAuthorizationError, match="recovery authorization"):
        _ = snapshot.available_route_ids


def test_route_snapshot_requires_exact_activation_sequence(monkeypatch) -> None:
    generation = _generation()
    snapshot = _issue_snapshot(monkeypatch, generation=generation)
    wrong_sequence = _recovery_evidence(generation, state_sequence=2)
    object.__setattr__(snapshot, "_evidence", wrong_sequence)

    with pytest.raises(ActivationAuthorizationError, match="bind the activation sequence"):
        _ = snapshot.available_route_ids


def test_route_snapshot_requires_authorized_durable_activation(monkeypatch) -> None:
    deployment = DeploymentIdentity("orgmetra_gateway", "production")
    generation = _generation()
    snapshot = _issue_snapshot(monkeypatch, generation=generation)
    object.__setattr__(
        snapshot,
        "_event",
        _event(deployment, generation, evidence_bundle_sha256=None),
    )

    with pytest.raises(ActivationAuthorizationError, match="authorized durable activation"):
        _ = snapshot.available_route_ids


def test_route_snapshot_rejects_route_coverage_retarget(monkeypatch) -> None:
    snapshot = _issue_snapshot(monkeypatch)
    object.__setattr__(
        snapshot,
        "_available_route_ids",
        ("people_get", "workforce_validation"),
    )

    with pytest.raises(ActivationAuthorizationError, match="issued route coverage"):
        _ = snapshot.available_route_ids


def test_route_snapshot_detects_equivalent_object_identity_replacement(monkeypatch) -> None:
    snapshot = _issue_snapshot(monkeypatch)
    original = snapshot.event
    replacement = ActivationEvent(
        deployment=original.deployment,
        activation_sequence=original.activation_sequence,
        generation_id=original.generation_id,
        previous_generation_id=original.previous_generation_id,
        event_kind=original.event_kind,
        evidence_bundle_sha256=original.evidence_bundle_sha256,
    )
    object.__setattr__(snapshot, "_event", replacement)

    with pytest.raises(ActivationAuthorizationError, match="issuance snapshot"):
        _ = snapshot.available_route_ids


def test_route_snapshot_cannot_be_recorded_twice(monkeypatch) -> None:
    snapshot = _issue_snapshot(monkeypatch)
    with pytest.raises(ActivationAuthorizationError, match="already issued"):
        _record_route_snapshot_integrity(snapshot)


def test_route_snapshot_integrity_state_does_not_extend_lifetime(monkeypatch) -> None:
    snapshot = _issue_snapshot(monkeypatch)
    snapshot_ref = ref(snapshot)

    del snapshot
    gc.collect()

    assert snapshot_ref() is None
