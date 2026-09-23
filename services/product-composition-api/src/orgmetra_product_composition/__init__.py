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
from .asgi_transport import (
    CanonicalHttpRequest,
    CompositionTransportError,
    canonical_request_from_asgi_scope,
    current_route_id_for_asgi_scope,
)
from .postgres_registry import PostgresGenerationRegistry
from .registry import (
    CompositionRegistryError,
    GenerationRecordSet,
    OwnerReleaseRecord,
    RouteMethodRecord,
    RouteRecord,
)
from .request_routing import (
    CompositionMethodNotAllowedError,
    CompositionRequestError,
    CompositionRouteNotFoundError,
    CompositionRouteUnavailableError,
    CompositionRoutingError,
    current_route_id_for_request,
)
from .serving_snapshot import (
    RecoveredRouteSnapshot,
    current_route_ids_for_snapshot,
    recover_active_route_snapshot,
)

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
    "CanonicalHttpRequest",
    "CompositionContractError",
    "CompositionGeneration",
    "CompositionMethodNotAllowedError",
    "CompositionRegistryError",
    "CompositionRequestError",
    "CompositionRoute",
    "CompositionRouteNotFoundError",
    "CompositionRouteUnavailableError",
    "CompositionRoutingError",
    "CompositionTransportError",
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
    "canonical_request_from_asgi_scope",
    "configuration_sha256",
    "current_route_id_for_asgi_scope",
    "current_route_id_for_request",
    "current_route_ids_for_snapshot",
    "recover_active_route_snapshot",
]
