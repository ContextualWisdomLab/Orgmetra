"""Project serviceable composition routes from current activation evidence.

Declared generation routes describe intended composition. This projection is deliberately
narrower: it first reuses the complete activation-evidence validation boundary, then exposes
only required routes and optional routes whose full owner-operation evidence is present.
A serving adapter can therefore avoid treating a declared-but-unobserved optional route as
callable while still preserving the immutable generation unchanged.
"""

from __future__ import annotations

from .activation_authorization import (
    ActivationAdmissionEvidence,
    ActivationAuthorizationError,
    AuthorizationAction,
)
from .admission import CompositionGeneration


def available_route_ids_for(
    evidence: ActivationAdmissionEvidence,
    *,
    deployment_id: str,
    environment_id: str,
    generation: CompositionGeneration,
    authorization_action: AuthorizationAction,
    authorized_state_sequence: int,
    now_unix_ms: int,
) -> tuple[str, ...]:
    """Return route IDs currently covered by valid whole-route activation evidence.

    This is a read-side serving projection, not a transition result. Validation failure means
    the caller must not use the projection for dispatch; it does not reinterpret an activation
    or recovery transaction that may already have committed.
    """

    if type(evidence) is not ActivationAdmissionEvidence:
        raise ActivationAuthorizationError(
            "route availability requires exact ActivationAdmissionEvidence"
        )
    evidence.validate_for(
        deployment_id=deployment_id,
        environment_id=environment_id,
        generation=generation,
        authorization_action=authorization_action,
        authorized_state_sequence=authorized_state_sequence,
        now_unix_ms=now_unix_ms,
    )
    observed_route_ids = {observation.route_id for observation in evidence.owner_operations}
    return tuple(
        route.route_id
        for route in generation.routes
        if route.required or route.route_id in observed_route_ids
    )
