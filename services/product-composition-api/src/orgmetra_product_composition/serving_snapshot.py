"""Issue route-availability snapshots only after durable recovery re-admission succeeds.

The snapshot is linearized at the successful recovery-attestation commit performed by
``AuthorizedPostgresActivationRegistry.recover_active``. It is therefore stronger than the
internal evidence-only route projection: the returned generation and evidence were rechecked
against the deployment's then-current durable activation state under the deployment row lock.

A snapshot is not perpetual dispatch authority. A serving adapter must discard it when its
activation sequence is superseded and must not use it after the embedded evidence expires.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from .activation import ActivationEvent, DeploymentIdentity
from .activation_authorization import (
    ActivationAdmissionEvidence,
    ActivationAuthorizationError,
    AuthorizedRecoveredActivation,
)
from .activation_runtime_integrity import AuthorizedPostgresActivationRegistry
from .admission import CompositionGeneration


@dataclass(frozen=True, slots=True, init=False)
class RecoveredRouteSnapshot:
    """One recovery-commit-bound route projection for the then-current activation state."""

    event: ActivationEvent
    generation: CompositionGeneration
    evidence: ActivationAdmissionEvidence
    available_route_ids: tuple[str, ...]

    def __new__(cls, *args: object, **kwargs: object) -> "RecoveredRouteSnapshot":
        """Prevent callers from forging a value that looks like issued recovery authority."""

        raise ActivationAuthorizationError(
            "RecoveredRouteSnapshot is issued only by recover_active_route_snapshot"
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
    object.__setattr__(snapshot, "event", recovered.event)
    object.__setattr__(snapshot, "generation", recovered.generation)
    object.__setattr__(snapshot, "evidence", recovered.evidence)
    object.__setattr__(snapshot, "available_route_ids", available_route_ids)
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

    if not isinstance(registry, AuthorizedPostgresActivationRegistry):
        raise ActivationAuthorizationError(
            "route snapshot requires AuthorizedPostgresActivationRegistry"
        )
    recovered = registry.recover_active(deployment)
    if recovered is None:
        return None
    if type(recovered) is not AuthorizedRecoveredActivation:
        raise ActivationAuthorizationError(
            "route snapshot recovery must return exact AuthorizedRecoveredActivation"
        )
    return _issue_route_snapshot(recovered)
