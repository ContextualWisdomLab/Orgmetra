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


def organization_unit_scope_code(organization_unit_id: UUID) -> str:
    """Return the exact Keyverse scope for one employing organization unit."""
    if not isinstance(organization_unit_id, UUID) or organization_unit_id.int in (0, _MAX_UUID_INT):
        raise ValueError("organization_unit_id must be an operational UUID")
    return f"orgmetra.people.write.organization_unit_{organization_unit_id.hex}"


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
    required_target_scope_code: str | None = None,
) -> AuthorizationDecision:
    """Authorize one exact HR resource without duplicating Keyverse policy logic.

    The People API contributes only request-edge identity/scope attributes and the
    resolved target. The integrated Orgmetra adapter remains the single owner of
    tenant/resource/purpose/operation/scope/field evaluation and denial evidence.
    ``required_target_scope_code`` narrows a valid operation to one exact target.
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
        required_target_scope_code=required_target_scope_code,
    )
    return require_purpose_bound_access(request=request, policy=policy)
