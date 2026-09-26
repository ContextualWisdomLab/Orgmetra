"""Project whole-route coverage from one validated activation-evidence value.

Declared generation routes describe intended composition. This internal helper is narrower: it
reuses the complete activation-evidence validation boundary, then reports required routes and
optional routes whose full owner-operation evidence is present. The route-id projection is sorted
lexically so semantically identical generations cannot produce different availability tuples only
because their input route tuples use a different order. It does not read PostgreSQL and therefore
does not prove that the supplied generation/evidence still represents the deployment's current
active state. A serving adapter must bind dispatch to a current durable activation snapshot before
using this projection; until that state-bound adapter exists, this helper is not part of the package
product public API.
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
    """Return canonical whole-route coverage, not current dispatch authority."""

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
        sorted(
            route.route_id
            for route in generation.routes
            if route.required or route.route_id in observed_route_ids
        )
    )
