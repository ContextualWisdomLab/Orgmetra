"""Regressions for the service-process authorization trust boundary."""

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
    """Build one trusted-composition policy value."""
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
    """Build one authenticated/request-derived authorization value."""
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


def _closure_bindings(function: Callable[..., object]) -> dict[str, object]:
    """Expose closure state exactly as same-process Python code can inspect it."""
    cells = function.__closure__
    if cells is None:
        return {}
    return {
        name: cell.cell_contents
        for name, cell in zip(function.__code__.co_freevars, cells, strict=True)
    }


@pytest.mark.parametrize(
    "attribute_name",
    (
        "_POLICY_SNAPSHOT_REGISTRY",
        "_REQUEST_SNAPSHOT_REGISTRY",
        "_POLICY_CONSTRUCTION_IDS",
        "_REQUEST_CONSTRUCTION_IDS",
        "_DECISION_SNAPSHOT_REGISTRY",
        "_DECISION_ISSUANCE_IDS",
    ),
)
def test_module_has_no_runtime_authority_registry(attribute_name: str) -> None:
    """No mutable Python registry may be described as an issuance security boundary."""
    assert not hasattr(authorization, attribute_name)


@pytest.mark.parametrize(
    "function",
    (
        PurposeBoundAccessPolicy.__post_init__,
        PurposeBoundAccessRequest.__post_init__,
        evaluate_purpose_bound_access,
    ),
)
def test_authorization_boundary_does_not_hide_mutable_authority_in_closure_cells(
    function: Callable[..., object],
) -> None:
    """Inspectable closure cells must not carry a claimed authorization capability."""
    assert _closure_bindings(function) == {}


def test_policy_authority_is_not_inferred_from_python_constructor_provenance() -> None:
    """Evaluation validates data; trusted composition, not object provenance, owns policy authority."""
    policy = object.__new__(PurposeBoundAccessPolicy)
    object.__setattr__(policy, "tenant_record_id", TENANT)
    object.__setattr__(policy, "policy_version_code", "people_pii_v1")
    object.__setattr__(policy, "resource_kind", "person_record")
    object.__setattr__(policy, "purpose_code", "hr_operations")
    object.__setattr__(policy, "operation_code", "read_person_pii")
    object.__setattr__(policy, "required_scope_code", "orgmetra.people.read")
    object.__setattr__(policy, "permitted_fields", frozenset({"work_email"}))

    decision = evaluate_purpose_bound_access(request=_request(), policy=policy)

    assert decision.allowed is True
    assert decision.authorized_fields == frozenset({"work_email"})


def test_current_values_are_revalidated_even_inside_the_trusted_process() -> None:
    """Low-level corruption still fails closed instead of relying on creation-time bookkeeping."""
    policy = _policy()
    object.__setattr__(policy, "permitted_fields", {"work_email"})

    with pytest.raises(ValueError, match="permitted_fields must be a frozenset"):
        evaluate_purpose_bound_access(request=_request(), policy=policy)
