"""Delegate People API field access to Orgmetra's integrated policy evaluator."""

from __future__ import annotations

from uuid import UUID

from orgmetra_keyverse_adapter import (
    AuthorizationDecision,
    PurposeBoundAccessPolicy,
    PurposeBoundAccessRequest,
    require_purpose_bound_access,
)

from orgmetra_people_api.auth import AuthenticatedPrincipal

_MAX_UUID_INT = (1 << 128) - 1


def _principal_authority(principal: object) -> tuple[UUID, str, frozenset[str]]:
    """Detach exact authenticated evidence before constructing a policy request."""
    if type(principal) is not AuthenticatedPrincipal:
        raise TypeError("principal must be an exact AuthenticatedPrincipal")
    tenant_record_id = principal.tenant_record_id
    if type(tenant_record_id) is not UUID:
        raise TypeError("principal tenant_record_id must be an exact UUID")
    tenant_identity = tenant_record_id.int
    if type(tenant_identity) is not int or not (0 < tenant_identity < _MAX_UUID_INT):
        raise TypeError("principal tenant_record_id must contain an operational integer UUID payload")
    actor_reference = principal.actor_reference
    if type(actor_reference) is not str:
        raise TypeError("principal actor_reference must be exact built-in text")
    granted_scope_codes = principal.granted_scope_codes
    if type(granted_scope_codes) is not frozenset or not granted_scope_codes:
        raise TypeError("principal granted_scope_codes must be an exact non-empty frozenset")
    if any(type(scope_code) is not str for scope_code in granted_scope_codes):
        raise TypeError("principal granted_scope_codes must contain exact built-in text")
    return (
        UUID(int=tenant_identity),
        actor_reference,
        frozenset(tuple(granted_scope_codes)),
    )


def authorize_resource_fields(
    *,
    principal: AuthenticatedPrincipal,
    tenant_record_id: UUID,
    resource_tenant_record_id: UUID,
    resource_reference: str,
    purpose_code: str,
    operation_code: str,
    resource_kind: str,
    requested_fields: frozenset[str],
    policy: PurposeBoundAccessPolicy,
) -> AuthorizationDecision:
    """Authorize one exact HR resource without duplicating Keyverse policy logic.

    The People API contributes only request-edge identity/scope attributes and the
    resolved target. The integrated Orgmetra adapter remains the single owner of
    tenant/resource/purpose/operation/scope/field evaluation and denial evidence.
    Authenticated principal evidence is reduced here as well as at HTTP edges so
    direct application callers cannot bypass the same inert-evidence boundary.
    """
    actor_tenant_record_id, actor_reference, granted_scope_codes = _principal_authority(principal)
    request = PurposeBoundAccessRequest(
        tenant_record_id=tenant_record_id,
        actor_tenant_record_id=actor_tenant_record_id,
        resource_tenant_record_id=resource_tenant_record_id,
        actor_reference=actor_reference,
        resource_reference=resource_reference,
        purpose_code=purpose_code,
        operation_code=operation_code,
        resource_kind=resource_kind,
        requested_fields=requested_fields,
        granted_scope_codes=granted_scope_codes,
    )
    return require_purpose_bound_access(request=request, policy=policy)