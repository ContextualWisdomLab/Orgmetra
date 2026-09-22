"""Bind activation authorization to the runtime capabilities admitted at construction.

The external evidence provider runs outside the deployment row lock by design. It must not
be able to retarget or weaken the clock or PostgreSQL adapters that are used after that
callback. This module keeps the product-facing wrapper's executable capabilities under a
process-local construction snapshot while leaving the structural registry internal.
"""

from __future__ import annotations

from threading import RLock
from weakref import ReferenceType, WeakValueDictionary, finalize, ref

from .activation import DeploymentIdentity, PostgresActivationRegistry
from .activation_authorization import (
    ActivationAdmissionEvidence,
    ActivationAuthorizationError,
    AuthorizationAction,
    AuthorizedPostgresActivationRegistry as _AuthorizedPostgresActivationRegistry,
    AuthorizedRecoveredActivation,
    _authorization_action,
    _state_sequence,
)
from .admission import CompositionGeneration, _revalidate_generation_snapshot
from .postgres_registry import PostgresGenerationRegistry


def _build_runtime_capability_construction_guard():
    """Build the process-local identity guard without retaining capability lifetimes."""

    constructed_registries: WeakValueDictionary[int, object] = WeakValueDictionary()
    # Weak references are identity witnesses without process-lifetime roots. If an
    # admitted capability is replaced and collected, the dead reference can never be
    # satisfied by a later object that happens to reuse the same CPython address.
    constructed_capabilities: dict[int, tuple[ReferenceType[object], ...]] = {}
    state_lock = RLock()

    def discard(registry_object_id: int) -> None:
        """Discard identity witnesses when their registry becomes unreachable."""

        with state_lock:
            constructed_capabilities.pop(registry_object_id, None)

    def capability_reference(label: str, capability: object) -> ReferenceType[object]:
        """Return a non-rooting identity witness or fail closed for unsupported callables."""

        try:
            return ref(capability)
        except TypeError as exc:
            raise TypeError(
                f"{label} must support weak-reference identity for runtime integrity"
            ) from exc

    def project(registry: AuthorizedPostgresActivationRegistry) -> tuple[object, ...]:
        """Project caller-supplied capabilities after validating internal adapter topology."""

        if type(registry._generation_registry) is not PostgresGenerationRegistry:
            raise ActivationAuthorizationError(
                "generation registry no longer matches the admitted PostgreSQL adapter type"
            )
        if type(registry._structural_registry) is not PostgresActivationRegistry:
            raise ActivationAuthorizationError(
                "structural registry no longer matches the admitted PostgreSQL adapter type"
            )
        if registry._generation_registry.connection_factory is not registry.connection_factory:
            raise ActivationAuthorizationError(
                "generation registry no longer uses the admitted PostgreSQL connection factory"
            )
        if registry._structural_registry.connection_factory is not registry.connection_factory:
            raise ActivationAuthorizationError(
                "structural registry no longer uses the admitted PostgreSQL connection factory"
            )
        return (
            registry.connection_factory,
            registry.evidence_provider,
            registry.clock_unix_ms,
        )

    def record_or_require(registry: AuthorizedPostgresActivationRegistry) -> None:
        """Record first-use capability identity or reject any later construction drift."""

        registry_object_id = id(registry)
        current_capabilities = project(registry)
        with state_lock:
            canonical_registry = constructed_registries.get(registry_object_id)
            canonical_capabilities = constructed_capabilities.get(registry_object_id)
            if canonical_registry is None and canonical_capabilities is None:
                constructed_registries[registry_object_id] = registry
                constructed_capabilities[registry_object_id] = tuple(
                    capability_reference(label, capability)
                    for label, capability in zip(
                        ("connection_factory", "evidence_provider", "clock_unix_ms"),
                        current_capabilities,
                        strict=True,
                    )
                )
                finalize(registry, discard, registry_object_id)
                return
            capabilities_match = (
                canonical_capabilities is not None
                and len(canonical_capabilities) == len(current_capabilities)
                and all(
                    canonical_reference() is current
                    for canonical_reference, current in zip(
                        canonical_capabilities,
                        current_capabilities,
                        strict=True,
                    )
                )
            )
            if canonical_registry is not registry or not capabilities_match:
                raise ActivationAuthorizationError(
                    "AuthorizedPostgresActivationRegistry no longer matches its construction snapshot"
                )

    return record_or_require


_record_or_require_runtime_capabilities = _build_runtime_capability_construction_guard()


class AuthorizedPostgresActivationRegistry(_AuthorizedPostgresActivationRegistry):
    """Product-facing activation registry with checked-as-used executable capabilities."""

    __slots__ = ("__weakref__",)

    def __post_init__(self) -> None:
        """Validate base construction and admit the executable capability identity once."""

        super().__post_init__()
        _record_or_require_runtime_capabilities(self)

    def _require_runtime_capabilities(self) -> None:
        """Reject any post-construction executable capability or adapter retargeting."""

        _record_or_require_runtime_capabilities(self)

    def _load_target(self, generation_id: str) -> CompositionGeneration:
        """Load one generation only through the admitted PostgreSQL capability topology."""

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
        """Validate evidence against the same non-rewinding clock admitted at construction."""

        self._require_runtime_capabilities()
        if type(deployment) is not DeploymentIdentity:
            raise ActivationAuthorizationError("deployment must be exact DeploymentIdentity")
        DeploymentIdentity.__post_init__(deployment)
        _revalidate_generation_snapshot(generation)
        action = _authorization_action(authorization_action)
        state_sequence = _state_sequence(authorized_state_sequence)

        provider = self.evidence_provider
        clock = self.clock_unix_ms
        before_provider_unix_ms = clock()
        self._require_runtime_capabilities()
        if type(before_provider_unix_ms) is not int or before_provider_unix_ms <= 0:
            raise ActivationAuthorizationError("clock_unix_ms must return an integer > 0")

        evidence = provider(deployment, generation, action, state_sequence)
        self._require_runtime_capabilities()
        if type(evidence) is not ActivationAdmissionEvidence:
            raise ActivationAuthorizationError(
                "evidence_provider must return exact ActivationAdmissionEvidence"
            )

        now_unix_ms = clock()
        self._require_runtime_capabilities()
        if type(now_unix_ms) is not int or now_unix_ms <= 0:
            raise ActivationAuthorizationError("clock_unix_ms must return an integer > 0")
        if now_unix_ms < before_provider_unix_ms:
            raise ActivationAuthorizationError(
                "clock_unix_ms moved backwards across external evidence acquisition"
            )
        evidence.validate_for(
            deployment_id=deployment.deployment_id,
            environment_id=deployment.environment_id,
            generation=generation,
            authorization_action=action,
            authorized_state_sequence=state_sequence,
            now_unix_ms=now_unix_ms,
        )
        return evidence

    def recover_active(
        self,
        deployment: DeploymentIdentity,
    ) -> AuthorizedRecoveredActivation | None:
        """Persist recovery without a fallible local freshness decision after commit.

        Freshness is checked before the durable write and independently by PostgreSQL at
        evidence/attestation insertion. Once the locked transaction commits, a later local wall
        clock sample must not turn a successful recovery attestation into an ambiguous failure.
        """

        structural_registry = self._structural_registry
        self._require_runtime_capabilities()
        first = structural_registry.recover_active(deployment)
        self._require_runtime_capabilities()
        if first is None:
            return None
        if first.event.evidence_bundle_sha256 is None:
            raise ActivationAuthorizationError(
                "authorized recovery requires durable authorization evidence"
            )

        evidence = self._obtain_evidence(
            deployment,
            first.generation,
            authorization_action="recover",
            authorized_state_sequence=first.event.activation_sequence,
        )

        structural_registry = self._structural_registry
        self._require_runtime_capabilities()
        second = structural_registry.recover_active_authorized(
            deployment,
            expected_activation_sequence=first.event.activation_sequence,
            expected_generation_id=first.generation.generation_id,
            evidence_bundle_sha256=evidence.bundle_sha256(),
            evidence_writer=self._evidence_writer(evidence),
        )

        # Do not add a fallible capability/freshness recheck here. The structural call above
        # commits the durable attestation before returning; PostgreSQL is the commit-time clock
        # authority, and a post-commit exception would make the caller observe false failure.
        return AuthorizedRecoveredActivation(
            event=second.event,
            generation=second.generation,
            evidence=evidence,
        )
