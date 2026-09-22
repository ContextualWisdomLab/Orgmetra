from __future__ import annotations

from collections.abc import Callable

import pytest

from orgmetra_product_composition.activation import (
    ActivationRegistryError,
    DeploymentIdentity,
    PostgresActivationRegistry,
)


def _drifted_registry() -> tuple[PostgresActivationRegistry, object, Callable[[], int]]:
    def admitted_factory() -> None:
        raise AssertionError("admitted factory is not reached after detected drift")

    replacement_calls = 0

    def replacement_factory() -> None:
        nonlocal replacement_calls
        replacement_calls += 1
        raise AssertionError("unadmitted structural connection factory executed")

    def calls() -> int:
        return replacement_calls

    registry = PostgresActivationRegistry(admitted_factory)  # type: ignore[arg-type]
    expected_factory = registry.connection_factory
    object.__setattr__(registry, "connection_factory", replacement_factory)
    return registry, expected_factory, calls


def _deployment() -> DeploymentIdentity:
    return DeploymentIdentity(
        deployment_id="orgmetra_gateway",
        environment_id="production",
    )


def test_authorized_transition_rejects_factory_drift_before_replacement_executes() -> None:
    """Authorized transition must use only the caller-pinned durable factory."""

    registry, expected_factory, replacement_calls = _drifted_registry()

    with pytest.raises(ActivationRegistryError, match="expected PostgreSQL connection factory"):
        registry.activate_authorized(
            _deployment(),
            generation_id="generation_one",
            expected_previous_sequence=0,
            evidence_bundle_sha256="a" * 64,
            evidence_writer=lambda _cursor: None,
            _connection_factory=expected_factory,  # type: ignore[arg-type]
        )

    assert replacement_calls() == 0


def test_recovery_read_rejects_factory_drift_before_replacement_executes() -> None:
    """Recovery snapshot must use only the caller-pinned durable factory."""

    registry, expected_factory, replacement_calls = _drifted_registry()

    with pytest.raises(ActivationRegistryError, match="expected PostgreSQL connection factory"):
        registry.recover_active(
            _deployment(),
            _connection_factory=expected_factory,  # type: ignore[arg-type]
        )

    assert replacement_calls() == 0


def test_authorized_recovery_rejects_factory_drift_before_replacement_executes() -> None:
    """Recovery attestation commit must use only the caller-pinned durable factory."""

    registry, expected_factory, replacement_calls = _drifted_registry()

    with pytest.raises(ActivationRegistryError, match="expected PostgreSQL connection factory"):
        registry.recover_active_authorized(
            _deployment(),
            expected_activation_sequence=1,
            expected_generation_id="generation_one",
            evidence_bundle_sha256="a" * 64,
            evidence_writer=lambda _cursor: None,
            _connection_factory=expected_factory,  # type: ignore[arg-type]
        )

    assert replacement_calls() == 0
