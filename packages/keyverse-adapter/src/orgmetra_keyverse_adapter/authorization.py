"""Fail-closed purpose-bound authorization at the Orgmetra Keyverse boundary.

The adapter consumes only already-authenticated Keyverse identity attributes and
Orgmetra-owned policy data. It never stores credentials and never asks Keyverse
to make an Orgmetra employment-policy decision. Authorization follows the NIST
SP 800-162 ABAC shape: subject/context, object, requested operation, and policy
attributes must all match. Purpose is one policy attribute, never a substitute
for the operation-specific token scope.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from uuid import UUID

_MAX_UUID_INT = (1 << 128) - 1
_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_RESOURCE_KIND_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_SCOPE_PATTERN = re.compile(r"^orgmetra(?:\.[a-z][a-z0-9_]*){2,}$")
_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$")
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")

_DENIAL_NEXT_ACTION = {
    "tenant_scope_mismatch": (
        "Re-resolve the actor, request context, resource, and policy in one tenant before retrying."
    ),
    "purpose_not_allowed": (
        "Use an approved purpose for this policy or obtain a separately governed policy decision."
    ),
    "operation_not_allowed": (
        "Use the operation authorized by this policy or obtain a narrower policy for the requested action."
    ),
    "resource_not_allowed": "Resolve the policy for the requested resource kind before retrying.",
    "required_scope_missing": (
        "Obtain the operation-specific Keyverse scope; a purpose header alone cannot authorize access."
    ),
    "field_not_allowed": (
        "Request only fields allowed for this purpose or obtain a separately reviewed field policy."
    ),
}


def _validate_uuid(field_name: str, value: object) -> None:
    """Require a real UUID and reject protocol-reserved Nil/Max sentinels."""
    if not isinstance(value, UUID):
        raise ValueError(f"{field_name} must be a UUID.")
    if value.int in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must not use a reserved UUID sentinel.")


def _validate_code(field_name: str, value: object) -> None:
    """Require an explicit lower snake_case policy or request code."""
    if not isinstance(value, str) or _CODE_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a lower snake_case code.")


def _validate_resource_kind(value: object) -> None:
    """Require a descriptive two-or-more-word lower snake_case resource kind."""
    if not isinstance(value, str) or _RESOURCE_KIND_PATTERN.fullmatch(value) is None:
        raise ValueError("resource_kind must contain two or more lower snake_case words.")


def _validate_scope(field_name: str, value: object) -> None:
    """Require one explicit Orgmetra operation scope rather than wildcards."""
    if not isinstance(value, str) or _SCOPE_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be an explicit orgmetra.<context>.<operation> scope.")


def _validate_reference(
    field_name: str,
    value: object,
    *,
    expected_namespace: str | None = None,
) -> None:
    """Require an opaque audit reference and optionally bind it to one resource kind."""
    if not isinstance(value, str) or _REFERENCE_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a namespaced opaque reference.")
    if expected_namespace is not None and value.partition(":")[0] != expected_namespace:
        raise ValueError(f"{field_name} namespace must match resource_kind.")


def _validate_version(value: object) -> None:
    """Require an immutable, whitespace-free policy version token."""
    if not isinstance(value, str) or _VERSION_PATTERN.fullmatch(value) is None:
        raise ValueError("policy_version_code must be a whitespace-free version token.")


def _validate_field_set(field_name: str, values: object) -> None:
    """Require an immutable, non-empty set of explicit lower snake_case fields."""
    if not isinstance(values, frozenset):
        raise ValueError(f"{field_name} must be a frozenset.")
    if not values:
        raise ValueError(f"{field_name} must not be empty.")
    if any(not isinstance(value, str) or _CODE_PATTERN.fullmatch(value) is None for value in values):
        raise ValueError(f"{field_name} must contain only explicit lower snake_case field names.")


def _validate_scope_set(values: object) -> None:
    """Require immutable, non-empty, explicit token scopes from the authenticated principal."""
    if not isinstance(values, frozenset):
        raise ValueError("granted_scope_codes must be a frozenset.")
    if not values:
        raise ValueError("granted_scope_codes must not be empty.")
    if any(not isinstance(value, str) or _SCOPE_PATTERN.fullmatch(value) is None for value in values):
        raise ValueError("granted_scope_codes must contain only explicit Orgmetra scopes.")


@dataclass(frozen=True, slots=True)
class PurposeBoundAccessPolicy:
    """One tenant-local field policy for one purpose, resource, and operation.

    A policy intentionally has no wildcard form. Separate purposes, operations,
    or resources require separate reviewed policy records so a broad token cannot
    silently widen access to necessary HR PII.
    """

    tenant_record_id: UUID
    policy_version_code: str
    resource_kind: str
    purpose_code: str
    operation_code: str
    required_scope_code: str
    permitted_fields: frozenset[str]

    def __post_init__(self) -> None:
        """Reject ambiguous or mutable policy attributes before evaluation."""
        _validate_uuid("tenant_record_id", self.tenant_record_id)
        _validate_version(self.policy_version_code)
        _validate_resource_kind(self.resource_kind)
        _validate_code("purpose_code", self.purpose_code)
        _validate_code("operation_code", self.operation_code)
        _validate_scope("required_scope_code", self.required_scope_code)
        _validate_field_set("permitted_fields", self.permitted_fields)


@dataclass(frozen=True, slots=True)
class PurposeBoundAccessRequest:
    """PII access attributes resolved before any protected field is returned.

    ``actor_tenant_record_id`` comes from the authenticated identity binding,
    ``tenant_record_id`` is the active Orgmetra request context, and
    ``resource_tenant_record_id`` comes from the target record identity. The
    opaque ``resource_reference`` identifies that exact target for audit
    correlation without copying its PII. An optional target scope narrows the
    operation to one exact organization or other governed target. All tenant
    identifiers must match the policy tenant. Only field names are carried here;
    field values remain behind the authoritative data boundary until access is
    allowed.
    """

    tenant_record_id: UUID
    actor_tenant_record_id: UUID
    resource_tenant_record_id: UUID
    actor_reference: str
    resource_reference: str
    purpose_code: str
    operation_code: str
    resource_kind: str
    requested_fields: frozenset[str]
    granted_scope_codes: frozenset[str]
    required_target_scope_code: str | None = None

    def __post_init__(self) -> None:
        """Reject untrusted identity, target, tenant, purpose, field, or scope attributes."""
        _validate_uuid("tenant_record_id", self.tenant_record_id)
        _validate_uuid("actor_tenant_record_id", self.actor_tenant_record_id)
        _validate_uuid("resource_tenant_record_id", self.resource_tenant_record_id)
        _validate_reference("actor_reference", self.actor_reference)
        _validate_resource_kind(self.resource_kind)
        _validate_reference(
            "resource_reference",
            self.resource_reference,
            expected_namespace=self.resource_kind,
        )
        _validate_code("purpose_code", self.purpose_code)
        _validate_code("operation_code", self.operation_code)
        _validate_field_set("requested_fields", self.requested_fields)
        _validate_scope_set(self.granted_scope_codes)
        if self.required_target_scope_code is not None:
            _validate_scope("required_target_scope_code", self.required_target_scope_code)


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    """PII-minimized authorization evidence safe to bind into an audit event."""

    allowed: bool
    tenant_record_id: UUID
    actor_reference: str
    resource_reference: str
    policy_version_code: str
    purpose_code: str
    operation_code: str
    resource_kind: str
    requested_fields: frozenset[str]
    authorized_fields: frozenset[str]
    reason_code: str
    next_action: str
    required_target_scope_code: str | None = None

    def __post_init__(self) -> None:
        """Reject malformed governed-target evidence on manually constructed decisions."""
        if self.required_target_scope_code is not None:
            _validate_scope("required_target_scope_code", self.required_target_scope_code)


class AuthorizationDeniedError(PermissionError):
    """A purpose-bound policy denied access and tells the caller how to recover safely."""

    def __init__(self, decision: AuthorizationDecision) -> None:
        """Preserve bounded denial metadata without including protected field values."""
        super().__init__(decision.reason_code)
        self.reason_code = decision.reason_code
        self.next_action = decision.next_action
        self.decision = decision


def _decision(
    *,
    request: PurposeBoundAccessRequest,
    policy: PurposeBoundAccessPolicy,
    allowed: bool,
    reason_code: str,
    next_action_override: str | None = None,
) -> AuthorizationDecision:
    """Build one immutable allow/deny record without copying protected values."""
    authorized_fields = request.requested_fields if allowed else frozenset()
    next_action = (
        "Continue with only the authorized fields."
        if allowed
        else (
            next_action_override
            if next_action_override is not None
            else _DENIAL_NEXT_ACTION[reason_code]
        )
    )
    return AuthorizationDecision(
        allowed=allowed,
        tenant_record_id=request.tenant_record_id,
        actor_reference=request.actor_reference,
        resource_reference=request.resource_reference,
        policy_version_code=policy.policy_version_code,
        purpose_code=request.purpose_code,
        operation_code=request.operation_code,
        resource_kind=request.resource_kind,
        requested_fields=request.requested_fields,
        authorized_fields=authorized_fields,
        reason_code=reason_code,
        next_action=next_action,
        required_target_scope_code=request.required_target_scope_code,
    )


def evaluate_purpose_bound_access(
    *,
    request: PurposeBoundAccessRequest,
    policy: PurposeBoundAccessPolicy,
) -> AuthorizationDecision:
    """Evaluate tenant, resource, purpose, operation, scope, and field attributes.

    The order deliberately checks tenant isolation before policy detail and then
    requires every narrowing attribute. Possessing a broad identity or a valid
    purpose header is insufficient when the operation scope or requested field
    set is not explicitly authorized.
    """
    if (
        request.tenant_record_id != policy.tenant_record_id
        or request.actor_tenant_record_id != policy.tenant_record_id
        or request.resource_tenant_record_id != policy.tenant_record_id
    ):
        return _decision(
            request=request,
            policy=policy,
            allowed=False,
            reason_code="tenant_scope_mismatch",
        )
    if request.resource_kind != policy.resource_kind:
        return _decision(
            request=request,
            policy=policy,
            allowed=False,
            reason_code="resource_not_allowed",
        )
    if request.purpose_code != policy.purpose_code:
        return _decision(
            request=request,
            policy=policy,
            allowed=False,
            reason_code="purpose_not_allowed",
        )
    if request.operation_code != policy.operation_code:
        return _decision(
            request=request,
            policy=policy,
            allowed=False,
            reason_code="operation_not_allowed",
        )
    if policy.required_scope_code not in request.granted_scope_codes:
        return _decision(
            request=request,
            policy=policy,
            allowed=False,
            reason_code="required_scope_missing",
        )
    if (
        request.required_target_scope_code is not None
        and request.required_target_scope_code not in request.granted_scope_codes
    ):
        return _decision(
            request=request,
            policy=policy,
            allowed=False,
            reason_code="required_scope_missing",
            next_action_override=(
                "Obtain the exact Keyverse scope for the governed target before retrying; "
                "the operation scope alone cannot authorize that target."
            ),
        )
    if not request.requested_fields.issubset(policy.permitted_fields):
        return _decision(
            request=request,
            policy=policy,
            allowed=False,
            reason_code="field_not_allowed",
        )
    return _decision(
        request=request,
        policy=policy,
        allowed=True,
        reason_code="access_permitted",
    )


def require_purpose_bound_access(
    *,
    request: PurposeBoundAccessRequest,
    policy: PurposeBoundAccessPolicy,
) -> AuthorizationDecision:
    """Return the allow decision or raise an actionable, PII-minimized denial."""
    decision = evaluate_purpose_bound_access(request=request, policy=policy)
    if not decision.allowed:
        raise AuthorizationDeniedError(decision)
    return decision
