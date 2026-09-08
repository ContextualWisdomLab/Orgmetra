"""Test support that obtains authorization evidence through the public evaluator."""

from __future__ import annotations

from uuid import UUID

from orgmetra_keyverse_adapter import (
    AuthorizationDecision,
    PurposeBoundAccessPolicy,
    PurposeBoundAccessRequest,
    evaluate_purpose_bound_access,
)


def issued_authorization(
    *,
    tenant_record_id: UUID,
    actor_reference: str,
    resource_reference: str,
    policy_version_code: str,
    purpose_code: str,
    operation_code: str,
    resource_kind: str,
    requested_fields: frozenset[str],
    required_scope_code: str,
    granted_scope_codes: frozenset[str] | None = None,
    permitted_fields: frozenset[str] | None = None,
    policy_purpose_code: str | None = None,
) -> AuthorizationDecision:
    """Return evidence produced by the same purpose-bound evaluation used in production."""
    policy = PurposeBoundAccessPolicy(
        tenant_record_id=tenant_record_id,
        policy_version_code=policy_version_code,
        resource_kind=resource_kind,
        purpose_code=policy_purpose_code or purpose_code,
        operation_code=operation_code,
        required_scope_code=required_scope_code,
        permitted_fields=permitted_fields or requested_fields,
    )
    request = PurposeBoundAccessRequest(
        tenant_record_id=tenant_record_id,
        actor_tenant_record_id=tenant_record_id,
        resource_tenant_record_id=tenant_record_id,
        actor_reference=actor_reference,
        resource_reference=resource_reference,
        purpose_code=purpose_code,
        operation_code=operation_code,
        resource_kind=resource_kind,
        requested_fields=requested_fields,
        granted_scope_codes=granted_scope_codes or frozenset({required_scope_code}),
    )
    return evaluate_purpose_bound_access(request=request, policy=policy)
