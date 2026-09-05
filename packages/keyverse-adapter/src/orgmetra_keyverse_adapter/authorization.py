"""Fail-closed purpose-bound authorization at the Orgmetra Keyverse boundary.

The adapter consumes authenticated Keyverse identity/scope attributes and an
Orgmetra-owned policy supplied by the trusted service composition boundary. The
Python value objects below validate and detach authorization data; they are not
unforgeable capabilities against arbitrary code already executing in the same
interpreter. Same-process arbitrary code execution is a service compromise and
belongs to deployment/workload isolation controls, not object-constructor tricks.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import NamedTuple
from uuid import UUID

_MAX_UUID_INT = (1 << 128) - 1
_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_RESOURCE_KIND_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_SCOPE_PATTERN = re.compile(r"^orgmetra(?:\.[a-z][a-z0-9_]*){2,}$")
_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$")
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")

_ALLOW_NEXT_ACTION = "Continue with only the authorized fields."
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
    """Require an exact UUID and reject protocol-reserved Nil/Max sentinels."""
    if type(value) is not UUID:
        raise ValueError(f"{field_name} must be a UUID.")
    if value.int in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must not use a reserved UUID sentinel.")


def _validated_uuid_int(field_name: str, value: object) -> int:
    """Validate and detach an exact UUID into one immutable integer snapshot."""
    _validate_uuid(field_name, value)
    value_int = value.int
    if type(value_int) is not int or not 0 <= value_int <= _MAX_UUID_INT:
        raise ValueError(f"{field_name} must contain a valid UUID integer.")
    return value_int


def _validate_code(field_name: str, value: object) -> None:
    """Require an exact built-in lower snake_case policy or request code."""
    if type(value) is not str or _CODE_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a lower snake_case code.")


def _validate_resource_kind(value: object) -> None:
    """Require an exact built-in descriptive lower snake_case resource kind."""
    if type(value) is not str or _RESOURCE_KIND_PATTERN.fullmatch(value) is None:
        raise ValueError("resource_kind must contain two or more lower snake_case words.")


def _validate_scope(field_name: str, value: object) -> None:
    """Require one exact built-in Orgmetra operation scope rather than wildcards."""
    if type(value) is not str or _SCOPE_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be an explicit orgmetra.<context>.<operation> scope.")


def _validate_reference(
    field_name: str,
    value: object,
    *,
    expected_namespace: str | None = None,
) -> None:
    """Require an exact built-in opaque reference and optionally bind its namespace."""
    if type(value) is not str or _REFERENCE_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a namespaced opaque reference.")
    if expected_namespace is not None and value.partition(":")[0] != expected_namespace:
        raise ValueError(f"{field_name} namespace must match resource_kind.")


def _validate_version(value: object) -> None:
    """Require an exact built-in immutable, whitespace-free policy version token."""
    if type(value) is not str or _VERSION_PATTERN.fullmatch(value) is None:
        raise ValueError("policy_version_code must be a whitespace-free version token.")


def _validate_field_set(field_name: str, values: object) -> None:
    """Require an exact immutable non-empty set of exact built-in field codes."""
    if type(values) is not frozenset:
        raise ValueError(f"{field_name} must be a frozenset.")
    if not values:
        raise ValueError(f"{field_name} must not be empty.")
    if any(type(value) is not str or _CODE_PATTERN.fullmatch(value) is None for value in values):
        raise ValueError(f"{field_name} must contain only explicit lower snake_case field names.")


def _validate_authorized_field_set(values: object) -> None:
    """Require an exact immutable authorized-field set while allowing an empty deny result."""
    if type(values) is not frozenset:
        raise ValueError("authorized_fields must be a frozenset.")
    if any(type(value) is not str or _CODE_PATTERN.fullmatch(value) is None for value in values):
        raise ValueError("authorized_fields must contain only explicit lower snake_case field names.")


def _validate_scope_set(values: object) -> None:
    """Require an exact immutable non-empty set of authenticated Orgmetra scopes."""
    if type(values) is not frozenset:
        raise ValueError("granted_scope_codes must be a frozenset.")
    if not values:
        raise ValueError("granted_scope_codes must not be empty.")
    if any(type(value) is not str or _SCOPE_PATTERN.fullmatch(value) is None for value in values):
        raise ValueError("granted_scope_codes must contain only explicit Orgmetra scopes.")


class _PolicySnapshot(NamedTuple):
    """Validated detached values for one trusted-source policy at evaluation time."""

    tenant_record_id_int: int
    policy_version_code: str
    resource_kind: str
    purpose_code: str
    operation_code: str
    required_scope_code: str
    permitted_fields: frozenset[str]


class _RequestSnapshot(NamedTuple):
    """Validated detached request attributes at evaluation time."""

    tenant_record_id_int: int
    actor_tenant_record_id_int: int
    resource_tenant_record_id_int: int
    actor_reference: str
    resource_reference: str
    purpose_code: str
    operation_code: str
    resource_kind: str
    requested_fields: frozenset[str]
    granted_scope_codes: frozenset[str]


class _DecisionSnapshot(NamedTuple):
    """Validated PII-minimized decision values at a consumer boundary."""

    allowed: bool
    tenant_record_id_int: int
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


@dataclass(frozen=True, slots=True)
class PurposeBoundAccessPolicy:
    """One trusted-composition policy value for one tenant/resource/operation.

    Object construction is validation, not policy issuance. Production callers
    must obtain this value from the Orgmetra-controlled composition/policy source;
    request payloads, LLM outputs, plugins, and remote callers are not policy
    authorities.
    """

    tenant_record_id: UUID
    policy_version_code: str
    resource_kind: str
    purpose_code: str
    operation_code: str
    required_scope_code: str
    permitted_fields: frozenset[str]

    def __post_init__(self) -> None:
        """Validate policy data and detach the caller-owned UUID instance."""
        tenant_int = _validated_uuid_int("tenant_record_id", self.tenant_record_id)
        _validate_version(self.policy_version_code)
        _validate_resource_kind(self.resource_kind)
        _validate_code("purpose_code", self.purpose_code)
        _validate_code("operation_code", self.operation_code)
        _validate_scope("required_scope_code", self.required_scope_code)
        _validate_field_set("permitted_fields", self.permitted_fields)
        object.__setattr__(self, "tenant_record_id", UUID(int=tenant_int))


@dataclass(frozen=True, slots=True)
class PurposeBoundAccessRequest:
    """Authorization attributes resolved from the request and authenticated identity."""

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

    def __post_init__(self) -> None:
        """Validate input attributes and detach caller-owned UUID instances."""
        tenant_int = _validated_uuid_int("tenant_record_id", self.tenant_record_id)
        actor_tenant_int = _validated_uuid_int(
            "actor_tenant_record_id",
            self.actor_tenant_record_id,
        )
        resource_tenant_int = _validated_uuid_int(
            "resource_tenant_record_id",
            self.resource_tenant_record_id,
        )
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
        object.__setattr__(self, "tenant_record_id", UUID(int=tenant_int))
        object.__setattr__(self, "actor_tenant_record_id", UUID(int=actor_tenant_int))
        object.__setattr__(self, "resource_tenant_record_id", UUID(int=resource_tenant_int))


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    """PII-minimized authorization decision data produced inside the service TCB.

    The type rejects dynamic subclasses and validates verdict/evidence coherence,
    but it is not an unforgeable capability against arbitrary code already running
    inside the service process. Persistence boundaries must treat same-process code
    as trusted and still revalidate decision semantics before durable use.
    """

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

    def __post_init__(self) -> None:
        """Validate decision coherence and detach the tenant UUID instance."""
        snapshot = _validated_decision_snapshot(
            allowed=self.allowed,
            tenant_record_id=self.tenant_record_id,
            actor_reference=self.actor_reference,
            resource_reference=self.resource_reference,
            policy_version_code=self.policy_version_code,
            purpose_code=self.purpose_code,
            operation_code=self.operation_code,
            resource_kind=self.resource_kind,
            requested_fields=self.requested_fields,
            authorized_fields=self.authorized_fields,
            reason_code=self.reason_code,
            next_action=self.next_action,
        )
        object.__setattr__(self, "tenant_record_id", UUID(int=snapshot.tenant_record_id_int))

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Prevent caller-defined decision subclasses from overriding field behavior."""
        del kwargs
        raise TypeError("AuthorizationDecision must not be subclassed")


class AuthorizationDeniedError(PermissionError):
    """A purpose-bound policy denied access and tells the caller how to recover safely."""

    def __init__(self, decision: AuthorizationDecision) -> None:
        """Preserve bounded denial metadata without including protected field values."""
        super().__init__(decision.reason_code)
        self.reason_code = decision.reason_code
        self.next_action = decision.next_action
        self.decision = decision


def _validated_policy_snapshot(policy: PurposeBoundAccessPolicy) -> _PolicySnapshot:
    """Revalidate and detach one policy immediately before evaluation."""
    tenant_int = _validated_uuid_int("tenant_record_id", policy.tenant_record_id)
    _validate_version(policy.policy_version_code)
    _validate_resource_kind(policy.resource_kind)
    _validate_code("purpose_code", policy.purpose_code)
    _validate_code("operation_code", policy.operation_code)
    _validate_scope("required_scope_code", policy.required_scope_code)
    _validate_field_set("permitted_fields", policy.permitted_fields)
    return _PolicySnapshot(
        tenant_int,
        policy.policy_version_code,
        policy.resource_kind,
        policy.purpose_code,
        policy.operation_code,
        policy.required_scope_code,
        policy.permitted_fields,
    )


def _validated_request_snapshot(request: PurposeBoundAccessRequest) -> _RequestSnapshot:
    """Revalidate and detach request data immediately before evaluation."""
    tenant_int = _validated_uuid_int("tenant_record_id", request.tenant_record_id)
    actor_tenant_int = _validated_uuid_int(
        "actor_tenant_record_id",
        request.actor_tenant_record_id,
    )
    resource_tenant_int = _validated_uuid_int(
        "resource_tenant_record_id",
        request.resource_tenant_record_id,
    )
    _validate_reference("actor_reference", request.actor_reference)
    _validate_resource_kind(request.resource_kind)
    _validate_reference(
        "resource_reference",
        request.resource_reference,
        expected_namespace=request.resource_kind,
    )
    _validate_code("purpose_code", request.purpose_code)
    _validate_code("operation_code", request.operation_code)
    _validate_field_set("requested_fields", request.requested_fields)
    _validate_scope_set(request.granted_scope_codes)
    return _RequestSnapshot(
        tenant_int,
        actor_tenant_int,
        resource_tenant_int,
        request.actor_reference,
        request.resource_reference,
        request.purpose_code,
        request.operation_code,
        request.resource_kind,
        request.requested_fields,
        request.granted_scope_codes,
    )


def _validated_decision_snapshot(
    *,
    allowed: object,
    tenant_record_id: object,
    actor_reference: object,
    resource_reference: object,
    policy_version_code: object,
    purpose_code: object,
    operation_code: object,
    resource_kind: object,
    requested_fields: object,
    authorized_fields: object,
    reason_code: object,
    next_action: object,
) -> _DecisionSnapshot:
    """Validate PII-minimized decision values without conferring policy authority."""
    if type(allowed) is not bool:
        raise ValueError("allowed must be a boolean.")
    tenant_int = _validated_uuid_int("tenant_record_id", tenant_record_id)
    _validate_reference("actor_reference", actor_reference)
    _validate_resource_kind(resource_kind)
    _validate_reference(
        "resource_reference",
        resource_reference,
        expected_namespace=resource_kind,
    )
    _validate_version(policy_version_code)
    _validate_code("purpose_code", purpose_code)
    _validate_code("operation_code", operation_code)
    _validate_field_set("requested_fields", requested_fields)
    _validate_authorized_field_set(authorized_fields)
    _validate_code("reason_code", reason_code)
    if type(next_action) is not str or not next_action.strip() or len(next_action) > 500:
        raise ValueError("next_action must be a non-blank string of at most 500 characters.")
    if allowed and authorized_fields != requested_fields:
        raise ValueError("allow decision must authorize exactly the requested fields.")
    if not allowed and authorized_fields:
        raise ValueError("deny decision must not authorize fields.")
    if allowed:
        if reason_code != "access_permitted":
            raise ValueError("allow decision must use access_permitted reason.")
        if next_action != _ALLOW_NEXT_ACTION:
            raise ValueError("allow decision must use the canonical next action.")
    else:
        if reason_code not in _DENIAL_NEXT_ACTION:
            raise ValueError("deny decision must use a known denial reason.")
        if next_action != _DENIAL_NEXT_ACTION[reason_code]:
            raise ValueError("deny decision must use the canonical next action.")
    return _DecisionSnapshot(
        allowed,
        tenant_int,
        actor_reference,
        resource_reference,
        policy_version_code,
        purpose_code,
        operation_code,
        resource_kind,
        requested_fields,
        authorized_fields,
        reason_code,
        next_action,
    )


def validate_authorization_decision(decision: AuthorizationDecision) -> _DecisionSnapshot:
    """Revalidate exact decision data before a same-process durable consumer uses it."""
    if type(decision) is not AuthorizationDecision:
        raise TypeError("decision must be an AuthorizationDecision")
    return _validated_decision_snapshot(
        allowed=decision.allowed,
        tenant_record_id=decision.tenant_record_id,
        actor_reference=decision.actor_reference,
        resource_reference=decision.resource_reference,
        policy_version_code=decision.policy_version_code,
        purpose_code=decision.purpose_code,
        operation_code=decision.operation_code,
        resource_kind=decision.resource_kind,
        requested_fields=decision.requested_fields,
        authorized_fields=decision.authorized_fields,
        reason_code=decision.reason_code,
        next_action=decision.next_action,
    )


def _decision(
    *,
    request: _RequestSnapshot,
    policy: _PolicySnapshot,
    allowed: bool,
    reason_code: str,
) -> AuthorizationDecision:
    """Build one validated decision from the current evaluation snapshots."""
    authorized_fields = request.requested_fields if allowed else frozenset()
    next_action = _ALLOW_NEXT_ACTION if allowed else _DENIAL_NEXT_ACTION[reason_code]
    return AuthorizationDecision(
        allowed=allowed,
        tenant_record_id=UUID(int=request.tenant_record_id_int),
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
    )


def evaluate_purpose_bound_access(
    *,
    request: PurposeBoundAccessRequest,
    policy: PurposeBoundAccessPolicy,
) -> AuthorizationDecision:
    """Evaluate trusted-source policy against authenticated/request attributes.

    ``policy`` must come from the service's trusted Orgmetra policy composition
    boundary. The evaluator deliberately does not attempt to prove that arbitrary
    Python code in the same interpreter is trustworthy; it revalidates current
    values and defends the data boundary exposed to remote/untrusted inputs.
    """
    if type(request) is not PurposeBoundAccessRequest:
        raise TypeError("request must be a PurposeBoundAccessRequest")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be a PurposeBoundAccessPolicy")

    request_snapshot = _validated_request_snapshot(request)
    policy_snapshot = _validated_policy_snapshot(policy)

    if (
        request_snapshot.tenant_record_id_int != policy_snapshot.tenant_record_id_int
        or request_snapshot.actor_tenant_record_id_int != policy_snapshot.tenant_record_id_int
        or request_snapshot.resource_tenant_record_id_int != policy_snapshot.tenant_record_id_int
    ):
        return _decision(
            request=request_snapshot,
            policy=policy_snapshot,
            allowed=False,
            reason_code="tenant_scope_mismatch",
        )
    if request_snapshot.resource_kind != policy_snapshot.resource_kind:
        return _decision(
            request=request_snapshot,
            policy=policy_snapshot,
            allowed=False,
            reason_code="resource_not_allowed",
        )
    if request_snapshot.purpose_code != policy_snapshot.purpose_code:
        return _decision(
            request=request_snapshot,
            policy=policy_snapshot,
            allowed=False,
            reason_code="purpose_not_allowed",
        )
    if request_snapshot.operation_code != policy_snapshot.operation_code:
        return _decision(
            request=request_snapshot,
            policy=policy_snapshot,
            allowed=False,
            reason_code="operation_not_allowed",
        )
    if policy_snapshot.required_scope_code not in request_snapshot.granted_scope_codes:
        return _decision(
            request=request_snapshot,
            policy=policy_snapshot,
            allowed=False,
            reason_code="required_scope_missing",
        )
    if not request_snapshot.requested_fields.issubset(policy_snapshot.permitted_fields):
        return _decision(
            request=request_snapshot,
            policy=policy_snapshot,
            allowed=False,
            reason_code="field_not_allowed",
        )
    return _decision(
        request=request_snapshot,
        policy=policy_snapshot,
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
