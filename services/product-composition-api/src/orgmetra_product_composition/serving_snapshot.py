"""Issue route-availability snapshots only after durable recovery re-admission succeeds.

The snapshot is linearized at the successful recovery-attestation commit performed by
``AuthorizedPostgresActivationRegistry.recover_active``. It is therefore stronger than the
internal evidence-only route projection: the returned generation and evidence were rechecked
against the deployment's then-current durable activation state under the deployment row lock.

A snapshot is not perpetual dispatch authority. A serving adapter must discard it when its
activation sequence is superseded and must not use it after the embedded evidence expires.
"""

from __future__ import annotations

from threading import RLock
from typing import cast
from weakref import WeakValueDictionary, finalize

from .activation import ActivationEvent, ActivationRegistryError, DeploymentIdentity
from .activation_authorization import (
    ActivationAdmissionEvidence,
    ActivationAuthorizationError,
    AuthorizedRecoveredActivation,
)
from .activation_runtime_integrity import AuthorizedPostgresActivationRegistry
from .admission import CompositionGeneration, _revalidate_generation_snapshot


class RecoveredRouteSnapshot:
    """One recovery-commit-bound route projection for the then-current activation state."""

    __slots__ = (
        "_event",
        "_generation",
        "_evidence",
        "_available_route_ids",
        "__weakref__",
    )

    def __new__(cls, *args: object, **kwargs: object) -> "RecoveredRouteSnapshot":
        """Prevent callers from forging a value that looks like issued recovery authority."""

        raise ActivationAuthorizationError(
            "RecoveredRouteSnapshot is issued only by recover_active_route_snapshot"
        )

    @property
    def event(self) -> ActivationEvent:
        """Return the activation event after rechecking snapshot construction integrity."""

        _require_route_snapshot_integrity(self)
        return cast(ActivationEvent, object.__getattribute__(self, "_event"))

    @property
    def generation(self) -> CompositionGeneration:
        """Return the recovered generation after rechecking snapshot construction integrity."""

        _require_route_snapshot_integrity(self)
        return cast(CompositionGeneration, object.__getattribute__(self, "_generation"))

    @property
    def evidence(self) -> ActivationAdmissionEvidence:
        """Return committed recovery evidence after rechecking snapshot construction integrity."""

        _require_route_snapshot_integrity(self)
        return cast(ActivationAdmissionEvidence, object.__getattribute__(self, "_evidence"))

    @property
    def available_route_ids(self) -> tuple[str, ...]:
        """Return the routes serviceable at snapshot issuance after integrity revalidation."""

        _require_route_snapshot_integrity(self)
        return cast(tuple[str, ...], object.__getattribute__(self, "_available_route_ids"))


def _project_route_snapshot(snapshot: RecoveredRouteSnapshot) -> tuple[object, ...]:
    """Project nested authority and route coverage without trusting public properties."""

    try:
        event = object.__getattribute__(snapshot, "_event")
        generation = object.__getattribute__(snapshot, "_generation")
        evidence = object.__getattribute__(snapshot, "_evidence")
        available_route_ids = object.__getattribute__(snapshot, "_available_route_ids")
    except AttributeError as exc:
        raise ActivationAuthorizationError(
            "RecoveredRouteSnapshot is not a canonically issued value"
        ) from exc

    if type(event) is not ActivationEvent:
        raise ActivationAuthorizationError("route snapshot requires exact ActivationEvent")
    ActivationEvent.__post_init__(event)
    try:
        DeploymentIdentity.__post_init__(event.deployment)
    except ActivationRegistryError as exc:
        raise ActivationAuthorizationError(
            "route snapshot DeploymentIdentity no longer matches its construction snapshot"
        ) from exc
    if type(generation) is not CompositionGeneration:
        raise ActivationAuthorizationError("route snapshot requires exact CompositionGeneration")
    _revalidate_generation_snapshot(generation)
    if type(evidence) is not ActivationAdmissionEvidence:
        raise ActivationAuthorizationError(
            "route snapshot requires exact ActivationAdmissionEvidence"
        )
    ActivationAdmissionEvidence.__post_init__(evidence)
    if type(available_route_ids) is not tuple or any(
        type(route_id) is not str for route_id in available_route_ids
    ):
        raise ActivationAuthorizationError("route snapshot route ids must be an exact tuple of str")

    if (
        evidence.deployment_id != event.deployment.deployment_id
        or evidence.environment_id != event.deployment.environment_id
    ):
        raise ActivationAuthorizationError(
            "route snapshot event and evidence must agree on deployment identity"
        )
    if event.generation_id != generation.generation_id:
        raise ActivationAuthorizationError("route snapshot event and generation must agree")
    if (
        evidence.generation_id != generation.generation_id
        or evidence.config_sha256 != generation.config_sha256
    ):
        raise ActivationAuthorizationError("route snapshot evidence and generation must agree")
    if evidence.authorization_action != "recover":
        raise ActivationAuthorizationError("route snapshot requires recovery authorization evidence")
    if evidence.authorized_state_sequence != event.activation_sequence:
        raise ActivationAuthorizationError("route snapshot evidence must bind the activation sequence")
    if event.evidence_bundle_sha256 is None:
        raise ActivationAuthorizationError("route snapshot requires authorized durable activation")

    observed_route_ids = {observation.route_id for observation in evidence.owner_operations}
    expected_route_ids = tuple(
        route.route_id
        for route in generation.routes
        if route.required or route.route_id in observed_route_ids
    )
    if available_route_ids != expected_route_ids:
        raise ActivationAuthorizationError(
            "RecoveredRouteSnapshot no longer matches its issued route coverage"
        )

    return (
        id(event),
        id(event.deployment),
        event.deployment.deployment_id,
        event.deployment.environment_id,
        event.activation_sequence,
        event.generation_id,
        event.previous_generation_id,
        event.event_kind,
        event.evidence_bundle_sha256,
        id(generation),
        generation.generation_id,
        generation.config_sha256,
        id(evidence),
        evidence.bundle_sha256(),
        available_route_ids,
    )


def _build_route_snapshot_integrity_runtime():
    """Track issued snapshots without extending their lifetime or accepting first-use forgery."""

    issued_snapshots: WeakValueDictionary[int, RecoveredRouteSnapshot] = WeakValueDictionary()
    issued_fields: dict[int, tuple[object, ...]] = {}
    state_lock = RLock()

    def discard(snapshot_object_id: int) -> None:
        """Discard construction evidence when the issued snapshot becomes unreachable."""

        with state_lock:
            issued_fields.pop(snapshot_object_id, None)

    def record(snapshot: RecoveredRouteSnapshot) -> None:
        """Record one module-issued snapshot after validating all nested authority bindings."""

        snapshot_object_id = id(snapshot)
        current_fields = _project_route_snapshot(snapshot)
        with state_lock:
            if issued_snapshots.get(snapshot_object_id) is not None:
                raise ActivationAuthorizationError("route snapshot was already issued")
            issued_snapshots[snapshot_object_id] = snapshot
            issued_fields[snapshot_object_id] = current_fields
            finalize(snapshot, discard, snapshot_object_id)

    def require(snapshot: RecoveredRouteSnapshot) -> None:
        """Reject forged, retargeted, or nested-mutated route snapshots before use."""

        snapshot_object_id = id(snapshot)
        current_fields = _project_route_snapshot(snapshot)
        with state_lock:
            if (
                issued_snapshots.get(snapshot_object_id) is not snapshot
                or issued_fields.get(snapshot_object_id) != current_fields
            ):
                raise ActivationAuthorizationError(
                    "RecoveredRouteSnapshot no longer matches its issuance snapshot"
                )

    return record, require


_record_route_snapshot_integrity, _require_route_snapshot_integrity = (
    _build_route_snapshot_integrity_runtime()
)


def _issue_route_snapshot(recovered: AuthorizedRecoveredActivation) -> RecoveredRouteSnapshot:
    """Project whole-route coverage from evidence already validated and committed by recovery."""

    observed_route_ids = {
        observation.route_id for observation in recovered.evidence.owner_operations
    }
    available_route_ids = tuple(
        route.route_id
        for route in recovered.generation.routes
        if route.required or route.route_id in observed_route_ids
    )
    snapshot = cast(RecoveredRouteSnapshot, object.__new__(RecoveredRouteSnapshot))
    object.__setattr__(snapshot, "_event", recovered.event)
    object.__setattr__(snapshot, "_generation", recovered.generation)
    object.__setattr__(snapshot, "_evidence", recovered.evidence)
    object.__setattr__(snapshot, "_available_route_ids", available_route_ids)
    _record_route_snapshot_integrity(snapshot)
    return snapshot


def recover_active_route_snapshot(
    registry: AuthorizedPostgresActivationRegistry,
    deployment: DeploymentIdentity,
) -> RecoveredRouteSnapshot | None:
    """Re-admit current durable activation, then issue its post-commit route projection.

    The function deliberately performs no new clock read or fallible freshness decision after
    ``recover_active`` returns: PostgreSQL has already validated and committed the recovery
    evidence under the deployment lock. This preserves the existing rule that a successful
    durable attestation is never reclassified locally as a failure after commit.
    """

    if type(registry) is not AuthorizedPostgresActivationRegistry:
        raise ActivationAuthorizationError(
            "route snapshot requires exact AuthorizedPostgresActivationRegistry"
        )
    recovered = registry.recover_active(deployment)
    if recovered is None:
        return None
    if type(recovered) is not AuthorizedRecoveredActivation:
        raise ActivationAuthorizationError(
            "route snapshot recovery must return exact AuthorizedRecoveredActivation"
        )
    return _issue_route_snapshot(recovered)
