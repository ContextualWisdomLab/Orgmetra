from __future__ import annotations

from collections.abc import Callable

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
    ReleasedAuthorityEvidence,
    configuration_sha256,
)
from orgmetra_product_composition.activation import PostgresActivationRegistry
from orgmetra_product_composition.postgres_registry import PostgresGenerationRegistry


def _generation(generation_id: str = "generation_one") -> CompositionGeneration:
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
        generation_id=generation_id,
        routes=routes,
        config_sha256=configuration_sha256(routes),
    )


def _authority(authority_id: str, repository: str, digest: str) -> ReleasedAuthorityEvidence:
    return ReleasedAuthorityEvidence(
        authority_id=authority_id,
        release_version="v1.0.0",
        artifact_sha256=digest,
        release_locator=f"https://github.com/ContextualWisdomLab/{repository}/releases/tag/v1.0.0",
    )


def _evidence(
    generation: CompositionGeneration,
    *,
    action: str = "activate",
    state_sequence: int = 0,
) -> ActivationAdmissionEvidence:
    route = generation.routes[0]
    owner = route.owner_release
    return ActivationAdmissionEvidence(
        deployment_id="orgmetra_gateway",
        environment_id="production",
        generation_id=generation.generation_id,
        config_sha256=generation.config_sha256,
        authorization_action=action,  # type: ignore[arg-type]
        authorized_state_sequence=state_sequence,
        keyverse_authority=_authority("keyverse", "keyverse", "3" * 64),
        orgmetra_authority=_authority("orgmetra", "Orgmetra", "4" * 64),
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
                valid_until_unix_ms=3_000,
            ),
        ),
        valid_until_unix_ms=3_000,
    )


def _registry() -> AuthorizedPostgresActivationRegistry:
    def connection_factory() -> None:
        return None

    def provider(*_args: object) -> ActivationAdmissionEvidence:
        raise AssertionError("provider is replaced by the focused runtime-integrity contract")

    def clock() -> int:
        return 1_500

    return AuthorizedPostgresActivationRegistry(
        connection_factory=connection_factory,  # type: ignore[arg-type]
        evidence_provider=provider,
        clock_unix_ms=clock,
    )


def test_generation_registry_use_is_pinned_before_runtime_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A retarget immediately after the guard must not change which adapter performs the load."""

    registry = _registry()
    admitted_registry = registry._generation_registry

    def alternate_factory() -> None:
        return None

    replacement_registry = PostgresGenerationRegistry(alternate_factory)  # type: ignore[arg-type]
    expected_generation = _generation("generation_one")
    retargeted_generation = _generation("generation_two")

    def fake_load(self: PostgresGenerationRegistry, _generation_id: str) -> CompositionGeneration:
        return expected_generation if self is admitted_registry else retargeted_generation

    monkeypatch.setattr(PostgresGenerationRegistry, "load", fake_load)
    original_guard = AuthorizedPostgresActivationRegistry._require_runtime_capabilities

    def mutate_after_guard(self: AuthorizedPostgresActivationRegistry) -> None:
        original_guard(self)
        self._generation_registry = replacement_registry

    monkeypatch.setattr(
        AuthorizedPostgresActivationRegistry,
        "_require_runtime_capabilities",
        mutate_after_guard,
    )

    assert registry._load_target("generation_one") is expected_generation


@pytest.mark.parametrize(
    ("operation_name", "state_sequence"),
    (("activate", 0), ("rollback", 1)),
)
def test_transition_rechecks_and_pins_structural_registry_after_evidence(
    monkeypatch: pytest.MonkeyPatch,
    operation_name: str,
    state_sequence: int,
) -> None:
    """Evidence completion must not leave a retargetable gap before the durable transition."""

    registry = _registry()
    generation = _generation()
    evidence = _evidence(
        generation,
        action=operation_name,
        state_sequence=state_sequence,
    )

    def alternate_factory() -> None:
        return None

    replacement_registry = PostgresActivationRegistry(alternate_factory)  # type: ignore[arg-type]

    def fake_load_target(
        self: AuthorizedPostgresActivationRegistry,
        _generation_id: str,
    ) -> CompositionGeneration:
        return generation

    def retarget_after_evidence(
        self: AuthorizedPostgresActivationRegistry,
        *_args: object,
        **_kwargs: object,
    ) -> ActivationAdmissionEvidence:
        self._structural_registry = replacement_registry
        return evidence

    def unexpected_transition(
        self: PostgresActivationRegistry,
        deployment: DeploymentIdentity,
        **_kwargs: object,
    ) -> ActivationEvent:
        previous_generation_id = None if state_sequence == 0 else "generation_previous"
        return ActivationEvent(
            deployment=deployment,
            activation_sequence=state_sequence + 1,
            generation_id=generation.generation_id,
            previous_generation_id=previous_generation_id,
            event_kind=operation_name,  # type: ignore[arg-type]
            evidence_bundle_sha256=evidence.bundle_sha256(),
        )

    monkeypatch.setattr(AuthorizedPostgresActivationRegistry, "_load_target", fake_load_target)
    monkeypatch.setattr(
        AuthorizedPostgresActivationRegistry,
        "_obtain_evidence",
        retarget_after_evidence,
    )
    method_name = f"{operation_name}_authorized"
    monkeypatch.setattr(PostgresActivationRegistry, method_name, unexpected_transition)

    operation: Callable[..., object] = getattr(registry, operation_name)
    with pytest.raises(ActivationAuthorizationError, match="construction snapshot"):
        operation(
            DeploymentIdentity(
                deployment_id="orgmetra_gateway",
                environment_id="production",
            ),
            generation_id=generation.generation_id,
            expected_previous_sequence=state_sequence,
        )


def test_generation_connection_factory_retarget_after_guard_never_executes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A nested generation DB factory swapped after the guard must not execute once."""

    registry = _registry()
    replacement_calls = 0

    def replacement_factory() -> None:
        nonlocal replacement_calls
        replacement_calls += 1
        raise AssertionError("unadmitted generation connection factory executed")

    original_guard = AuthorizedPostgresActivationRegistry._require_runtime_capabilities
    mutated = False

    def mutate_nested_factory_after_guard(self: AuthorizedPostgresActivationRegistry) -> None:
        nonlocal mutated
        original_guard(self)
        if not mutated:
            object.__setattr__(
                self._generation_registry,
                "connection_factory",
                replacement_factory,
            )
            mutated = True

    monkeypatch.setattr(
        AuthorizedPostgresActivationRegistry,
        "_require_runtime_capabilities",
        mutate_nested_factory_after_guard,
    )

    with pytest.raises(ActivationAuthorizationError, match="construction snapshot"):
        registry._load_target("generation_one")

    assert replacement_calls == 0


@pytest.mark.parametrize(
    ("operation_name", "state_sequence"),
    (("activate", 0), ("rollback", 1)),
)
def test_transition_connection_factory_retarget_after_guard_never_executes(
    monkeypatch: pytest.MonkeyPatch,
    operation_name: str,
    state_sequence: int,
) -> None:
    """A nested structural DB factory swapped after the guard must not execute once."""

    registry = _registry()
    generation = _generation()
    evidence = _evidence(
        generation,
        action=operation_name,
        state_sequence=state_sequence,
    )
    replacement_calls = 0

    def replacement_factory() -> None:
        nonlocal replacement_calls
        replacement_calls += 1
        raise AssertionError("unadmitted structural connection factory executed")

    def fake_load_target(
        self: AuthorizedPostgresActivationRegistry,
        _generation_id: str,
    ) -> CompositionGeneration:
        return generation

    def fake_obtain_evidence(
        self: AuthorizedPostgresActivationRegistry,
        *_args: object,
        **_kwargs: object,
    ) -> ActivationAdmissionEvidence:
        return evidence

    original_guard = AuthorizedPostgresActivationRegistry._require_runtime_capabilities
    mutated = False

    def mutate_nested_factory_after_guard(self: AuthorizedPostgresActivationRegistry) -> None:
        nonlocal mutated
        original_guard(self)
        if not mutated:
            object.__setattr__(
                self._structural_registry,
                "connection_factory",
                replacement_factory,
            )
            mutated = True

    monkeypatch.setattr(AuthorizedPostgresActivationRegistry, "_load_target", fake_load_target)
    monkeypatch.setattr(
        AuthorizedPostgresActivationRegistry,
        "_obtain_evidence",
        fake_obtain_evidence,
    )
    monkeypatch.setattr(
        AuthorizedPostgresActivationRegistry,
        "_require_runtime_capabilities",
        mutate_nested_factory_after_guard,
    )

    operation: Callable[..., object] = getattr(registry, operation_name)
    with pytest.raises(ActivationAuthorizationError, match="construction snapshot"):
        operation(
            DeploymentIdentity(
                deployment_id="orgmetra_gateway",
                environment_id="production",
            ),
            generation_id=generation.generation_id,
            expected_previous_sequence=state_sequence,
        )

    assert replacement_calls == 0
