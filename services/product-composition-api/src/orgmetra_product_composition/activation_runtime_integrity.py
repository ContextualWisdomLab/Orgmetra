"""Bind activation authorization to the runtime capabilities admitted at construction.

The external evidence provider runs outside the deployment row lock by design. It must not
be able to retarget the clock or PostgreSQL adapters that are used after that callback.
This module keeps the product-facing wrapper's executable capabilities under a process-local
construction snapshot while leaving the structural registry internal.
"""

from __future__ import annotations

from threading import RLock
from typing import Any
from weakref import WeakValueDictionary, finalize

from .activation import DeploymentIdentity
from .activation_authorization import (
    ActivationAdmissionEvidence,
    ActivationAuthorizationError,
    AuthorizationAction,
    AuthorizedPostgresActivationRegistry as _AuthorizedPostgresActivationRegistry,
    _authorization_action,
    _state_sequence,
)
from .admission import CompositionGeneration, _revalidate_generation_snapshot


def _build_runtime_capability_construction_guard():
    constructed_registries: WeakValueDictionary[int, object] = WeakValueDictionary()
    constructed_capabilities: dict[int, tuple[int, ...]] = {}
    state_lock = RLock()

    def discard(registry_object_id: int) -> None:
        with state_lock:
            constructed_capabilities.pop(registry_object_id, None)

    def project(registry: AuthorizedPostgresActivationRegistry) -> tuple[int, ...]:
        return (
            id(registry.connection_factory),
            id(registry.evidence_provider),
            id(registry.clock_unix_ms),
            id(registry._generation_registry),
            id(registry._generation_registry.connection_factory),
            id(registry._structural_registry),
            id(registry._structural_registry.connection_factory),
        )

    def record_or_require(registry: AuthorizedPostgresActivationRegistry) -> None:
        registry_object_id = id(registry)
        current_capabilities = project(registry)
        with state_lock:
            canonical_registry = constructed_registries.get(registry_object_id)
            canonical_capabilities = constructed_capabilities.get(registry_object_id)
            if canonical_registry is None and canonical_capabilities is None:
                constructed_registries[registry_object_id] = registry
                constructed_capabilities[registry_object_id] = current_capabilities
                finalize(registry, discard, registry_object_id)
                return
            if canonical_registry is not registry or canonical_capabilities != current_capabilities:
                raise ActivationAuthorizationError(
                    "AuthorizedPostgresActivationRegistry no longer matches its construction snapshot"
                )

    return record_or_require


_record_or_require_runtime_capabilities = _build_runtime_capability_construction_guard()


class AuthorizedPostgresActivationRegistry(_AuthorizedPostgresActivationRegistry):
    """Product-facing activation registry with checked-as-used executable capabilities."""

    __slots__ = ("__weakref__",)

    def __post_init__(self) -> None:
        super().__post_init__()
        _record_or_require_runtime_capabilities(self)

    def _require_runtime_capabilities(self) -> None:
        _record_or_require_runtime_capabilities(self)

    def _load_target(self, generation_id: str) -> CompositionGeneration:
        self._require_runtime_capabilities()
        return super()._load_target(generation_id)

    def _obtain_evidence(
        self,
        deployment: DeploymentIdentity,
        generation: CompositionGeneration,
        *,
        authorization_action: AuthorizationAction,
        authorized_state_sequence: int,
    ) -> ActivationAdmissionEvidence:
        """Validate evidence against the same provider and clock admitted at construction."""
        self._require_runtime_capabilities()
        if type(deployment) is not DeploymentIdentity:
            raise ActivationAuthorizationError("deployment must be exact DeploymentIdentity")
        DeploymentIdentity.__post_init__(deployment)
        _revalidate_generation_snapshot(generation)
        action = _authorization_action(authorization_action)
        state_sequence = _state_sequence(authorized_state_sequence)

        provider = self.evidence_provider
        clock = self.clock_unix_ms
        evidence = provider(deployment, generation, action, state_sequence)
        self._require_runtime_capabilities()
        if type(evidence) is not ActivationAdmissionEvidence:
            raise ActivationAuthorizationError(
                "evidence_provider must return exact ActivationAdmissionEvidence"
            )

        now_unix_ms = clock()
        self._require_runtime_capabilities()
        evidence.validate_for(
            deployment_id=deployment.deployment_id,
            environment_id=deployment.environment_id,
            generation=generation,
            authorization_action=action,
            authorized_state_sequence=state_sequence,
            now_unix_ms=now_unix_ms,
        )
        return evidence

    def recover_active(self, deployment: DeploymentIdentity) -> Any:
        """Reject capability retargeting before the first durable recovery read."""
        self._require_runtime_capabilities()
        return super().recover_active(deployment)
