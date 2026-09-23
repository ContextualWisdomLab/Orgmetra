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
from .route_availability import available_route_ids_for

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
    "ReleasedAuthorityEvidence",
    "RouteMethodRecord",
    "RouteRecord",
    "admit_generation",
    "available_route_ids_for",
    "configuration_sha256",
]
