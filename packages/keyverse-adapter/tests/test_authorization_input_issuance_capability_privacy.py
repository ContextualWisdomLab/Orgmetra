"""Regressions for policy/request issuance capability privacy."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

import pytest

import orgmetra_keyverse_adapter.authorization as authorization
from orgmetra_keyverse_adapter.authorization import (
    PurposeBoundAccessPolicy,
    PurposeBoundAccessRequest,
    evaluate_purpose_bound_access,
)

TENANT = UUID("10000000-0000-7000-8000-000000000501")


def _policy() -> PurposeBoundAccessPolicy:
    """Build one legitimately constructor-issued narrow policy."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="people_pii_v1",
        resource_kind="person_record",
        purpose_code="hr_operations",
        operation_code="read_person_pii",
        required_scope_code="orgmetra.people.read",
        permitted_fields=frozenset({"work_email"}),
    )


def _request() -> PurposeBoundAccessRequest:
    """Build one legitimately constructor-issued narrow request."""
    return PurposeBoundAccessRequest(
        tenant_record_id=TENANT,
        actor_tenant_record_id=TENANT,
        resource_tenant_record_id=TENANT,
        actor_reference="keyverse_subject:sub_jordan_hale",
        resource_reference="person_record:per_01J5EXACTTARGET",
        purpose_code="hr_operations",
        operation_code="read_person_pii",
        resource_kind="person_record",
        requested_fields=frozenset({"work_email"}),
        granted_scope_codes=frozenset({"orgmetra.people.read"}),
    )


def _forged_policy() -> PurposeBoundAccessPolicy:
    """Allocate valid-looking exact policy fields without its constructor."""
    policy = object.__new__(PurposeBoundAccessPolicy)
    object.__setattr__(policy, "tenant_record_id", TENANT)
    object.__setattr__(policy, "policy_version_code", "people_pii_v1")
    object.__setattr__(policy, "resource_kind", "person_record")
    object.__setattr__(policy, "purpose_code", "hr_operations")
    object.__setattr__(policy, "operation_code", "read_person_pii")
    object.__setattr__(policy, "required_scope_code", "orgmetra.people.read")
    object.__setattr__(policy, "permitted_fields", frozenset({"work_email"}))
    return policy


def _forged_request() -> PurposeBoundAccessRequest:
    """Allocate valid-looking exact request fields without its constructor."""
    request = object.__new__(PurposeBoundAccessRequest)
    object.__setattr__(request, "tenant_record_id", TENANT)
    object.__setattr__(request, "actor_tenant_record_id", TENANT)
    object.__setattr__(request, "resource_tenant_record_id", TENANT)
    object.__setattr__(request, "actor_reference", "keyverse_subject:sub_jordan_hale")
    object.__setattr__(request, "resource_reference", "person_record:per_01J5EXACTTARGET")
    object.__setattr__(request, "purpose_code", "hr_operations")
    object.__setattr__(request, "operation_code", "read_person_pii")
    object.__setattr__(request, "resource_kind", "person_record")
    object.__setattr__(request, "requested_fields", frozenset({"work_email"}))
    object.__setattr__(request, "granted_scope_codes", frozenset({"orgmetra.people.read"}))
    return request


def _closure_bindings(function: Callable[..., object]) -> dict[str, object]:
    """Expose function cells exactly as an ordinary same-process Python consumer can."""
    cells = function.__closure__
    if cells is None:
        return {}
    return {
        name: cell.cell_contents
        for name, cell in zip(function.__code__.co_freevars, cells, strict=True)
    }


def test_module_consumer_cannot_activate_forged_policy_through_construction_state() -> None:
    """Mutable module construction state must not mint policy authority."""
    policy = _forged_policy()
    construction_ids = getattr(authorization, "_POLICY_CONSTRUCTION_IDS", None)
    registry = getattr(authorization, "_POLICY_SNAPSHOT_REGISTRY", None)

    try:
        if construction_ids is not None:
            construction_ids.add(id(policy))
        with pytest.raises(TypeError, match="must be initialized through its constructor"):
            PurposeBoundAccessPolicy.__post_init__(policy)
    finally:
        if construction_ids is not None:
            construction_ids.discard(id(policy))
        if registry is not None:
            registry.pop(id(policy), None)

    with pytest.raises(ValueError, match="was not issued by the validated constructor"):
        evaluate_purpose_bound_access(request=_request(), policy=policy)


def test_module_consumer_cannot_activate_forged_request_through_construction_state() -> None:
    """Mutable module construction state must not mint request authority."""
    request = _forged_request()
    construction_ids = getattr(authorization, "_REQUEST_CONSTRUCTION_IDS", None)
    registry = getattr(authorization, "_REQUEST_SNAPSHOT_REGISTRY", None)

    try:
        if construction_ids is not None:
            construction_ids.add(id(request))
        with pytest.raises(TypeError, match="must be initialized through its constructor"):
            PurposeBoundAccessRequest.__post_init__(request)
    finally:
        if construction_ids is not None:
            construction_ids.discard(id(request))
        if registry is not None:
            registry.pop(id(request), None)

    with pytest.raises(ValueError, match="was not issued by the validated constructor"):
        evaluate_purpose_bound_access(request=request, policy=_policy())


def test_same_process_consumer_cannot_mint_policy_by_mutating_closure_cells() -> None:
    """Inspectable Python closure cells must not constitute policy issuance authority."""
    policy = _forged_policy()
    bindings = _closure_bindings(PurposeBoundAccessPolicy.__post_init__)
    construction_ids = bindings.get("policy_construction_ids")
    registry = bindings.get("policy_registry")

    if construction_ids is not None:
        construction_ids.add(id(policy))
    try:
        with pytest.raises(TypeError, match="must be initialized through its constructor"):
            PurposeBoundAccessPolicy.__post_init__(policy)
    finally:
        if construction_ids is not None:
            construction_ids.discard(id(policy))
        if registry is not None:
            registry.pop(id(policy), None)

    with pytest.raises(ValueError, match="was not issued by the validated constructor"):
        evaluate_purpose_bound_access(request=_request(), policy=policy)


def test_same_process_consumer_cannot_mint_request_by_mutating_closure_cells() -> None:
    """Inspectable Python closure cells must not constitute request issuance authority."""
    request = _forged_request()
    bindings = _closure_bindings(PurposeBoundAccessRequest.__post_init__)
    construction_ids = bindings.get("request_construction_ids")
    registry = bindings.get("request_registry")

    if construction_ids is not None:
        construction_ids.add(id(request))
    try:
        with pytest.raises(TypeError, match="must be initialized through its constructor"):
            PurposeBoundAccessRequest.__post_init__(request)
    finally:
        if construction_ids is not None:
            construction_ids.discard(id(request))
        if registry is not None:
            registry.pop(id(request), None)

    with pytest.raises(ValueError, match="was not issued by the validated constructor"):
        evaluate_purpose_bound_access(request=request, policy=_policy())


@pytest.mark.parametrize(
    "attribute_name",
    (
        "_POLICY_SNAPSHOT_REGISTRY",
        "_REQUEST_SNAPSHOT_REGISTRY",
        "_POLICY_CONSTRUCTION_IDS",
        "_REQUEST_CONSTRUCTION_IDS",
    ),
)
def test_module_does_not_expose_writable_input_issuance_capabilities(attribute_name: str) -> None:
    """Policy/request issuance mutation capability must not be a module attribute."""
    assert not hasattr(authorization, attribute_name)
