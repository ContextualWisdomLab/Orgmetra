"""Fail-closed purpose-bound authorization at the Orgmetra Keyverse boundary.

The adapter consumes only already-authenticated Keyverse identity attributes and
Orgmetra-owned policy data. It never stores credentials and never asks Keyverse
to make an Orgmetra employment-policy decision. Authorization follows the NIST
SP 800-162 ABAC shape: subject/context, object, requested operation, and policy
attributes must all match. Purpose is one policy attribute, never a substitute
for the operation-specific token scope.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import re
from typing import NamedTuple
import weakref
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
    """Require an exact immutable set of exact built-in lower snake_case fields."""
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
    """Require an exact immutable set of exact built-in authenticated token scopes."""
    if type(values) is not frozenset:
        raise ValueError("granted_scope_codes must be a frozenset.")
    if not values:
        raise ValueError("granted_scope_codes must not be empty.")
    if any(type(value) is not str or _SCOPE_PATTERN.fullmatch(value) is None for value in values):
        raise ValueError("granted_scope_codes must contain only explicit Orgmetra scopes.")


class _PolicySnapshot(NamedTuple):
    """Detached creation-time authority for one purpose-bound policy."""

    tenant_record_id_int: int
    policy_version_code: str
    resource_kind: str
    purpose_code: str
    operation_code: str
    required_scope_code: str
    permitted_fields: frozenset[str]


class _RequestSnapshot(NamedTuple):
    """Detached creation-time authority for one purpose-bound access request."""

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


_POLICY_SNAPSHOT_REGISTRY: dict[
    int,
    tuple[weakref.ReferenceType[object], _PolicySnapshot],
] = {}
_REQUEST_SNAPSHOT_REGISTRY: dict[
    int,
    tuple[weakref.ReferenceType[object], _RequestSnapshot],
] = {}
_POLICY_CONSTRUCTION_IDS: set[int] = set()
_REQUEST_CONSTRUCTION_IDS: set[int] = set()


@dataclass(frozen=True, slots=True, weakref_slot=True, init=False)
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

    def __init__(
        self,
        *,
        tenant_record_id: UUID,
        policy_version_code: str,
        resource_kind: str,
        purpose_code: str,
        operation_code: str,
        required_scope_code: str,
        permitted_fields: frozenset[str],
    ) -> None:
        """Write fields and issue authority only inside this constructor call."""
        key = id(self)
        if key in _POLICY_SNAPSHOT_REGISTRY:
            raise TypeError("PurposeBoundAccessPolicy is already initialized")
        if key in _POLICY_CONSTRUCTION_IDS:
            raise TypeError("PurposeBoundAccessPolicy construction is already in progress")
        _POLICY_CONSTRUCTION_IDS.add(key)
        try:
            object.__setattr__(self, "tenant_record_id", tenant_record_id)
            object.__setattr__(self, "policy_version_code", policy_version_code)
            object.__setattr__(self, "resource_kind", resource_kind)
            object.__setattr__(self, "purpose_code", purpose_code)
            object.__setattr__(self, "operation_code", operation_code)
            object.__setattr__(self, "required_scope_code", required_scope_code)
            object.__setattr__(self, "permitted_fields", permitted_fields)
            self.__post_init__()
        finally:
            _POLICY_CONSTRUCTION_IDS.discard(key)

    def __post_init__(self) -> None:
        """Issue a validated snapshot only while the governed constructor is active."""
        key = id(self)
        if key not in _POLICY_CONSTRUCTION_IDS:
            raise TypeError("PurposeBoundAccessPolicy must be initialized through its constructor")
        snapshot = _validated_policy_snapshot(self)
        if key in _POLICY_SNAPSHOT_REGISTRY:
            raise TypeError("PurposeBoundAccessPolicy is already initialized")
        reference = weakref.ref(
            self,
            lambda _reference, evidence_key=key: _POLICY_SNAPSHOT_REGISTRY.pop(
                evidence_key,
                None,
            ),
        )
        _POLICY_SNAPSHOT_REGISTRY[key] = (reference, snapshot)


@dataclass(frozen=True, slots=True, weakref_slot=True, init=False)
class PurposeBoundAccessRequest:
    """PII access attributes resolved before any protected field is returned.

    ``actor_tenant_record_id`` comes from the authenticated identity binding,
    ``tenant_record_id`` is the active Orgmetra request context, and
    ``resource_tenant_record_id`` comes from the target record identity. The
    opaque ``resource_reference`` identifies that exact target for audit
    correlation without copying its PII. All tenant identifiers must match the
    policy tenant. Only field names are carried here; field values remain behind
    the authoritative data boundary until access is allowed.
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

    def __init__(
        self,
        *,
        tenant_record_id: UUID,
        actor_tenant_record_id: UUID,
        resource_tenant_record_id: UUID,
        actor_reference: str,
        resource_reference: str,
        purpose_code: str,
        operation_code: str,
        resource_kind: str,
        requested_fields: frozenset[str],
        granted_scope_codes: frozenset[str],
    ) -> None:
        """Write fields and issue authority only inside this constructor call."""
        key = id(self)
        if key in _REQUEST_SNAPSHOT_REGISTRY:
            raise TypeError("PurposeBoundAccessRequest is already initialized")
        if key in _REQUEST_CONSTRUCTION_IDS:
            raise TypeError("PurposeBoundAccessRequest construction is already in progress")
        _REQUEST_CONSTRUCTION_IDS.add(key)
        try:
            object.__setattr__(self, "tenant_record_id", tenant_record_id)
            object.__setattr__(self, "actor_tenant_record_id", actor_tenant_record_id)
            object.__setattr__(self, "resource_tenant_record_id", resource_tenant_record_id)
            object.__setattr__(self, "actor_reference", actor_reference)
            object.__setattr__(self, "resource_reference", resource_reference)
            object.__setattr__(self, "purpose_code", purpose_code)
            object.__setattr__(self, "operation_code", operation_code)
            object.__setattr__(self, "resource_kind", resource_kind)
            object.__setattr__(self, "requested_fields", requested_fields)
            object.__setattr__(self, "granted_scope_codes", granted_scope_codes)
            self.__post_init__()
        finally:
            _REQUEST_CONSTRUCTION_IDS.discard(key)

    def __post_init__(self) -> None:
        """Issue a validated snapshot only while the governed constructor is active."""
        key = id(self)
        if key not in _REQUEST_CONSTRUCTION_IDS:
            raise TypeError("PurposeBoundAccessRequest must be initialized through its constructor")
        snapshot = _validated_request_snapshot(self)
        if key in _REQUEST_SNAPSHOT_REGISTRY:
            raise TypeError("PurposeBoundAccessRequest is already initialized")
        reference = weakref.ref(
            self,
            lambda _reference, evidence_key=key: _REQUEST_SNAPSHOT_REGISTRY.pop(
                evidence_key,
                None,
            ),
        )
        _REQUEST_SNAPSHOT_REGISTRY[key] = (reference, snapshot)


def _validated_policy_snapshot(policy: PurposeBoundAccessPolicy) -> _PolicySnapshot:
    """Read, validate, and detach one complete policy snapshot."""
    tenant_record_id = policy.tenant_record_id
    policy_version_code = policy.policy_version_code
    resource_kind = policy.resource_kind
    purpose_code = policy.purpose_code
    operation_code = policy.operation_code
    required_scope_code = policy.required_scope_code
    permitted_fields = policy.permitted_fields

    tenant_record_id_int = _validated_uuid_int("tenant_record_id", tenant_record_id)
    _validate_version(policy_version_code)
    _validate_resource_kind(resource_kind)
    _validate_code("purpose_code", purpose_code)
    _validate_code("operation_code", operation_code)
    _validate_scope("required_scope_code", required_scope_code)
    _validate_field_set("permitted_fields", permitted_fields)
    return _PolicySnapshot(
        tenant_record_id_int,
        policy_version_code,
        resource_kind,
        purpose_code,
        operation_code,
        required_scope_code,
        permitted_fields,
    )


def _validated_request_snapshot(request: PurposeBoundAccessRequest) -> _RequestSnapshot:
    """Read, validate, and detach one complete access-request snapshot."""
    tenant_record_id = request.tenant_record_id
    actor_tenant_record_id = request.actor_tenant_record_id
    resource_tenant_record_id = request.resource_tenant_record_id
    actor_reference = request.actor_reference
    resource_reference = request.resource_reference
    purpose_code = request.purpose_code
    operation_code = request.operation_code
    resource_kind = request.resource_kind
    requested_fields = request.requested_fields
    granted_scope_codes = request.granted_scope_codes

    tenant_record_id_int = _validated_uuid_int("tenant_record_id", tenant_record_id)
    actor_tenant_record_id_int = _validated_uuid_int(
        "actor_tenant_record_id",
        actor_tenant_record_id,
    )
    resource_tenant_record_id_int = _validated_uuid_int(
        "resource_tenant_record_id",
        resource_tenant_record_id,
    )
    _validate_reference("actor_reference", actor_reference)
    _validate_resource_kind(resource_kind)
    _validate_reference(
        "resource_reference",
        resource_reference,
        expected_namespace=resource_kind,
    )
    _validate_code("purpose_code", purpose_code)
    _validate_code("operation_code", operation_code)
    _validate_field_set("requested_fields", requested_fields)
    _validate_scope_set(granted_scope_codes)
    return _RequestSnapshot(
        tenant_record_id_int,
        actor_tenant_record_id_int,
        resource_tenant_record_id_int,
        actor_reference,
        resource_reference,
        purpose_code,
        operation_code,
        resource_kind,
        requested_fields,
        granted_scope_codes,
    )


def _issued_policy_snapshot(policy: PurposeBoundAccessPolicy) -> _PolicySnapshot:
    """Return creation-time policy authority only when live fields still match it."""
    entry = _POLICY_SNAPSHOT_REGISTRY.get(id(policy))
    if entry is None or entry[0]() is not policy:
        raise ValueError("PurposeBoundAccessPolicy was not issued by the validated constructor")
    current = _validated_policy_snapshot(policy)
    if current != entry[1]:
        raise ValueError("PurposeBoundAccessPolicy changed after validation")
    return entry[1]


def _issued_request_snapshot(request: PurposeBoundAccessRequest) -> _RequestSnapshot:
    """Return creation-time request authority only when live fields still match it."""
    entry = _REQUEST_SNAPSHOT_REGISTRY.get(id(request))
    if entry is None or entry[0]() is not request:
        raise ValueError("PurposeBoundAccessRequest was not issued by the validated constructor")
    current = _validated_request_snapshot(request)
    if current != entry[1]:
        raise ValueError("PurposeBoundAccessRequest changed after validation")
    return entry[1]


def _privatize_input_issuance_runtime() -> tuple[
    Callable[[PurposeBoundAccessPolicy], _PolicySnapshot],
    Callable[[PurposeBoundAccessRequest], _RequestSnapshot],
]:
    """Move policy/request issuance mutation state behind constructor-bound closures."""
    policy_registry = _POLICY_SNAPSHOT_REGISTRY
    request_registry = _REQUEST_SNAPSHOT_REGISTRY
    policy_construction_ids = _POLICY_CONSTRUCTION_IDS
    request_construction_ids = _REQUEST_CONSTRUCTION_IDS

    def policy_init(
        self: PurposeBoundAccessPolicy,
        *,
        tenant_record_id: UUID,
        policy_version_code: str,
        resource_kind: str,
        purpose_code: str,
        operation_code: str,
        required_scope_code: str,
        permitted_fields: frozenset[str],
    ) -> None:
        """Write fields and issue authority only inside this constructor call."""
        key = id(self)
        if key in policy_registry:
            raise TypeError("PurposeBoundAccessPolicy is already initialized")
        if key in policy_construction_ids:
            raise TypeError("PurposeBoundAccessPolicy construction is already in progress")
        policy_construction_ids.add(key)
        try:
            object.__setattr__(self, "tenant_record_id", tenant_record_id)
            object.__setattr__(self, "policy_version_code", policy_version_code)
            object.__setattr__(self, "resource_kind", resource_kind)
            object.__setattr__(self, "purpose_code", purpose_code)
            object.__setattr__(self, "operation_code", operation_code)
            object.__setattr__(self, "required_scope_code", required_scope_code)
            object.__setattr__(self, "permitted_fields", permitted_fields)
            self.__post_init__()
        finally:
            policy_construction_ids.discard(key)

    def policy_post_init(self: PurposeBoundAccessPolicy) -> None:
        """Issue a policy snapshot only while its private constructor state is active."""
        key = id(self)
        if key not in policy_construction_ids:
            raise TypeError("PurposeBoundAccessPolicy must be initialized through its constructor")
        snapshot = _validated_policy_snapshot(self)
        if key in policy_registry:
            raise TypeError("PurposeBoundAccessPolicy is already initialized")
        reference = weakref.ref(
            self,
            lambda _reference, evidence_key=key: policy_registry.pop(evidence_key, None),
        )
        policy_registry[key] = (reference, snapshot)

    def request_init(
        self: PurposeBoundAccessRequest,
        *,
        tenant_record_id: UUID,
        actor_tenant_record_id: UUID,
        resource_tenant_record_id: UUID,
        actor_reference: str,
        resource_reference: str,
        purpose_code: str,
        operation_code: str,
        resource_kind: str,
        requested_fields: frozenset[str],
        granted_scope_codes: frozenset[str],
    ) -> None:
        """Write fields and issue authority only inside this constructor call."""
        key = id(self)
        if key in request_registry:
            raise TypeError("PurposeBoundAccessRequest is already initialized")
        if key in request_construction_ids:
            raise TypeError("PurposeBoundAccessRequest construction is already in progress")
        request_construction_ids.add(key)
        try:
            object.__setattr__(self, "tenant_record_id", tenant_record_id)
            object.__setattr__(self, "actor_tenant_record_id", actor_tenant_record_id)
            object.__setattr__(self, "resource_tenant_record_id", resource_tenant_record_id)
            object.__setattr__(self, "actor_reference", actor_reference)
            object.__setattr__(self, "resource_reference", resource_reference)
            object.__setattr__(self, "purpose_code", purpose_code)
            object.__setattr__(self, "operation_code", operation_code)
            object.__setattr__(self, "resource_kind", resource_kind)
            object.__setattr__(self, "requested_fields", requested_fields)
            object.__setattr__(self, "granted_scope_codes", granted_scope_codes)
            self.__post_init__()
        finally:
            request_construction_ids.discard(key)

    def request_post_init(self: PurposeBoundAccessRequest) -> None:
        """Issue a request snapshot only while its private constructor state is active."""
        key = id(self)
        if key not in request_construction_ids:
            raise TypeError("PurposeBoundAccessRequest must be initialized through its constructor")
        snapshot = _validated_request_snapshot(self)
        if key in request_registry:
            raise TypeError("PurposeBoundAccessRequest is already initialized")
        reference = weakref.ref(
            self,
            lambda _reference, evidence_key=key: request_registry.pop(evidence_key, None),
        )
        request_registry[key] = (reference, snapshot)

    def issued_policy_snapshot(policy: PurposeBoundAccessPolicy) -> _PolicySnapshot:
        """Return creation-time policy authority only when live fields still match it."""
        entry = policy_registry.get(id(policy))
        if entry is None or entry[0]() is not policy:
            raise ValueError("PurposeBoundAccessPolicy was not issued by the validated constructor")
        current = _validated_policy_snapshot(policy)
        if current != entry[1]:
            raise ValueError("PurposeBoundAccessPolicy changed after validation")
        return entry[1]

    def issued_request_snapshot(request: PurposeBoundAccessRequest) -> _RequestSnapshot:
        """Return creation-time request authority only when live fields still match it."""
        entry = request_registry.get(id(request))
        if entry is None or entry[0]() is not request:
            raise ValueError("PurposeBoundAccessRequest was not issued by the validated constructor")
        current = _validated_request_snapshot(request)
        if current != entry[1]:
            raise ValueError("PurposeBoundAccessRequest changed after validation")
        return entry[1]

    policy_init.__name__ = "__init__"
    policy_init.__qualname__ = "PurposeBoundAccessPolicy.__init__"
    policy_post_init.__name__ = "__post_init__"
    policy_post_init.__qualname__ = "PurposeBoundAccessPolicy.__post_init__"
    request_init.__name__ = "__init__"
    request_init.__qualname__ = "PurposeBoundAccessRequest.__init__"
    request_post_init.__name__ = "__post_init__"
    request_post_init.__qualname__ = "PurposeBoundAccessRequest.__post_init__"

    PurposeBoundAccessPolicy.__init__ = policy_init  # type: ignore[method-assign]
    PurposeBoundAccessPolicy.__post_init__ = policy_post_init  # type: ignore[method-assign]
    PurposeBoundAccessRequest.__init__ = request_init  # type: ignore[method-assign]
    PurposeBoundAccessRequest.__post_init__ = request_post_init  # type: ignore[method-assign]
    return issued_policy_snapshot, issued_request_snapshot


_issued_policy_snapshot, _issued_request_snapshot = _privatize_input_issuance_runtime()
del _POLICY_SNAPSHOT_REGISTRY
del _REQUEST_SNAPSHOT_REGISTRY
del _POLICY_CONSTRUCTION_IDS
del _REQUEST_CONSTRUCTION_IDS
del _privatize_input_issuance_runtime


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
) -> tuple[object, ...]:
    """Validate decision evidence and detach caller-owned mutable runtime objects."""
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
    if allowed and reason_code != "access_permitted":
        raise ValueError("allow decision must use access_permitted reason.")
    if not allowed and reason_code == "access_permitted":
        raise ValueError("deny decision must not use access_permitted reason.")
    return (
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


class AuthorizationDecision:
    """PII-minimized authorization evidence with detached, structurally immutable state.

    Validated values live in evaluator-private snapshot storage rather than writable
    instance slots. In particular the tenant UUID is stored as its integer value
    and rebuilt on access, so a later low-level mutation of the caller's UUID cannot
    rewrite already-issued authorization evidence. The public constructor is
    intentionally non-authoritative: only purpose-bound evaluation may mint an
    issued decision.
    """

    __slots__ = ("__weakref__",)

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

    def __init__(
        self,
        *,
        allowed: bool,
        tenant_record_id: UUID,
        actor_reference: str,
        resource_reference: str,
        policy_version_code: str,
        purpose_code: str,
        operation_code: str,
        resource_kind: str,
        requested_fields: frozenset[str],
        authorized_fields: frozenset[str],
        reason_code: str,
        next_action: str,
    ) -> None:
        """Reject direct construction; only the evaluator may register evidence."""
        try:
            _decision_snapshot_for(self)
        except ValueError:
            raise TypeError("AuthorizationDecision must be issued by purpose-bound evaluation") from None
        raise TypeError("AuthorizationDecision is already initialized")

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Seal the evidence type so subclasses cannot override validation hooks."""
        raise TypeError("AuthorizationDecision must not be subclassed")

    def _snapshot(self) -> tuple[object, ...]:
        """Return evaluator-issued state or fail closed for low-level forged instances."""
        return _decision_snapshot_for(self)

    @property
    def allowed(self) -> bool:
        """Return the immutable allow/deny verdict."""
        return self._snapshot()[0]  # type: ignore[return-value]

    @property
    def tenant_record_id(self) -> UUID:
        """Return a detached UUID copy of the authorized tenant identity."""
        return UUID(int=self._snapshot()[1])  # type: ignore[arg-type]

    @property
    def actor_reference(self) -> str:
        """Return the PII-minimized actor reference."""
        return self._snapshot()[2]  # type: ignore[return-value]

    @property
    def resource_reference(self) -> str:
        """Return the opaque target reference bound to the decision."""
        return self._snapshot()[3]  # type: ignore[return-value]

    @property
    def policy_version_code(self) -> str:
        """Return the immutable policy version used for evaluation."""
        return self._snapshot()[4]  # type: ignore[return-value]

    @property
    def purpose_code(self) -> str:
        """Return the purpose bound to the decision."""
        return self._snapshot()[5]  # type: ignore[return-value]

    @property
    def operation_code(self) -> str:
        """Return the operation bound to the decision."""
        return self._snapshot()[6]  # type: ignore[return-value]

    @property
    def resource_kind(self) -> str:
        """Return the governed resource kind."""
        return self._snapshot()[7]  # type: ignore[return-value]

    @property
    def requested_fields(self) -> frozenset[str]:
        """Return the exact immutable requested-field set."""
        return self._snapshot()[8]  # type: ignore[return-value]

    @property
    def authorized_fields(self) -> frozenset[str]:
        """Return the exact immutable authorized-field set."""
        return self._snapshot()[9]  # type: ignore[return-value]

    @property
    def reason_code(self) -> str:
        """Return the governed allow/deny reason code."""
        return self._snapshot()[10]  # type: ignore[return-value]

    @property
    def next_action(self) -> str:
        """Return bounded non-authoritative recovery guidance."""
        return self._snapshot()[11]  # type: ignore[return-value]

    def __repr__(self) -> str:
        """Preserve a deterministic value-style representation for diagnostics."""
        return (
            "AuthorizationDecision("
            f"allowed={self.allowed!r}, "
            f"tenant_record_id={self.tenant_record_id!r}, "
            f"actor_reference={self.actor_reference!r}, "
            f"resource_reference={self.resource_reference!r}, "
            f"policy_version_code={self.policy_version_code!r}, "
            f"purpose_code={self.purpose_code!r}, "
            f"operation_code={self.operation_code!r}, "
            f"resource_kind={self.resource_kind!r}, "
            f"requested_fields={self.requested_fields!r}, "
            f"authorized_fields={self.authorized_fields!r}, "
            f"reason_code={self.reason_code!r}, "
            f"next_action={self.next_action!r})"
        )

    def __eq__(self, other: object) -> bool:
        """Retain dataclass-like value equality only for exact issued decisions."""
        if type(other) is not AuthorizationDecision:
            return False
        return self._snapshot() == other._snapshot()

    def __hash__(self) -> int:
        """Retain stable value hashing over detached immutable evidence."""
        return hash(self._snapshot())


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
    request: _RequestSnapshot,
    policy: _PolicySnapshot,
    allowed: bool,
    reason_code: str,
) -> AuthorizationDecision:
    """Reject direct use of the former module-level authority-minting helper."""
    raise TypeError("decision issuance is internal to evaluate_purpose_bound_access")


def _build_decision_runtime() -> tuple[
    Callable[[AuthorizationDecision], tuple[object, ...]],
    Callable[..., AuthorizationDecision],
]:
    """Create evaluator-private decision storage and expose only read/evaluate closures."""
    registry: dict[
        int,
        tuple[weakref.ReferenceType[object], tuple[object, ...]],
    ] = {}

    def decision_snapshot_for(decision: AuthorizationDecision) -> tuple[object, ...]:
        """Return only state registered by this evaluator runtime."""
        entry = registry.get(id(decision))
        if entry is None or entry[0]() is not decision:
            raise ValueError("AuthorizationDecision was not issued by purpose-bound evaluation")
        return entry[1]

    def evaluate(
        *,
        request: PurposeBoundAccessRequest,
        policy: PurposeBoundAccessPolicy,
    ) -> AuthorizationDecision:
        """Evaluate tenant, resource, purpose, operation, scope, and field attributes."""
        if type(request) is not PurposeBoundAccessRequest:
            raise TypeError("request must be a PurposeBoundAccessRequest")
        if type(policy) is not PurposeBoundAccessPolicy:
            raise TypeError("policy must be a PurposeBoundAccessPolicy")

        request_snapshot = _issued_request_snapshot(request)
        policy_snapshot = _issued_policy_snapshot(policy)

        def issue_decision(*, allowed: bool, reason_code: str) -> AuthorizationDecision:
            """Register one decision from already-issued policy/request snapshots."""
            authorized_fields = request_snapshot.requested_fields if allowed else frozenset()
            next_action = _ALLOW_NEXT_ACTION if allowed else _DENIAL_NEXT_ACTION[reason_code]
            snapshot = _validated_decision_snapshot(
                allowed=allowed,
                tenant_record_id=UUID(int=request_snapshot.tenant_record_id_int),
                actor_reference=request_snapshot.actor_reference,
                resource_reference=request_snapshot.resource_reference,
                policy_version_code=policy_snapshot.policy_version_code,
                purpose_code=request_snapshot.purpose_code,
                operation_code=request_snapshot.operation_code,
                resource_kind=request_snapshot.resource_kind,
                requested_fields=request_snapshot.requested_fields,
                authorized_fields=authorized_fields,
                reason_code=reason_code,
                next_action=next_action,
            )
            decision = object.__new__(AuthorizationDecision)
            key = id(decision)
            reference = weakref.ref(
                decision,
                lambda _reference, evidence_key=key: registry.pop(evidence_key, None),
            )
            registry[key] = (reference, snapshot)
            return decision

        if (
            request_snapshot.tenant_record_id_int != policy_snapshot.tenant_record_id_int
            or request_snapshot.actor_tenant_record_id_int != policy_snapshot.tenant_record_id_int
            or request_snapshot.resource_tenant_record_id_int != policy_snapshot.tenant_record_id_int
        ):
            return issue_decision(allowed=False, reason_code="tenant_scope_mismatch")
        if request_snapshot.resource_kind != policy_snapshot.resource_kind:
            return issue_decision(allowed=False, reason_code="resource_not_allowed")
        if request_snapshot.purpose_code != policy_snapshot.purpose_code:
            return issue_decision(allowed=False, reason_code="purpose_not_allowed")
        if request_snapshot.operation_code != policy_snapshot.operation_code:
            return issue_decision(allowed=False, reason_code="operation_not_allowed")
        if policy_snapshot.required_scope_code not in request_snapshot.granted_scope_codes:
            return issue_decision(allowed=False, reason_code="required_scope_missing")
        if not request_snapshot.requested_fields.issubset(policy_snapshot.permitted_fields):
            return issue_decision(allowed=False, reason_code="field_not_allowed")
        return issue_decision(allowed=True, reason_code="access_permitted")

    return decision_snapshot_for, evaluate


_decision_snapshot_for, evaluate_purpose_bound_access = _build_decision_runtime()


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
