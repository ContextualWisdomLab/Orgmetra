"""Orgmetra product-composition admission and durable registry contracts."""

from .activation import (
    ActivationConflictError,
    ActivationEvent,
    ActivationRegistryError,
    DeploymentIdentity,
    PostgresActivationRegistry,
    RecoveredActivation,
)
from .activation_authorization import (
    ActivationAdmissionEvidence,
    ActivationAuthorizationError,
    AuthorizedActivation,
    AuthorizedPostgresActivationRegistry,
    AuthorizedRecoveredActivation,
    OwnerOperationObservation,
    ReleasedAuthorityEvidence,
)
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

__all__ = [
    "ActivationAdmissionEvidence",
    "ActivationAuthorizationError",
    "ActivationConflictError",
    "ActivationEvent",
    "ActivationRegistryError",
    "AdmissionReceipt",
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
    "PostgresActivationRegistry",
    "PostgresGenerationRegistry",
    "RecoveredActivation",
    "ReleasedAuthorityEvidence",
    "RouteMethodRecord",
    "RouteRecord",
    "admit_generation",
    "configuration_sha256",
]
