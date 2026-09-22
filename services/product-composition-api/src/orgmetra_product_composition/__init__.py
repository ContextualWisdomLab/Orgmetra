"""Orgmetra product-composition admission and durable registry contracts."""

from .activation import (
    ActivationConflictError,
    ActivationEvent,
    ActivationRegistryError,
    DeploymentIdentity,
    PostgresActivationRegistry,
    RecoveredActivation,
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
    "ActivationConflictError",
    "ActivationEvent",
    "ActivationRegistryError",
    "AdmissionReceipt",
    "CompositionContractError",
    "CompositionGeneration",
    "CompositionRegistryError",
    "CompositionRoute",
    "DeploymentIdentity",
    "GenerationRecordSet",
    "OwnerApiRelease",
    "OwnerReleaseRecord",
    "PostgresActivationRegistry",
    "PostgresGenerationRegistry",
    "RecoveredActivation",
    "RouteMethodRecord",
    "RouteRecord",
    "admit_generation",
    "configuration_sha256",
]
