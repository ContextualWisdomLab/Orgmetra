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
EventKind = Literal["activate", "rollback"]
_CANONICAL_IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")

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
SELECT activation_sequence, generation_id, event_kind, previous_generation_id
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

_REPEATABLE_READ_ONLY_SQL = "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"


class ActivationRegistryError(CompositionRegistryError):
    """Raised when durable activation evidence is invalid or incomplete."""


class ActivationConflictError(ActivationRegistryError):
    """Raised when compare-and-append activation state has advanced or is a no-op."""


def _canonical_identifier(field_name: str, value: object) -> str:
    if type(value) is not str:
        raise ActivationRegistryError(f"{field_name} must be an exact built-in str")
    if not 1 <= len(value) <= 64 or _CANONICAL_IDENTIFIER.fullmatch(value) is None:
        raise ActivationRegistryError(
            f"{field_name} must be canonical 1..64-character lower snake_case"
        )
    return value


def _expected_sequence(value: object) -> int:
    if type(value) is not int or value < 0:
        raise ActivationRegistryError("expected_previous_sequence must be an integer >= 0")
    return value


def _build_deployment_identity_construction_runtime():
    """Build process-local snapshots so one identity object cannot be retargeted."""
    constructed_deployments: WeakValueDictionary[int, DeploymentIdentity] = WeakValueDictionary()
    constructed_fields: dict[int, tuple[str, str]] = {}
    state_lock = RLock()

    def discard_deployment_identity(deployment_object_id: int) -> None:
        with state_lock:
            constructed_fields.pop(deployment_object_id, None)

    def record_or_require_deployment_identity(deployment: DeploymentIdentity) -> None:
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

    def __post_init__(self) -> None:
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


@dataclass(frozen=True, slots=True)
class RecoveredActivation:
    """Active event plus the freshly reconstructed immutable generation it selects."""

    event: ActivationEvent
    generation: CompositionGeneration

    def __post_init__(self) -> None:
        if type(self.event) is not ActivationEvent:
            raise ActivationRegistryError("recovery requires exact ActivationEvent")
        if type(self.generation) is not CompositionGeneration:
            raise ActivationRegistryError("recovery requires exact CompositionGeneration")
        if self.event.generation_id != self.generation.generation_id:
            raise ActivationRegistryError("recovered event and generation must agree")


@dataclass(frozen=True, slots=True)
class PostgresActivationRegistry:
    """Serialize deployment activation and recover active durable configuration."""

    connection_factory: PostgresConnectionFactory

    def __post_init__(self) -> None:
        if not callable(self.connection_factory):
            raise TypeError("connection_factory must be callable")

    def activate(
        self,
        deployment: DeploymentIdentity,
        *,
        generation_id: str,
        expected_previous_sequence: int,
    ) -> ActivationEvent:
        """Append a normal activation after compare-and-locking the deployment state."""
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
        """Append rollback to a generation that was previously active on this deployment."""
        return self._transition(
            deployment,
            generation_id=generation_id,
            expected_previous_sequence=expected_previous_sequence,
            event_kind="rollback",
        )

    def recover_active(self, deployment: DeploymentIdentity) -> RecoveredActivation | None:
        """Recover active event and generation from one repeatable-read database snapshot."""
        identity = self._deployment(deployment)
        with self.connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(_REPEATABLE_READ_ONLY_SQL)
                current = self._latest_event(cursor, identity)
                if current is None:
                    return None
                generation = self._load_generation(cursor, current.generation_id)
                return RecoveredActivation(event=current, generation=generation)

    def _transition(
        self,
        deployment: DeploymentIdentity,
        *,
        generation_id: str,
        expected_previous_sequence: int,
        event_kind: EventKind,
    ) -> ActivationEvent:
        identity = self._deployment(deployment)
        target_generation_id = _canonical_identifier("generation_id", generation_id)
        expected = _expected_sequence(expected_previous_sequence)

        with self.connection_factory() as connection:
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
                cursor.execute(
                    _INSERT_EVENT_SQL,
                    (
                        identity.deployment_id,
                        identity.environment_id,
                        next_sequence,
                        target_generation_id,
                        previous_generation_id,
                        event_kind,
                    ),
                )
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
                )

    @staticmethod
    def _deployment(deployment: DeploymentIdentity) -> DeploymentIdentity:
        if type(deployment) is not DeploymentIdentity:
            raise ActivationRegistryError("deployment must be exact DeploymentIdentity")
        DeploymentIdentity.__post_init__(deployment)
        return deployment

    @staticmethod
    def _lock_deployment(cursor: Any, deployment: DeploymentIdentity) -> None:
        params = (deployment.deployment_id, deployment.environment_id)
        cursor.execute(_INSERT_DEPLOYMENT_SQL, params)
        cursor.execute(_LOCK_DEPLOYMENT_SQL, params)
        if cursor.fetchone() != params:
            raise ActivationRegistryError("deployment lock did not resolve exact identity")

    @staticmethod
    def _latest_event(cursor: Any, deployment: DeploymentIdentity) -> ActivationEvent | None:
        cursor.execute(
            _SELECT_LATEST_EVENT_SQL,
            (deployment.deployment_id, deployment.environment_id),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        activation_sequence, generation_id, event_kind, previous_generation_id = row
        return ActivationEvent(
            deployment=deployment,
            activation_sequence=activation_sequence,
            generation_id=generation_id,
            previous_generation_id=previous_generation_id,
            event_kind=event_kind,
        )

    @staticmethod
    def _load_generation(cursor: Any, generation_id: str) -> CompositionGeneration:
        records = PostgresGenerationRegistry._load_record_set(cursor, generation_id)
        if records is None:
            raise ActivationRegistryError("activation target requires a persisted generation")
        try:
            return records.restore_generation()
        except CompositionRegistryError as exc:
            raise ActivationRegistryError(
                "persisted generation failed canonical reconstruction"
            ) from exc
