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
    """
    request = PurposeBoundAccessRequest(
        tenant_record_id=tenant_record_id,
        actor_tenant_record_id=principal.tenant_record_id,
        resource_tenant_record_id=resource_tenant_record_id,
        actor_reference=principal.actor_reference,
        resource_reference=resource_reference,
        purpose_code=purpose_code,
        operation_code=operation_code,
        resource_kind=resource_kind,
        requested_fields=requested_fields,
        granted_scope_codes=principal.granted_scope_codes,
    )
    return require_purpose_bound_access(request=request, policy=policy)
