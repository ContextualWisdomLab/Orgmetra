"""Append-only PostgreSQL activation authority for persisted composition generations.

Activation is a compare-and-append operation over an explicit non-PII deployment and
environment coordinate. The adapter serializes writers by locking the deployment row,
reconstructs the target generation from durable normalized material, and records a new
event. Rollback is the same append-only transition with the additional requirement that
the target generation was previously active on that deployment.
"""

from __future__ import annotations

import re
from contextlib import AbstractContextManager
from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable, Literal
from weakref import WeakValueDictionary, finalize

from .admission import CompositionGeneration
from .postgres_registry import PostgresGenerationRegistry
from .registry import CompositionRegistryError

PostgresConnectionFactory = Callable[[], AbstractContextManager[Any]]
TransactionEvidenceWriter = Callable[[Any], None]
EventKind = Literal["activate", "rollback"]
_CANONICAL_IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_INSERT_DEPLOYMENT_SQL = """
INSERT INTO public.product_composition_deployment (deployment_id, environment_id)
VALUES (%s, %s)
ON CONFLICT (deployment_id, environment_id) DO NOTHING
""".strip()

_LOCK_DEPLOYMENT_SQL = """
SELECT deployment_id, environment_id
FROM public.product_composition_deployment
WHERE deployment_id = %s AND environment_id = %s
FOR UPDATE
""".strip()

_SELECT_LATEST_EVENT_SQL = """
SELECT
    activation_sequence,
    generation_id,
    event_kind,
    previous_generation_id,
    evidence_bundle_sha256
FROM public.product_composition_activation_event
WHERE deployment_id = %s AND environment_id = %s
ORDER BY activation_sequence DESC
LIMIT 1
""".strip()

_SELECT_PRIOR_TARGET_SQL = """
SELECT 1
FROM public.product_composition_activation_event
WHERE deployment_id = %s
  AND environment_id = %s
  AND generation_id = %s
  AND activation_sequence <= %s
LIMIT 1
""".strip()

_SELECT_LATEST_RECOVERY_SEQUENCE_SQL = """
SELECT COALESCE(MAX(recovery_sequence), 0)
FROM public.product_composition_recovery_attestation
WHERE deployment_id = %s AND environment_id = %s
""".strip()

_INSERT_RECOVERY_ATTESTATION_SQL = """
INSERT INTO public.product_composition_recovery_attestation (
    deployment_id,
    environment_id,
    recovery_sequence,
    activation_sequence,
    generation_id,
    evidence_bundle_sha256
)
VALUES (%s, %s, %s, %s, %s, %s)
RETURNING recovery_sequence
""".strip()

_INSERT_EVENT_SQL = """
INSERT INTO public.product_composition_activation_event (
    deployment_id,
    environment_id,
    activation_sequence,
    generation_id,
    previous_generation_id,
    event_kind
)
VALUES (%s, %s, %s, %s, %s, %s)
RETURNING activation_sequence
""".strip()

_INSERT_AUTHORIZED_EVENT_SQL = """
INSERT INTO public.product_composition_activation_event (
    deployment_id,
    environment_id,
    activation_sequence,
    generation_id,
    previous_generation_id,
    event_kind,
    evidence_bundle_sha256
)
VALUES (%s, %s, %s, %s, %s, %s, %s)
RETURNING activation_sequence
""".strip()

_REPEATABLE_READ_ONLY_SQL = "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"


class ActivationRegistryError(CompositionRegistryError):
    """Raised when durable activation evidence is invalid or incomplete."""


class ActivationConflictError(ActivationRegistryError):
    """Raised when compare-and-append activation state has advanced or is a no-op."""


def _canonical_identifier(field_name: str, value: object) -> str:
    """Require the stable lower-snake identifier representation used in durable keys."""
    if type(value) is not str:
        raise ActivationRegistryError(f"{field_name} must be an exact built-in str")
    if not 1 <= len(value) <= 64 or _CANONICAL_IDENTIFIER.fullmatch(value) is None:
        raise ActivationRegistryError(
            f"{field_name} must be canonical 1..64-character lower snake_case"
        )
    return value


def _evidence_digest(value: object) -> str:
    """Require an exact lowercase SHA-256 digest before binding evidence to history."""
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise ActivationRegistryError(
            "evidence_bundle_sha256 must be a lowercase SHA-256 digest"
        )
    return value


def _expected_sequence(value: object) -> int:
    """Require a non-negative compare-and-append predecessor sequence."""
    if type(value) is not int or value < 0:
        raise ActivationRegistryError("expected_previous_sequence must be an integer >= 0")
    return value


def _build_deployment_identity_construction_runtime():
    """Build process-local snapshots so one identity object cannot be retargeted."""
    constructed_deployments: WeakValueDictionary[int, DeploymentIdentity] = WeakValueDictionary()
    constructed_fields: dict[int, tuple[str, str]] = {}
    state_lock = RLock()

    def discard_deployment_identity(deployment_object_id: int) -> None:
        """Drop field evidence when the corresponding deployment object is collected."""
        with state_lock:
            constructed_fields.pop(deployment_object_id, None)

    def record_or_require_deployment_identity(deployment: DeploymentIdentity) -> None:
        """Record first construction or reject later field retargeting on the same object."""
        deployment_object_id = id(deployment)
        current_fields = (deployment.deployment_id, deployment.environment_id)
        with state_lock:
            canonical_deployment = constructed_deployments.get(deployment_object_id)
            canonical_fields = constructed_fields.get(deployment_object_id)
            if canonical_deployment is None and canonical_fields is None:
                constructed_deployments[deployment_object_id] = deployment
                constructed_fields[deployment_object_id] = current_fields
                finalize(deployment, discard_deployment_identity, deployment_object_id)
                return
            if canonical_deployment is not deployment or canonical_fields != current_fields:
                raise ActivationRegistryError(
                    "DeploymentIdentity no longer matches its construction snapshot"
                )

    return record_or_require_deployment_identity


_record_or_require_deployment_identity = _build_deployment_identity_construction_runtime()


@dataclass(frozen=True, slots=True, weakref_slot=True)
class DeploymentIdentity:
    """Explicit non-PII deployment/environment coordinate for activation serialization."""

    deployment_id: str
    environment_id: str

    def __post_init__(self) -> None:
        """Validate durable key syntax and bind this object to its construction fields."""
        _canonical_identifier("deployment_id", self.deployment_id)
        _canonical_identifier("environment_id", self.environment_id)
        _record_or_require_deployment_identity(self)


@dataclass(frozen=True, slots=True)
class ActivationEvent:
    """One immutable transition in a deployment's activation sequence."""

    deployment: DeploymentIdentity
    activation_sequence: int
    generation_id: str
    previous_generation_id: str | None
    event_kind: EventKind
    evidence_bundle_sha256: str | None = None

    def __post_init__(self) -> None:
        """Enforce sequence, lineage and optional evidence invariants on one event."""
        if type(self.deployment) is not DeploymentIdentity:
            raise ActivationRegistryError("activation event requires exact DeploymentIdentity")
        if type(self.activation_sequence) is not int or self.activation_sequence <= 0:
            raise ActivationRegistryError("activation_sequence must be an integer > 0")
        _canonical_identifier("generation_id", self.generation_id)
        if self.previous_generation_id is not None:
            _canonical_identifier("previous_generation_id", self.previous_generation_id)
        if self.event_kind not in ("activate", "rollback"):
            raise ActivationRegistryError("event_kind must be activate or rollback")
        if self.activation_sequence == 1 and self.previous_generation_id is not None:
            raise ActivationRegistryError("first activation cannot have a previous generation")
        if self.activation_sequence > 1 and self.previous_generation_id is None:
            raise ActivationRegistryError("successor activation requires previous generation")
        if self.evidence_bundle_sha256 is not None:
            _evidence_digest(self.evidence_bundle_sha256)


@dataclass(frozen=True, slots=True)
class RecoveredActivation:
    """Active event plus the freshly reconstructed generation and optional attestation sequence."""

    event: ActivationEvent
    generation: CompositionGeneration
    recovery_sequence: int | None = None

    def __post_init__(self) -> None:
        """Require exact event/generation types and a valid durable recovery sequence when present."""
        if type(self.event) is not ActivationEvent:
            raise ActivationRegistryError("recovery requires exact ActivationEvent")
        if type(self.generation) is not CompositionGeneration:
            raise ActivationRegistryError("recovery requires exact CompositionGeneration")
        if self.event.generation_id != self.generation.generation_id:
            raise ActivationRegistryError("recovered event and generation must agree")
        if self.recovery_sequence is not None and (
            type(self.recovery_sequence) is not int or self.recovery_sequence <= 0
        ):
            raise ActivationRegistryError("recovery_sequence must be an integer > 0 when present")


@dataclass(frozen=True, slots=True)
class PostgresActivationRegistry:
    """Serialize structural activation and recover durable configuration.

    ``activate`` and ``rollback`` remain structural primitives for migration and fault
    tests. Product-facing positive authorization uses the authorized methods so evidence
    is persisted under the same transaction and deployment lock as the event append.
    """

    connection_factory: PostgresConnectionFactory

    def __post_init__(self) -> None:
        """Reject a registry that cannot open the caller-owned PostgreSQL boundary."""
        if not callable(self.connection_factory):
            raise TypeError("connection_factory must be callable")

    def activate(
        self,
        deployment: DeploymentIdentity,
        *,
        generation_id: str,
        expected_previous_sequence: int,
    ) -> ActivationEvent:
        """Append a structural activation after compare-and-locking deployment state."""
        return self._transition(
            deployment,
            generation_id=generation_id,
            expected_previous_sequence=expected_previous_sequence,
            event_kind="activate",
        )

    def rollback(
        self,
        deployment: DeploymentIdentity,
        *,
        generation_id: str,
        expected_previous_sequence: int,
    ) -> ActivationEvent:
        """Append structural rollback to a generation previously active on deployment."""
        return self._transition(
            deployment,
            generation_id=generation_id,
            expected_previous_sequence=expected_previous_sequence,
            event_kind="rollback",
        )

    def activate_authorized(
        self,
        deployment: DeploymentIdentity,
        *,
        generation_id: str,
        expected_previous_sequence: int,
        evidence_bundle_sha256: str,
        evidence_writer: TransactionEvidenceWriter,
        _connection_factory: PostgresConnectionFactory | None = None,
    ) -> ActivationEvent:
        """Append activation with local evidence persistence inside the locked transaction."""
        return self._transition(
            deployment,
            generation_id=generation_id,
            expected_previous_sequence=expected_previous_sequence,
            event_kind="activate",
            evidence_bundle_sha256=evidence_bundle_sha256,
            evidence_writer=evidence_writer,
            _connection_factory=_connection_factory,
        )

    def rollback_authorized(
        self,
        deployment: DeploymentIdentity,
        *,
        generation_id: str,
        expected_previous_sequence: int,
        evidence_bundle_sha256: str,
        evidence_writer: TransactionEvidenceWriter,
        _connection_factory: PostgresConnectionFactory | None = None,
    ) -> ActivationEvent:
        """Append rollback with local evidence persistence inside the locked transaction."""
        return self._transition(
            deployment,
            generation_id=generation_id,
            expected_previous_sequence=expected_previous_sequence,
            event_kind="rollback",
            evidence_bundle_sha256=evidence_bundle_sha256,
            evidence_writer=evidence_writer,
            _connection_factory=_connection_factory,
        )

    def recover_active(
        self,
        deployment: DeploymentIdentity,
        *,
        _connection_factory: PostgresConnectionFactory | None = None,
    ) -> RecoveredActivation | None:
        """Recover active event and generation from one repeatable-read database snapshot."""
        identity = self._deployment(deployment)
        connection_factory = self._resolved_connection_factory(_connection_factory)
        with connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(_REPEATABLE_READ_ONLY_SQL)
                current = self._latest_event(cursor, identity)
                if current is None:
                    return None
                generation = self._load_generation(cursor, current.generation_id)
                return RecoveredActivation(event=current, generation=generation)

    def recover_active_authorized(
        self,
        deployment: DeploymentIdentity,
        *,
        expected_activation_sequence: int,
        expected_generation_id: str,
        evidence_bundle_sha256: str,
        evidence_writer: TransactionEvidenceWriter,
        _connection_factory: PostgresConnectionFactory | None = None,
    ) -> RecoveredActivation:
        """Persist fresh recovery evidence only while the expected active state remains locked."""
        identity = self._deployment(deployment)
        expected_sequence = _expected_sequence(expected_activation_sequence)
        if expected_sequence == 0:
            raise ActivationRegistryError("authorized recovery requires an active sequence > 0")
        expected_generation = _canonical_identifier(
            "expected_generation_id",
            expected_generation_id,
        )
        evidence_digest = _evidence_digest(evidence_bundle_sha256)
        if not callable(evidence_writer):
            raise ActivationRegistryError("evidence_writer must be callable")
        connection_factory = self._resolved_connection_factory(_connection_factory)

        with connection_factory() as connection:
            with connection.cursor() as cursor:
                self._lock_deployment(cursor, identity)
                current = self._latest_event(cursor, identity)
                if (
                    current is None
                    or current.activation_sequence != expected_sequence
                    or current.generation_id != expected_generation
                ):
                    raise ActivationConflictError(
                        "activation changed during external recovery re-admission"
                    )
                if current.evidence_bundle_sha256 is None:
                    raise ActivationRegistryError(
                        "authorized recovery requires durable authorization evidence"
                    )

                generation = self._load_generation(cursor, expected_generation)
                evidence_writer(cursor)
                cursor.execute(
                    _SELECT_LATEST_RECOVERY_SEQUENCE_SQL,
                    (identity.deployment_id, identity.environment_id),
                )
                row = cursor.fetchone()
                if row is None or type(row[0]) is not int or row[0] < 0:
                    raise ActivationRegistryError(
                        "recovery attestation sequence query returned invalid durable state"
                    )
                next_recovery_sequence = row[0] + 1
                cursor.execute(
                    _INSERT_RECOVERY_ATTESTATION_SQL,
                    (
                        identity.deployment_id,
                        identity.environment_id,
                        next_recovery_sequence,
                        current.activation_sequence,
                        current.generation_id,
                        evidence_digest,
                    ),
                )
                if cursor.fetchone() != (next_recovery_sequence,):
                    raise ActivationRegistryError(
                        "recovery attestation insert did not return expected durable sequence"
                    )
                return RecoveredActivation(
                    event=current,
                    generation=generation,
                    recovery_sequence=next_recovery_sequence,
                )

    def _transition(
        self,
        deployment: DeploymentIdentity,
        *,
        generation_id: str,
        expected_previous_sequence: int,
        event_kind: EventKind,
        evidence_bundle_sha256: str | None = None,
        evidence_writer: TransactionEvidenceWriter | None = None,
        _connection_factory: PostgresConnectionFactory | None = None,
    ) -> ActivationEvent:
        """Lock one deployment and append exactly one compare-and-authorized transition."""
        identity = self._deployment(deployment)
        target_generation_id = _canonical_identifier("generation_id", generation_id)
        expected = _expected_sequence(expected_previous_sequence)
        evidence_digest = (
            None if evidence_bundle_sha256 is None else _evidence_digest(evidence_bundle_sha256)
        )
        if (evidence_digest is None) != (evidence_writer is None):
            raise ActivationRegistryError(
                "authorized transition requires both evidence digest and local writer"
            )
        if evidence_writer is not None and not callable(evidence_writer):
            raise ActivationRegistryError("evidence_writer must be callable")
        connection_factory = self._resolved_connection_factory(_connection_factory)

        with connection_factory() as connection:
            with connection.cursor() as cursor:
                self._lock_deployment(cursor, identity)
                current = self._latest_event(cursor, identity)
                current_sequence = 0 if current is None else current.activation_sequence
                if current_sequence != expected:
                    raise ActivationConflictError(
                        "expected previous activation sequence does not match durable state"
                    )
                if current is not None and current.generation_id == target_generation_id:
                    raise ActivationConflictError("target generation is already active")
                if event_kind == "rollback":
                    if current is None:
                        raise ActivationRegistryError(
                            "rollback requires a previously active generation"
                        )
                    cursor.execute(
                        _SELECT_PRIOR_TARGET_SQL,
                        (
                            identity.deployment_id,
                            identity.environment_id,
                            target_generation_id,
                            current.activation_sequence,
                        ),
                    )
                    if cursor.fetchone() is None:
                        raise ActivationRegistryError(
                            "rollback target must have been previously active on deployment"
                        )

                self._load_generation(cursor, target_generation_id)
                next_sequence = current_sequence + 1
                previous_generation_id = None if current is None else current.generation_id
                if evidence_writer is not None:
                    evidence_writer(cursor)
                    statement = _INSERT_AUTHORIZED_EVENT_SQL
                    params = (
                        identity.deployment_id,
                        identity.environment_id,
                        next_sequence,
                        target_generation_id,
                        previous_generation_id,
                        event_kind,
                        evidence_digest,
                    )
                else:
                    statement = _INSERT_EVENT_SQL
                    params = (
                        identity.deployment_id,
                        identity.environment_id,
                        next_sequence,
                        target_generation_id,
                        previous_generation_id,
                        event_kind,
                    )
                cursor.execute(statement, params)
                inserted = cursor.fetchone()
                if inserted != (next_sequence,):
                    raise ActivationRegistryError(
                        "activation event insert did not return expected durable sequence"
                    )
                return ActivationEvent(
                    deployment=identity,
                    activation_sequence=next_sequence,
                    generation_id=target_generation_id,
                    previous_generation_id=previous_generation_id,
                    event_kind=event_kind,
                    evidence_bundle_sha256=evidence_digest,
                )

    def _resolved_connection_factory(
        self,
        expected: PostgresConnectionFactory | None,
    ) -> PostgresConnectionFactory:
        """Pin the current factory or reject drift from a caller-admitted factory."""
        connection_factory = self.connection_factory if expected is None else expected
        if self.connection_factory is not connection_factory:
            raise ActivationRegistryError(
                "activation registry no longer uses expected PostgreSQL connection factory"
            )
        return connection_factory

    @staticmethod
    def _deployment(deployment: DeploymentIdentity) -> DeploymentIdentity:
        """Revalidate an exact deployment object before it enters a durable transaction."""
        if type(deployment) is not DeploymentIdentity:
            raise ActivationRegistryError("deployment must be exact DeploymentIdentity")
        DeploymentIdentity.__post_init__(deployment)
        return deployment

    @staticmethod
    def _lock_deployment(cursor: Any, deployment: DeploymentIdentity) -> None:
        """Create-if-absent then lock the durable row that serializes deployment writers."""
        params = (deployment.deployment_id, deployment.environment_id)
        cursor.execute(_INSERT_DEPLOYMENT_SQL, params)
        cursor.execute(_LOCK_DEPLOYMENT_SQL, params)
        if cursor.fetchone() != params:
            raise ActivationRegistryError("deployment lock did not resolve exact identity")

    @staticmethod
    def _latest_event(cursor: Any, deployment: DeploymentIdentity) -> ActivationEvent | None:
        """Reconstruct the latest append-only event for a locked or snapshot deployment."""
        cursor.execute(
            _SELECT_LATEST_EVENT_SQL,
            (deployment.deployment_id, deployment.environment_id),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        (
            activation_sequence,
            generation_id,
            event_kind,
            previous_generation_id,
            evidence_bundle_sha256,
        ) = row
        return ActivationEvent(
            deployment=deployment,
            activation_sequence=activation_sequence,
            generation_id=generation_id,
            previous_generation_id=previous_generation_id,
            event_kind=event_kind,
            evidence_bundle_sha256=evidence_bundle_sha256,
        )

    @staticmethod
    def _load_generation(cursor: Any, generation_id: str) -> CompositionGeneration:
        """Reconstruct a persisted generation and translate registry corruption at this boundary."""
        records = PostgresGenerationRegistry._load_record_set(cursor, generation_id)
        if records is None:
            raise ActivationRegistryError("activation target requires a persisted generation")
        try:
            return records.restore_generation()
        except CompositionRegistryError as exc:
            raise ActivationRegistryError(
                "persisted generation failed canonical reconstruction"
            ) from exc
