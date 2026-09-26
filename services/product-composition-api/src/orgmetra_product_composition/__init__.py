"""Orgmetra product-composition admission and durable registry contracts."""

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
    "AdmissionReceipt",
    "CompositionContractError",
    "CompositionGeneration",
    "CompositionRegistryError",
    "CompositionRoute",
    "GenerationRecordSet",
    "OwnerApiRelease",
    "OwnerReleaseRecord",
    "PostgresGenerationRegistry",
    "RouteMethodRecord",
    "RouteRecord",
    "admit_generation",
    "configuration_sha256",
]
