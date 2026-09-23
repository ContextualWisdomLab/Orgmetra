"""Issue route-availability snapshots only after durable recovery re-admission succeeds.

The snapshot is linearized at the successful recovery-attestation commit performed by
``AuthorizedPostgresActivationRegistry.recover_active``. It is therefore stronger than the
internal evidence-only route projection: the returned generation and evidence were rechecked
against the deployment's then-current durable activation state under the deployment row lock.

A snapshot is not perpetual dispatch authority. A serving adapter must discard it when its
activation sequence is superseded, when a newer recovery attestation supersedes its evidence,
when its exact durable recovery attestation disappears, or after the embedded evidence expires.
"""

from __future__ import annotations

from threading import RLock
from typing import cast
from weakref import WeakValueDictionary, finalize

from .activation import (
    ActivationConflictError,
    ActivationEvent,
    ActivationRegistryError,
    DeploymentIdentity,
)
from .activation_authorization import (
    ActivationAdmissionEvidence,
    ActivationAuthorizationError,
    AuthorizedRecoveredActivation,
)
from .activation_runtime_integrity import (
    AuthorizedPostgresActivationRegistry,
    _require_pinned_connection_factory,
)
from .admission import CompositionGeneration, _revalidate_generation_snapshot


_SELECT_CURRENT_SERVING_STATE_SQL = """
WITH current_activation AS (
    SELECT
        deployment_id,
        environment_id,
        activation_sequence,
        generation_id,
        previous_generation_id,
        event_kind,
        evidence_bundle_sha256
    FROM public.product_composition_activation_event
    WHERE deployment_id = %s AND environment_id = %s
    ORDER BY activation_sequence DESC
    LIMIT 1
),
serving_clock AS MATERIALIZED (
    SELECT clock_timestamp() AS observed_at
)
SELECT
    current_activation.activation_sequence,
    current_activation.generation_id,
    current_activation.previous_generation_id,
    current_activation.event_kind,
    current_activation.evidence_bundle_sha256,
    recovery_attestation.recovery_sequence,
    recovery_attestation.evidence_bundle_sha256 AS recovery_evidence_bundle_sha256,
    (
        SELECT MAX(latest_recovery.recovery_sequence)
        FROM public.product_composition_recovery_attestation AS latest_recovery
        WHERE latest_recovery.deployment_id = current_activation.deployment_id
          AND latest_recovery.environment_id = current_activation.environment_id
    ) AS latest_recovery_sequence,
    floor(extract(epoch FROM recovery_attestation.recovered_at) * 1000)::bigint AS recovered_at_unix_ms,
    floor(extract(epoch FROM serving_clock.observed_at) * 1000)::bigint AS observed_at_unix_ms,
    serving_clock.observed_at < recovery_attestation.recovered_at AS recovery_clock_rewound
FROM current_activation
CROSS JOIN serving_clock
LEFT JOIN public.product_composition_recovery_attestation AS recovery_attestation
  ON recovery_attestation.deployment_id = current_activation.deployment_id
 AND recovery_attestation.environment_id = current_activation.environment_id
 AND recovery_attestation.recovery_sequence = %s
 AND recovery_attestation.activation_sequence = current_activation.activation_sequence
 AND recovery_attestation.generation_id = current_activation.generation_id
 AND recovery_attestation.evidence_bundle_sha256 = %s
""".strip()


class RecoveredRouteSnapshot:
    """One recovery-commit-bound route projection for the then-current activation state."""

    __slots__ = (
        "_event",
        "_generation",
        "_evidence",
        "_recovery_sequence",
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
    def recovery_sequence(self) -> int:
        """Return the exact durable recovery attestation sequence that issued this snapshot."""

        _require_route_snapshot_integrity(self)
        return cast(int, object.__getattribute__(self, "_recovery_sequence"))

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
        recovery_sequence = object.__getattribute__(snapshot, "_recovery_sequence")
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
    if type(recovery_sequence) is not int or recovery_sequence <= 0:
        raise ActivationAuthorizationError(
            "route snapshot requires a durable recovery sequence > 0"
        )
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
        sorted(
            route.route_id
            for route in generation.routes
            if route.required or route.route_id in observed_route_ids
        )
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
        recovery_sequence,
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

    if type(recovered.recovery_sequence) is not int or recovered.recovery_sequence <= 0:
        raise ActivationAuthorizationError(
            "route snapshot requires the committed recovery attestation sequence"
        )
    observed_route_ids = {
        observation.route_id for observation in recovered.evidence.owner_operations
    }
    available_route_ids = tuple(
        sorted(
            route.route_id
            for route in recovered.generation.routes
            if route.required or route.route_id in observed_route_ids
        )
    )
    snapshot = cast(RecoveredRouteSnapshot, object.__new__(RecoveredRouteSnapshot))
    object.__setattr__(snapshot, "_event", recovered.event)
    object.__setattr__(snapshot, "_generation", recovered.generation)
    object.__setattr__(snapshot, "_evidence", recovered.evidence)
    object.__setattr__(snapshot, "_recovery_sequence", recovered.recovery_sequence)
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


def current_route_ids_for_snapshot(
    registry: AuthorizedPostgresActivationRegistry,
    deployment: DeploymentIdentity,
    snapshot: RecoveredRouteSnapshot,
) -> tuple[str, ...]:
    """Return routes only if snapshot state, latest attestation and freshness survive one DB read.

    The database statement is the routing-decision linearization point. It rechecks the current
    activation, the exact recovery sequence that issued the snapshot, and whether that sequence
    remains the deployment's latest recovery attestation, while using PostgreSQL wall clock as
    freshness authority. A later activation or recovery may supersede this decision after the
    read, so callers must invoke this at the request-routing boundary rather than treating a
    successful result as a perpetual cache grant.
    """

    if type(registry) is not AuthorizedPostgresActivationRegistry:
        raise ActivationAuthorizationError(
            "serving currentness requires exact AuthorizedPostgresActivationRegistry"
        )
    if type(deployment) is not DeploymentIdentity:
        raise ActivationAuthorizationError("serving currentness requires exact DeploymentIdentity")
    try:
        DeploymentIdentity.__post_init__(deployment)
    except ActivationRegistryError as exc:
        raise ActivationAuthorizationError(
            "serving deployment no longer matches its construction snapshot"
        ) from exc
    deployment_id = deployment.deployment_id
    environment_id = deployment.environment_id
    if type(snapshot) is not RecoveredRouteSnapshot:
        raise ActivationAuthorizationError("serving currentness requires exact RecoveredRouteSnapshot")

    _require_route_snapshot_integrity(snapshot)
    issued_event = snapshot.event
    recovery_sequence = snapshot.recovery_sequence
    evidence = snapshot.evidence
    recovery_evidence_bundle_sha256 = evidence.bundle_sha256()
    recovery_valid_until_unix_ms = evidence.valid_until_unix_ms
    if (
        issued_event.deployment.deployment_id != deployment_id
        or issued_event.deployment.environment_id != environment_id
    ):
        raise ActivationAuthorizationError(
            "serving deployment does not match the recovered route snapshot deployment"
        )

    structural_registry = registry._structural_registry
    connection_factory = structural_registry.connection_factory
    registry._require_runtime_capabilities()
    _require_pinned_connection_factory(structural_registry, connection_factory)
    with connection_factory() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                _SELECT_CURRENT_SERVING_STATE_SQL,
                (
                    deployment_id,
                    environment_id,
                    recovery_sequence,
                    recovery_evidence_bundle_sha256,
                ),
            )
            row = cursor.fetchone()

    # This is a read-only use boundary, so post-I/O integrity checks may fail closed without
    # turning a committed write into an ambiguous failure.
    registry._require_runtime_capabilities()
    _require_pinned_connection_factory(structural_registry, connection_factory)
    try:
        DeploymentIdentity.__post_init__(deployment)
    except ActivationRegistryError as exc:
        raise ActivationAuthorizationError(
            "serving deployment changed across database use"
        ) from exc
    if deployment.deployment_id != deployment_id or deployment.environment_id != environment_id:
        raise ActivationAuthorizationError("serving deployment changed across database use")
    _require_route_snapshot_integrity(snapshot)
    issued_event = snapshot.event
    evidence = snapshot.evidence
    if (
        snapshot.recovery_sequence != recovery_sequence
        or evidence.bundle_sha256() != recovery_evidence_bundle_sha256
        or evidence.valid_until_unix_ms != recovery_valid_until_unix_ms
    ):
        raise ActivationAuthorizationError("route snapshot recovery authority changed across database use")

    if row is None:
        raise ActivationConflictError("route snapshot was superseded by missing durable activation state")
    if type(row) is not tuple or len(row) != 11:
        raise ActivationAuthorizationError("serving state query returned invalid durable shape")
    (
        activation_sequence,
        generation_id,
        previous_generation_id,
        event_kind,
        evidence_bundle_sha256,
        durable_recovery_sequence,
        durable_recovery_evidence_sha256,
        latest_recovery_sequence,
        recovered_at_unix_ms,
        observed_at_unix_ms,
        recovery_clock_rewound,
    ) = row
    if type(activation_sequence) is not int or activation_sequence <= 0:
        raise ActivationAuthorizationError("serving state returned invalid activation sequence")
    if type(generation_id) is not str:
        raise ActivationAuthorizationError("serving state returned invalid generation id")
    if previous_generation_id is not None and type(previous_generation_id) is not str:
        raise ActivationAuthorizationError("serving state returned invalid previous generation id")
    if type(event_kind) is not str:
        raise ActivationAuthorizationError("serving state returned invalid event kind")
    if evidence_bundle_sha256 is not None and type(evidence_bundle_sha256) is not str:
        raise ActivationAuthorizationError("serving state returned invalid evidence digest")
    if (
        durable_recovery_sequence is None
        and durable_recovery_evidence_sha256 is None
        and recovered_at_unix_ms is None
    ):
        raise ActivationConflictError("route snapshot durable recovery attestation is missing")
    if type(durable_recovery_sequence) is not int or durable_recovery_sequence <= 0:
        raise ActivationAuthorizationError("serving state returned invalid recovery sequence")
    if type(durable_recovery_evidence_sha256) is not str:
        raise ActivationAuthorizationError("serving state returned invalid recovery evidence digest")
    if type(latest_recovery_sequence) is not int or latest_recovery_sequence <= 0:
        raise ActivationAuthorizationError("serving state returned invalid latest recovery sequence")
    if type(recovered_at_unix_ms) is not int or recovered_at_unix_ms <= 0:
        raise ActivationAuthorizationError("serving state returned invalid recovery timestamp")
    if type(observed_at_unix_ms) is not int or observed_at_unix_ms <= 0:
        raise ActivationAuthorizationError("serving state returned invalid database wall clock")
    if type(recovery_clock_rewound) is not bool:
        raise ActivationAuthorizationError("serving state returned invalid recovery clock ordering")

    current_fields = (
        activation_sequence,
        generation_id,
        previous_generation_id,
        event_kind,
        evidence_bundle_sha256,
    )
    issued_fields = (
        issued_event.activation_sequence,
        issued_event.generation_id,
        issued_event.previous_generation_id,
        issued_event.event_kind,
        issued_event.evidence_bundle_sha256,
    )
    if current_fields != issued_fields:
        raise ActivationConflictError("route snapshot was superseded by durable activation state")
    if durable_recovery_sequence != recovery_sequence:
        raise ActivationConflictError(
            "route snapshot durable recovery attestation no longer matches issued recovery sequence"
        )
    if durable_recovery_evidence_sha256 != recovery_evidence_bundle_sha256:
        raise ActivationConflictError(
            "route snapshot durable recovery attestation no longer matches issued recovery evidence"
        )
    if latest_recovery_sequence != recovery_sequence:
        raise ActivationConflictError(
            "route snapshot was superseded by newer recovery attestation"
        )
    if recovery_clock_rewound or observed_at_unix_ms < recovered_at_unix_ms:
        raise ActivationAuthorizationError(
            "database wall clock moved behind recovery attestation"
        )
    if observed_at_unix_ms >= recovery_valid_until_unix_ms:
        raise ActivationAuthorizationError(
            "route snapshot recovery evidence expired before the serving decision"
        )

    return snapshot.available_route_ids