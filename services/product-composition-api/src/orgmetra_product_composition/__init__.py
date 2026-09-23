"""Orgmetra product-composition admission and durable registry contracts."""

from .activation import (
    ActivationConflictError,
    ActivationEvent,
    ActivationRegistryError,
    DeploymentIdentity,
    RecoveredActivation,
)
from .activation_authorization import (
    ActivationAdmissionEvidence,
    ActivationAuthorizationError,
    AuthorizationAction,
    AuthorizedActivation,
    AuthorizedRecoveredActivation,
    OwnerOperationObservation,
    ReleasedAuthorityEvidence,
)
from .activation_runtime_integrity import AuthorizedPostgresActivationRegistry
from .admission import (
    AdmissionReceipt,
    CompositionContractError,
    CompositionGeneration,
    CompositionRoute,
    OwnerApiRelease,
    admit_generation,
    configuration_sha256,
)
from .postgres_registry import PostgresGenerationRegistry
from .registry import (
    CompositionRegistryError,
    GenerationRecordSet,
    OwnerReleaseRecord,
    RouteMethodRecord,
    RouteRecord,
)
from .serving_snapshot import RecoveredRouteSnapshot, recover_active_route_snapshot

__all__ = [
    "ActivationAdmissionEvidence",
    "ActivationAuthorizationError",
    "ActivationConflictError",
    "ActivationEvent",
    "ActivationRegistryError",
    "AdmissionReceipt",
    "AuthorizationAction",
    "AuthorizedActivation",
    "AuthorizedPostgresActivationRegistry",
    "AuthorizedRecoveredActivation",
    "CompositionContractError",
    "CompositionGeneration",
    "CompositionRegistryError",
    "CompositionRoute",
    "DeploymentIdentity",
    "GenerationRecordSet",
    "OwnerApiRelease",
    "OwnerOperationObservation",
    "OwnerReleaseRecord",
    "PostgresGenerationRegistry",
    "RecoveredActivation",
    "RecoveredRouteSnapshot",
    "ReleasedAuthorityEvidence",
    "RouteMethodRecord",
    "RouteRecord",
    "admit_generation",
    "configuration_sha256",
    "recover_active_route_snapshot",
]
