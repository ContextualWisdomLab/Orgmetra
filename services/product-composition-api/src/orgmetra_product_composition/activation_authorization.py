"""Fail-closed external re-admission evidence for composition activation.

Remote identity, ACL, and owner-operation checks run through a caller-supplied verifier
before the structural activation registry acquires its deployment row lock. Exact evidence
coordinates are then persisted by a local transaction callback before activation append or
while recovery rechecks the same active state under that lock.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
from threading import RLock
from time import time_ns
from typing import Any, Callable, Literal
from weakref import WeakValueDictionary, finalize

from .activation import (
    ActivationEvent,
    ActivationRegistryError,
    DeploymentIdentity,
    PostgresActivationRegistry as StructuralPostgresActivationRegistry,
)
from .admission import CompositionGeneration, _revalidate_generation_snapshot
from .postgres_registry import PostgresConnectionFactory, PostgresGenerationRegistry

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
_POLICY_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_ALLOWED_METHODS = frozenset({"DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"})
_FLOATING_RELEASES = frozenset({"develop", "head", "latest", "main", "master"})
AuthorityId = Literal["keyverse", "orgmetra"]
AuthorizationAction = Literal["activate", "rollback", "recover"]

_INSERT_EVIDENCE_SQL = """
INSERT INTO public.product_composition_activation_evidence (
    evidence_bundle_sha256,
    deployment_id,
    environment_id,
    generation_id,
    config_sha256,
    authorization_action,
    authorized_state_sequence,
    keyverse_release_version,
    keyverse_artifact_sha256,
    keyverse_release_locator,
    orgmetra_release_version,
    orgmetra_artifact_sha256,
    orgmetra_release_locator,
    orgmetra_policy_version_code,
    authorization_decision_sha256,
    valid_until_unix_ms
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (evidence_bundle_sha256) DO NOTHING
RETURNING evidence_bundle_sha256
""".strip()

_SELECT_EVIDENCE_SQL = """
SELECT
    deployment_id,
    environment_id,
    generation_id,
    config_sha256,
    authorization_action,
    authorized_state_sequence,
    keyverse_release_version,
    keyverse_artifact_sha256,
    keyverse_release_locator,
    orgmetra_release_version,
    orgmetra_artifact_sha256,
    orgmetra_release_locator,
    orgmetra_policy_version_code,
    authorization_decision_sha256,
    valid_until_unix_ms
FROM public.product_composition_activation_evidence
WHERE evidence_bundle_sha256 = %s
""".strip()

_INSERT_OBSERVATION_SQL = """
INSERT INTO public.product_composition_activation_owner_observation (
    evidence_bundle_sha256,
    generation_id,
    route_id,
    method,
    path_template,
    service_id,
    release_version,
    openapi_sha256,
    artifact_sha256,
    observation_sha256,
    observed_at_unix_ms,
    valid_until_unix_ms
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (evidence_bundle_sha256, route_id, method) DO NOTHING
""".strip()

_SELECT_OBSERVATIONS_SQL = """
SELECT
    route_id,
    method,
    path_template,
    service_id,
    release_version,
    openapi_sha256,
    artifact_sha256,
    observation_sha256,
    observed_at_unix_ms,
    valid_until_unix_ms
FROM public.product_composition_activation_owner_observation
WHERE evidence_bundle_sha256 = %s
ORDER BY route_id, method
""".strip()


class ActivationAuthorizationError(ActivationRegistryError):
    """Raised when external authorization or owner-operation evidence is unusable."""


def _exact_text(field_name: str, value: object, *, maximum: int) -> str:
    """Require exact bounded text before it can participate in authority identity."""
    if type(value) is not str:
        raise ActivationAuthorizationError(f"{field_name} must be an exact built-in str")
    if not value or len(value) > maximum:
        raise ActivationAuthorizationError(f"{field_name} must contain 1..{maximum} characters")
    return value


def _identifier(field_name: str, value: object) -> str:
    """Require the canonical lower-snake identifier representation used in durable evidence."""
    text = _exact_text(field_name, value, maximum=64)
    if _IDENTIFIER.fullmatch(text) is None:
        raise ActivationAuthorizationError(f"{field_name} must be canonical lower snake_case")
    return text


def _sha256(field_name: str, value: object) -> str:
    """Require an exact lowercase SHA-256 digest for content-addressed authority evidence."""
    text = _exact_text(field_name, value, maximum=64)
    if _SHA256.fullmatch(text) is None:
        raise ActivationAuthorizationError(f"{field_name} must be a lowercase SHA-256 digest")
    return text


def _release_version(field_name: str, value: object) -> str:
    """Reject floating refs and require an immutable release-version representation."""
    text = _exact_text(field_name, value, maximum=64)
    if text.lower() in _FLOATING_RELEASES or text.lower().startswith(("refs/", "pr-")):
        raise ActivationAuthorizationError(f"{field_name} must identify an immutable release")
    if _VERSION.fullmatch(text) is None:
        raise ActivationAuthorizationError(f"{field_name} has an unsupported representation")
    return text


def _unix_ms(field_name: str, value: object) -> int:
    """Require a positive exact integer wall-clock value expressed in milliseconds."""
    if type(value) is not int or value <= 0:
        raise ActivationAuthorizationError(f"{field_name} must be an integer > 0")
    return value


def _authorization_action(value: object) -> AuthorizationAction:
    """Constrain durable evidence intent to the three supported state-transition actions."""
    if type(value) is not str or value not in ("activate", "rollback", "recover"):
        raise ActivationAuthorizationError(
            "authorization_action must be activate, rollback, or recover"
        )
    return value


def _state_sequence(value: object) -> int:
    """Require the non-negative durable state sequence authorized by the evidence bundle."""
    if type(value) is not int or value < 0:
        raise ActivationAuthorizationError("authorized_state_sequence must be an integer >= 0")
    return value


def _build_construction_runtime(
    label: str,
    projector: Callable[[Any], tuple[object, ...]],
) -> Callable[[Any], None]:
    """Build a process-local construction snapshot guard for one evidence value type."""
    constructed_objects: WeakValueDictionary[int, object] = WeakValueDictionary()
    constructed_fields: dict[int, tuple[object, ...]] = {}
    state_lock = RLock()

    def discard_construction(object_id: int) -> None:
        """Discard projected field evidence when its weakly tracked value is collected."""
        with state_lock:
            constructed_fields.pop(object_id, None)

    def record_or_require(value: object) -> None:
        """Record first construction or reject later semantic retargeting of the same value."""
        object_id = id(value)
        current_fields = projector(value)
        with state_lock:
            canonical_object = constructed_objects.get(object_id)
            canonical_fields = constructed_fields.get(object_id)
            if canonical_object is None and canonical_fields is None:
                constructed_objects[object_id] = value
                constructed_fields[object_id] = current_fields
                finalize(value, discard_construction, object_id)
                return
            if canonical_object is not value or canonical_fields != current_fields:
                raise ActivationAuthorizationError(
                    f"{label} no longer matches its construction snapshot"
                )

    return record_or_require


@dataclass(frozen=True, slots=True, weakref_slot=True)
class ReleasedAuthorityEvidence:
    """Immutable release coordinate for one external activation authority."""

    authority_id: AuthorityId
    release_version: str
    artifact_sha256: str
    release_locator: str

    def __post_init__(self) -> None:
        """Bind authority identity, artifact digest and version to the canonical release URL."""
        if self.authority_id not in ("keyverse", "orgmetra"):
            raise ActivationAuthorizationError("authority_id must be keyverse or orgmetra")
        release_version = _release_version("release_version", self.release_version)
        artifact_sha256 = _sha256("artifact_sha256", self.artifact_sha256)
        repository = "keyverse" if self.authority_id == "keyverse" else "Orgmetra"
        expected_locator = (
            f"https://github.com/ContextualWisdomLab/{repository}/releases/tag/{release_version}"
        )
        locator = _exact_text("release_locator", self.release_locator, maximum=512)
        if locator != expected_locator:
            raise ActivationAuthorizationError(
                "release_locator must bind the exact canonical authority release"
            )
        object.__setattr__(self, "release_version", release_version)
        object.__setattr__(self, "artifact_sha256", artifact_sha256)
        object.__setattr__(self, "release_locator", locator)
        _record_or_require_released_authority_construction(self)


_record_or_require_released_authority_construction = _build_construction_runtime(
    "ReleasedAuthorityEvidence",
    lambda value: (
        value.authority_id,
        value.release_version,
        value.artifact_sha256,
        value.release_locator,
    ),
)


@dataclass(frozen=True, slots=True, weakref_slot=True)
class OwnerOperationObservation:
    """Fresh observation for one route operation on one exact owner release."""

    route_id: str
    path_template: str
    method: str
    service_id: str
    release_version: str
    openapi_sha256: str
    artifact_sha256: str
    observation_sha256: str
    observed_at_unix_ms: int
    valid_until_unix_ms: int

    def __post_init__(self) -> None:
        """Normalize one observed operation and bind it to its immutable owner release."""
        object.__setattr__(self, "route_id", _identifier("route_id", self.route_id))
        object.__setattr__(self, "service_id", _identifier("service_id", self.service_id))
        object.__setattr__(
            self,
            "path_template",
            _exact_text("path_template", self.path_template, maximum=256),
        )
        method = _exact_text("method", self.method, maximum=7)
        if method not in _ALLOWED_METHODS:
            raise ActivationAuthorizationError("method is not an admitted HTTP method")
        object.__setattr__(self, "method", method)
        object.__setattr__(
            self,
            "release_version",
            _release_version("release_version", self.release_version),
        )
        object.__setattr__(
            self,
            "openapi_sha256",
            _sha256("openapi_sha256", self.openapi_sha256),
        )
        object.__setattr__(
            self,
            "artifact_sha256",
            _sha256("artifact_sha256", self.artifact_sha256),
        )
        object.__setattr__(
            self,
            "observation_sha256",
            _sha256("observation_sha256", self.observation_sha256),
        )
        observed_at = _unix_ms("observed_at_unix_ms", self.observed_at_unix_ms)
        valid_until = _unix_ms("valid_until_unix_ms", self.valid_until_unix_ms)
        if valid_until <= observed_at:
            raise ActivationAuthorizationError(
                "owner operation evidence must expire after observation"
            )
        _record_or_require_owner_observation_construction(self)

    def authority_key(self) -> tuple[str, str, str, str, str, str, str]:
        """Return the exact generation operation identity covered by this observation."""
        OwnerOperationObservation.__post_init__(self)
        return (
            self.route_id,
            self.path_template,
            self.method,
            self.service_id,
            self.release_version,
            self.openapi_sha256,
            self.artifact_sha256,
        )


_record_or_require_owner_observation_construction = _build_construction_runtime(
    "OwnerOperationObservation",
    lambda value: (
        value.route_id,
        value.path_template,
        value.method,
        value.service_id,
        value.release_version,
        value.openapi_sha256,
        value.artifact_sha256,
        value.observation_sha256,
        value.observed_at_unix_ms,
        value.valid_until_unix_ms,
    ),
)


@dataclass(frozen=True, slots=True, weakref_slot=True)
class ActivationAdmissionEvidence:
    """Fresh allow evidence bound to one deployment, transition intent, and exact generation."""

    deployment_id: str
    environment_id: str
    generation_id: str
    config_sha256: str
    authorization_action: AuthorizationAction
    authorized_state_sequence: int
    keyverse_authority: ReleasedAuthorityEvidence
    orgmetra_authority: ReleasedAuthorityEvidence
    orgmetra_policy_version_code: str
    authorization_decision_sha256: str
    owner_operations: tuple[OwnerOperationObservation, ...]
    valid_until_unix_ms: int

    def __post_init__(self) -> None:
        """Validate exact authority, transition and owner-operation material at construction."""
        object.__setattr__(
            self,
            "deployment_id",
            _identifier("deployment_id", self.deployment_id),
        )
        object.__setattr__(
            self,
            "environment_id",
            _identifier("environment_id", self.environment_id),
        )
        object.__setattr__(
            self,
            "generation_id",
            _identifier("generation_id", self.generation_id),
        )
        object.__setattr__(self, "config_sha256", _sha256("config_sha256", self.config_sha256))
        object.__setattr__(
            self,
            "authorization_action",
            _authorization_action(self.authorization_action),
        )
        object.__setattr__(
            self,
            "authorized_state_sequence",
            _state_sequence(self.authorized_state_sequence),
        )
        if type(self.keyverse_authority) is not ReleasedAuthorityEvidence:
            raise ActivationAuthorizationError(
                "keyverse_authority must be exact ReleasedAuthorityEvidence"
            )
        ReleasedAuthorityEvidence.__post_init__(self.keyverse_authority)
        if self.keyverse_authority.authority_id != "keyverse":
            raise ActivationAuthorizationError("keyverse_authority must identify keyverse")
        if type(self.orgmetra_authority) is not ReleasedAuthorityEvidence:
            raise ActivationAuthorizationError(
                "orgmetra_authority must be exact ReleasedAuthorityEvidence"
            )
        ReleasedAuthorityEvidence.__post_init__(self.orgmetra_authority)
        if self.orgmetra_authority.authority_id != "orgmetra":
            raise ActivationAuthorizationError("orgmetra_authority must identify orgmetra")
        policy_version = _exact_text(
            "orgmetra_policy_version_code",
            self.orgmetra_policy_version_code,
            maximum=128,
        )
        if _POLICY_VERSION.fullmatch(policy_version) is None:
            raise ActivationAuthorizationError(
                "orgmetra_policy_version_code must be a whitespace-free immutable token"
            )
        object.__setattr__(self, "orgmetra_policy_version_code", policy_version)
        object.__setattr__(
            self,
            "authorization_decision_sha256",
            _sha256("authorization_decision_sha256", self.authorization_decision_sha256),
        )
        if type(self.owner_operations) is not tuple or any(
            type(item) is not OwnerOperationObservation for item in self.owner_operations
        ):
            raise ActivationAuthorizationError(
                "owner_operations must be an exact tuple of OwnerOperationObservation values"
            )
        for observation in self.owner_operations:
            OwnerOperationObservation.__post_init__(observation)
        _unix_ms("valid_until_unix_ms", self.valid_until_unix_ms)
        _record_or_require_activation_evidence_construction(self)

    def validate_for(
        self,
        *,
        deployment_id: str,
        environment_id: str,
        generation: CompositionGeneration,
        authorization_action: AuthorizationAction,
        authorized_state_sequence: int,
        now_unix_ms: int,
    ) -> None:
        """Require freshness and whole-route owner coverage before evidence can be used."""
        ActivationAdmissionEvidence.__post_init__(self)
        expected_deployment_id = _identifier("deployment_id", deployment_id)
        expected_environment_id = _identifier("environment_id", environment_id)
        expected_action = _authorization_action(authorization_action)
        expected_state_sequence = _state_sequence(authorized_state_sequence)
        if type(generation) is not CompositionGeneration:
            raise ActivationAuthorizationError("generation must be exact CompositionGeneration")
        _revalidate_generation_snapshot(generation)
        now = _unix_ms("now_unix_ms", now_unix_ms)
        if (
            self.deployment_id != expected_deployment_id
            or self.environment_id != expected_environment_id
        ):
            raise ActivationAuthorizationError("authorization evidence targets another deployment")
        if (
            self.generation_id != generation.generation_id
            or self.config_sha256 != generation.config_sha256
        ):
            raise ActivationAuthorizationError("authorization evidence targets another generation")
        if self.authorization_action != expected_action:
            raise ActivationAuthorizationError(
                "authorization evidence targets another authorization action"
            )
        if self.authorized_state_sequence != expected_state_sequence:
            raise ActivationAuthorizationError("authorization evidence targets another state sequence")
        if now >= self.valid_until_unix_ms:
            raise ActivationAuthorizationError("activation authorization evidence is expired")

        expected_operations_by_route = {
            route.route_id: {
                (
                    route.route_id,
                    route.path_template,
                    method,
                    route.owner_release.service_id,
                    route.owner_release.release_version,
                    route.owner_release.openapi_sha256,
                    route.owner_release.artifact_sha256,
                )
                for method in route.methods
            }
            for route in generation.routes
        }
        expected_operations = set().union(*expected_operations_by_route.values())
        observed_operations = [item.authority_key() for item in self.owner_operations]
        observed_operation_set = set(observed_operations)
        if len(observed_operation_set) != len(observed_operations):
            raise ActivationAuthorizationError(
                "owner operation evidence must not contain duplicates"
            )
        if not observed_operation_set.issubset(expected_operations):
            raise ActivationAuthorizationError(
                "owner operation evidence targets another generation route operation"
            )

        for route in generation.routes:
            expected_route_operations = expected_operations_by_route[route.route_id]
            observed_route_operations = {
                operation
                for operation in observed_operation_set
                if operation[0] == route.route_id
            }
            if route.required:
                if observed_route_operations != expected_route_operations:
                    raise ActivationAuthorizationError(
                        f"required route {route.route_id} requires exact owner operation coverage"
                    )
                continue
            if observed_route_operations and observed_route_operations != expected_route_operations:
                raise ActivationAuthorizationError(
                    f"optional route {route.route_id} owner operation evidence must be absent or complete"
                )

        for observation in self.owner_operations:
            if observation.observed_at_unix_ms > now:
                raise ActivationAuthorizationError(
                    "owner operation observation is from the future"
                )
            if now >= observation.valid_until_unix_ms:
                raise ActivationAuthorizationError("owner operation observation is expired")
            if self.valid_until_unix_ms > observation.valid_until_unix_ms:
                raise ActivationAuthorizationError(
                    "activation evidence validity must not outlive owner operation evidence"
                )

    def bundle_sha256(self) -> str:
        """Digest exact evidence coordinates for durable attribution."""
        ActivationAdmissionEvidence.__post_init__(self)
        material = {
            "deployment_id": self.deployment_id,
            "environment_id": self.environment_id,
            "generation_id": self.generation_id,
            "config_sha256": self.config_sha256,
            "authorization_action": self.authorization_action,
            "authorized_state_sequence": self.authorized_state_sequence,
            "keyverse_authority": {
                "release_version": self.keyverse_authority.release_version,
                "artifact_sha256": self.keyverse_authority.artifact_sha256,
                "release_locator": self.keyverse_authority.release_locator,
            },
            "orgmetra_authority": {
                "release_version": self.orgmetra_authority.release_version,
                "artifact_sha256": self.orgmetra_authority.artifact_sha256,
                "release_locator": self.orgmetra_authority.release_locator,
                "policy_version_code": self.orgmetra_policy_version_code,
            },
            "authorization_decision_sha256": self.authorization_decision_sha256,
            "owner_operations": [
                {
                    "route_id": item.route_id,
                    "path_template": item.path_template,
                    "method": item.method,
                    "service_id": item.service_id,
                    "release_version": item.release_version,
                    "openapi_sha256": item.openapi_sha256,
                    "artifact_sha256": item.artifact_sha256,
                    "observation_sha256": item.observation_sha256,
                    "observed_at_unix_ms": item.observed_at_unix_ms,
                    "valid_until_unix_ms": item.valid_until_unix_ms,
                }
                for item in sorted(
                    self.owner_operations,
                    key=lambda value: (value.route_id, value.method),
                )
            ],
            "valid_until_unix_ms": self.valid_until_unix_ms,
        }
        encoded = json.dumps(material, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _root_row(self) -> tuple[object, ...]:
        """Project the exact non-PII durable root material behind the bundle digest."""
        ActivationAdmissionEvidence.__post_init__(self)
        return (
            self.deployment_id,
            self.environment_id,
            self.generation_id,
            self.config_sha256,
            self.authorization_action,
            self.authorized_state_sequence,
            self.keyverse_authority.release_version,
            self.keyverse_authority.artifact_sha256,
            self.keyverse_authority.release_locator,
            self.orgmetra_authority.release_version,
            self.orgmetra_authority.artifact_sha256,
            self.orgmetra_authority.release_locator,
            self.orgmetra_policy_version_code,
            self.authorization_decision_sha256,
            self.valid_until_unix_ms,
        )

    def _observation_rows(self) -> tuple[tuple[object, ...], ...]:
        """Project deterministic durable owner-operation evidence without response payloads."""
        ActivationAdmissionEvidence.__post_init__(self)
        return tuple(
            (
                item.route_id,
                item.method,
                item.path_template,
                item.service_id,
                item.release_version,
                item.openapi_sha256,
                item.artifact_sha256,
                item.observation_sha256,
                item.observed_at_unix_ms,
                item.valid_until_unix_ms,
            )
            for item in sorted(self.owner_operations, key=lambda value: (value.route_id, value.method))
        )


_record_or_require_activation_evidence_construction = _build_construction_runtime(
    "ActivationAdmissionEvidence",
    lambda value: (
        value.deployment_id,
        value.environment_id,
        value.generation_id,
        value.config_sha256,
        value.authorization_action,
        value.authorized_state_sequence,
        value.keyverse_authority,
        value.orgmetra_authority,
        value.orgmetra_policy_version_code,
        value.authorization_decision_sha256,
        value.owner_operations,
        value.valid_until_unix_ms,
    ),
)


ActivationEvidenceProvider = Callable[
    [DeploymentIdentity, CompositionGeneration, AuthorizationAction, int], ActivationAdmissionEvidence
]
ClockUnixMs = Callable[[], int]


@dataclass(frozen=True, slots=True)
class AuthorizedActivation:
    """Structural activation result plus the external evidence that allowed it."""

    event: ActivationEvent
    generation: CompositionGeneration
    evidence: ActivationAdmissionEvidence


@dataclass(frozen=True, slots=True)
class AuthorizedRecoveredActivation:
    """Restart recovery result re-admitted with fresh external evidence."""

    event: ActivationEvent
    generation: CompositionGeneration
    evidence: ActivationAdmissionEvidence


def _persist_activation_evidence(cursor: Any, evidence: ActivationAdmissionEvidence) -> None:
    """Persist or verify one content-addressed evidence bundle inside activation transaction."""
    ActivationAdmissionEvidence.__post_init__(evidence)
    bundle_sha256 = evidence.bundle_sha256()
    root_row = evidence._root_row()
    cursor.execute(_INSERT_EVIDENCE_SQL, (bundle_sha256, *root_row))
    cursor.fetchone()
    cursor.execute(_SELECT_EVIDENCE_SQL, (bundle_sha256,))
    if cursor.fetchone() != root_row:
        raise ActivationAuthorizationError(
            "activation evidence digest is bound to different durable root material"
        )

    for observation in evidence.owner_operations:
        cursor.execute(
            _INSERT_OBSERVATION_SQL,
            (
                bundle_sha256,
                evidence.generation_id,
                observation.route_id,
                observation.method,
                observation.path_template,
                observation.service_id,
                observation.release_version,
                observation.openapi_sha256,
                observation.artifact_sha256,
                observation.observation_sha256,
                observation.observed_at_unix_ms,
                observation.valid_until_unix_ms,
            ),
        )
    cursor.execute(_SELECT_OBSERVATIONS_SQL, (bundle_sha256,))
    if tuple(cursor.fetchall()) != evidence._observation_rows():
        raise ActivationAuthorizationError(
            "activation evidence digest is bound to different durable owner observations"
        )


@dataclass(slots=True)
class AuthorizedPostgresActivationRegistry:
    """Re-admit durable state without remote I/O under the deployment row lock.

    The provider runs before the lock. Activation/rollback persist evidence and append the
    transition in one local transaction. Recovery samples state once, performs external
    verification, then locks and rechecks that same state while persisting a recovery
    attestation. PostgreSQL independently checks evidence intent, expiry and operation coverage.
    """

    connection_factory: PostgresConnectionFactory
    evidence_provider: ActivationEvidenceProvider
    clock_unix_ms: ClockUnixMs = lambda: time_ns() // 1_000_000
    _generation_registry: PostgresGenerationRegistry = field(init=False, repr=False)
    _structural_registry: StructuralPostgresActivationRegistry = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Validate executable inputs and construct PostgreSQL adapters from one factory."""
        if not callable(self.connection_factory):
            raise TypeError("connection_factory must be callable")
        if not callable(self.evidence_provider):
            raise TypeError("evidence_provider must be callable")
        if not callable(self.clock_unix_ms):
            raise TypeError("clock_unix_ms must be callable")
        self._generation_registry = PostgresGenerationRegistry(self.connection_factory)
        self._structural_registry = StructuralPostgresActivationRegistry(self.connection_factory)

    def _load_target(self, generation_id: str) -> CompositionGeneration:
        """Require the requested activation target to exist in durable generation authority."""
        generation = self._generation_registry.load(generation_id)
        if generation is None:
            raise ActivationAuthorizationError(
                "activation authorization requires a persisted generation"
            )
        return generation

    def _obtain_evidence(
        self,
        deployment: DeploymentIdentity,
        generation: CompositionGeneration,
        *,
        authorization_action: AuthorizationAction,
        authorized_state_sequence: int,
    ) -> ActivationAdmissionEvidence:
        """Acquire and validate exact external evidence for one intended durable transition."""
        if type(deployment) is not DeploymentIdentity:
            raise ActivationAuthorizationError("deployment must be exact DeploymentIdentity")
        DeploymentIdentity.__post_init__(deployment)
        _revalidate_generation_snapshot(generation)
        action = _authorization_action(authorization_action)
        state_sequence = _state_sequence(authorized_state_sequence)
        evidence = self.evidence_provider(deployment, generation, action, state_sequence)
        if type(evidence) is not ActivationAdmissionEvidence:
            raise ActivationAuthorizationError(
                "evidence_provider must return exact ActivationAdmissionEvidence"
            )
        evidence.validate_for(
            deployment_id=deployment.deployment_id,
            environment_id=deployment.environment_id,
            generation=generation,
            authorization_action=action,
            authorized_state_sequence=state_sequence,
            now_unix_ms=self.clock_unix_ms(),
        )
        return evidence

    @staticmethod
    def _evidence_writer(evidence: ActivationAdmissionEvidence) -> Callable[[Any], None]:
        """Bind one evidence value to a transaction-local persistence callback."""
        def write(cursor: Any) -> None:
            """Persist the captured evidence using the caller's already-open transaction."""
            _persist_activation_evidence(cursor, evidence)

        return write

    def activate(
        self,
        deployment: DeploymentIdentity,
        *,
        generation_id: str,
        expected_previous_sequence: int,
    ) -> AuthorizedActivation:
        """Authorize remotely, then persist evidence and append under one local transaction."""
        generation = self._load_target(generation_id)
        evidence = self._obtain_evidence(
            deployment,
            generation,
            authorization_action="activate",
            authorized_state_sequence=expected_previous_sequence,
        )
        event = self._structural_registry.activate_authorized(
            deployment,
            generation_id=generation.generation_id,
            expected_previous_sequence=expected_previous_sequence,
            evidence_bundle_sha256=evidence.bundle_sha256(),
            evidence_writer=self._evidence_writer(evidence),
        )
        return AuthorizedActivation(event=event, generation=generation, evidence=evidence)

    def rollback(
        self,
        deployment: DeploymentIdentity,
        *,
        generation_id: str,
        expected_previous_sequence: int,
    ) -> AuthorizedActivation:
        """Authorize rollback, then persist evidence and append under one local transaction."""
        generation = self._load_target(generation_id)
        evidence = self._obtain_evidence(
            deployment,
            generation,
            authorization_action="rollback",
            authorized_state_sequence=expected_previous_sequence,
        )
        event = self._structural_registry.rollback_authorized(
            deployment,
            generation_id=generation.generation_id,
            expected_previous_sequence=expected_previous_sequence,
            evidence_bundle_sha256=evidence.bundle_sha256(),
            evidence_writer=self._evidence_writer(evidence),
        )
        return AuthorizedActivation(event=event, generation=generation, evidence=evidence)

    def recover_active(self, deployment: DeploymentIdentity) -> AuthorizedRecoveredActivation | None:
        """Re-admit recovery, then persist that fresh evidence under a locked state recheck."""
        first = self._structural_registry.recover_active(deployment)
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
        second = self._structural_registry.recover_active_authorized(
            deployment,
            expected_activation_sequence=first.event.activation_sequence,
            expected_generation_id=first.generation.generation_id,
            evidence_bundle_sha256=evidence.bundle_sha256(),
            evidence_writer=self._evidence_writer(evidence),
        )
        evidence.validate_for(
            deployment_id=deployment.deployment_id,
            environment_id=deployment.environment_id,
            generation=second.generation,
            authorization_action="recover",
            authorized_state_sequence=second.event.activation_sequence,
            now_unix_ms=self.clock_unix_ms(),
        )
        return AuthorizedRecoveredActivation(
            event=second.event,
            generation=second.generation,
            evidence=evidence,
        )
