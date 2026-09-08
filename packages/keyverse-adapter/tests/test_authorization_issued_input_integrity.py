"""Live-value integrity regressions for purpose-bound authorization inputs."""

from __future__ import annotations

from uuid import UUID

import pytest

from orgmetra_keyverse_adapter.authorization import (
    PurposeBoundAccessPolicy,
    PurposeBoundAccessRequest,
    evaluate_purpose_bound_access,
)

TENANT = UUID("10000000-0000-7000-8000-000000000501")


def _policy(*, field: str = "work_email", tenant: UUID = TENANT) -> PurposeBoundAccessPolicy:
    """Build one trusted-composition policy value."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=tenant,
        policy_version_code="people_pii_v1",
        resource_kind="person_record",
        purpose_code="hr_operations",
        operation_code="read_person_pii",
        required_scope_code="orgmetra.people.read",
        permitted_fields=frozenset({field}),
    )


def _request(
    *,
    field: str = "work_email",
    tenant: UUID = TENANT,
) -> PurposeBoundAccessRequest:
    """Build one request-derived authorization value."""
    return PurposeBoundAccessRequest(
        tenant_record_id=tenant,
        actor_tenant_record_id=tenant,
        resource_tenant_record_id=tenant,
        actor_reference="keyverse_subject:sub_jordan_hale",
        resource_reference="person_record:per_01J5EXACTTARGET",
        purpose_code="hr_operations",
        operation_code="read_person_pii",
        resource_kind="person_record",
        requested_fields=frozenset({field}),
        granted_scope_codes=frozenset({"orgmetra.people.read"}),
    )


def test_policy_constructor_detaches_caller_owned_uuid() -> None:
    """Later low-level caller UUID mutation cannot rewrite a policy value."""
    tenant = UUID(str(TENANT))
    policy = _policy(tenant=tenant)

    object.__setattr__(tenant, "int", 0)

    assert policy.tenant_record_id == TENANT


def test_request_constructor_detaches_caller_owned_uuid_instances() -> None:
    """Request tenant identities do not retain caller-owned UUID objects."""
    tenant = UUID(str(TENANT))
    request = _request(tenant=tenant)

    object.__setattr__(tenant, "int", 0)

    assert request.tenant_record_id == TENANT
    assert request.actor_tenant_record_id == TENANT
    assert request.resource_tenant_record_id == TENANT


def test_evaluator_revalidates_post_construction_policy_runtime_type() -> None:
    """Low-level policy corruption fails closed at the evaluation boundary."""
    policy = _policy()
    object.__setattr__(policy, "permitted_fields", {"work_email"})

    with pytest.raises(ValueError, match="permitted_fields must be a frozenset"):
        evaluate_purpose_bound_access(request=_request(), policy=policy)


def test_evaluator_revalidates_post_construction_request_scope_runtime_type() -> None:
    """Low-level scope corruption cannot reach membership evaluation."""
    request = _request()
    object.__setattr__(request, "granted_scope_codes", {"orgmetra.people.read"})

    with pytest.raises(ValueError, match="granted_scope_codes must be a frozenset"):
        evaluate_purpose_bound_access(request=request, policy=_policy())


def test_evaluator_revalidates_post_construction_request_field_runtime_type() -> None:
    """Low-level field-set corruption cannot reach subset evaluation."""
    request = _request()
    object.__setattr__(request, "requested_fields", {"work_email"})

    with pytest.raises(ValueError, match="requested_fields must be a frozenset"):
        evaluate_purpose_bound_access(request=request, policy=_policy())


def test_same_process_policy_value_change_is_not_misrepresented_as_provenance_security() -> None:
    """Inside the TCB, valid current policy data—not a Python object history—drives evaluation."""
    policy = _policy()
    object.__setattr__(policy, "permitted_fields", frozenset({"compensation_amount"}))

    decision = evaluate_purpose_bound_access(
        request=_request(field="compensation_amount"),
        policy=policy,
    )

    assert decision.allowed is True
    assert decision.authorized_fields == frozenset({"compensation_amount"})


def test_policy_retains_deterministic_value_semantics() -> None:
    """Validation hardening preserves stable equality, hashing, and diagnostics."""
    left = _policy()
    right = _policy()

    assert left == right
    assert hash(left) == hash(right)
    assert repr(left).startswith("PurposeBoundAccessPolicy(")


def test_request_retains_deterministic_value_semantics() -> None:
    """Request validation preserves stable equality, hashing, and diagnostics."""
    left = _request()
    right = _request()

    assert left == right
    assert hash(left) == hash(right)
    assert repr(left).startswith("PurposeBoundAccessRequest(")
