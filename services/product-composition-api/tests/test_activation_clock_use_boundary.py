from __future__ import annotations

import pytest

from orgmetra_product_composition import (
    ActivationAdmissionEvidence,
    ActivationAuthorizationError,
    AuthorizedPostgresActivationRegistry,
    CompositionGeneration,
    CompositionRoute,
    DeploymentIdentity,
    OwnerApiRelease,
    configuration_sha256,
)


def _generation() -> CompositionGeneration:
    """Build a valid generation for the focused clock use-boundary contract."""

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


def test_first_clock_read_uses_capability_pinned_before_runtime_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not execute a clock swapped immediately after its runtime-integrity check."""

    replacement_calls: list[int] = []

    def connection_factory() -> None:
        return None

    def provider(*_args: object) -> ActivationAdmissionEvidence:
        raise AssertionError("provider must not run after capability drift")

    def admitted_clock() -> int:
        return 1_500

    def replacement_clock() -> int:
        replacement_calls.append(1)
        return 1_500

    registry = AuthorizedPostgresActivationRegistry(
        connection_factory=connection_factory,  # type: ignore[arg-type]
        evidence_provider=provider,
        clock_unix_ms=admitted_clock,
    )
    original_guard = AuthorizedPostgresActivationRegistry._require_runtime_capabilities
    guard_calls = 0

    def mutate_after_guard(self: AuthorizedPostgresActivationRegistry) -> None:
        nonlocal guard_calls
        original_guard(self)
        guard_calls += 1
        if guard_calls == 1:
            self.clock_unix_ms = replacement_clock

    monkeypatch.setattr(
        AuthorizedPostgresActivationRegistry,
        "_require_runtime_capabilities",
        mutate_after_guard,
    )

    with pytest.raises(ActivationAuthorizationError, match="construction snapshot"):
        registry._obtain_evidence(
            DeploymentIdentity(
                deployment_id="orgmetra_gateway",
                environment_id="production",
            ),
            _generation(),
            authorization_action="activate",
            authorized_state_sequence=0,
        )

    assert replacement_calls == []
