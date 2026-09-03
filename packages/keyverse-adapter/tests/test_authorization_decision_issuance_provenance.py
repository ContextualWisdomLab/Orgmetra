"""Issuance-provenance regressions for purpose-bound authorization decisions."""

from __future__ import annotations

import weakref
from uuid import UUID

import pytest

import orgmetra_keyverse_adapter.authorization as authorization_module
from orgmetra_keyverse_adapter import (
    AuthorizationDecision,
    PurposeBoundAccessPolicy,
    PurposeBoundAccessRequest,
    evaluate_purpose_bound_access,
)

TENANT = UUID("10000000-0000-7000-8000-000000000501")
RESOURCE_REFERENCE = "assignment_record:0198a412800070008000000000000070"
REQUESTED_FIELDS = frozenset({"assignment_category_code"})


def test_direct_decision_constructor_cannot_mint_allow_authority() -> None:
    """A caller must not mint an allow decision without governed policy evaluation."""
    with pytest.raises(TypeError, match="purpose-bound evaluation"):
        AuthorizationDecision(
            allowed=True,
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:operator-17",
            resource_reference=RESOURCE_REFERENCE,
            policy_version_code="assignment-correction-v1",
            purpose_code="workforce_admin",
            operation_code="correct_record",
            resource_kind="assignment_record",
            requested_fields=REQUESTED_FIELDS,
            authorized_fields=REQUESTED_FIELDS,
            reason_code="access_permitted",
            next_action="Continue with only the authorized fields.",
        )


def test_module_decision_helper_cannot_mint_from_fabricated_snapshots() -> None:
    """Module-callable helpers must not turn fabricated snapshots into authority."""
    request_snapshot = authorization_module._RequestSnapshot(
        TENANT.int,
        TENANT.int,
        TENANT.int,
        "keyverse_subject:operator-17",
        RESOURCE_REFERENCE,
        "workforce_admin",
        "correct_record",
        "assignment_record",
        REQUESTED_FIELDS,
        frozenset({"orgmetra.people.write"}),
    )
    policy_snapshot = authorization_module._PolicySnapshot(
        TENANT.int,
        "assignment-correction-v1",
        "assignment_record",
        "workforce_admin",
        "correct_record",
        "orgmetra.people.write",
        REQUESTED_FIELDS,
    )

    with pytest.raises(TypeError, match="internal to evaluate_purpose_bound_access"):
        authorization_module._decision(
            request=request_snapshot,
            policy=policy_snapshot,
            allowed=True,
            reason_code="access_permitted",
        )
    assert not hasattr(authorization_module, "_DECISION_ISSUANCE_IDS")


def test_module_registry_insertion_cannot_mint_forged_decision() -> None:
    """Consumer-visible module state must not provide a writable authority registry."""
    forged = object.__new__(AuthorizationDecision)
    snapshot = authorization_module._validated_decision_snapshot(
        allowed=True,
        tenant_record_id=TENANT,
        actor_reference="keyverse_subject:operator-17",
        resource_reference=RESOURCE_REFERENCE,
        policy_version_code="assignment-correction-v1",
        purpose_code="workforce_admin",
        operation_code="correct_record",
        resource_kind="assignment_record",
        requested_fields=REQUESTED_FIELDS,
        authorized_fields=REQUESTED_FIELDS,
        reason_code="access_permitted",
        next_action="Continue with only the authorized fields.",
    )
    registry = getattr(authorization_module, "_DECISION_SNAPSHOT_REGISTRY", None)
    try:
        if registry is not None:
            registry[id(forged)] = (weakref.ref(forged), snapshot)
        with pytest.raises(ValueError, match="was not issued by purpose-bound evaluation"):
            _ = forged.allowed
    finally:
        if registry is not None:
            registry.pop(id(forged), None)


def test_governed_evaluator_remains_the_decision_issuance_path() -> None:
    """Matching issued request and policy evidence still produce one allow decision."""
    policy = PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="assignment-correction-v1",
        resource_kind="assignment_record",
        purpose_code="workforce_admin",
        operation_code="correct_record",
        required_scope_code="orgmetra.people.write",
        permitted_fields=REQUESTED_FIELDS,
    )
    request = PurposeBoundAccessRequest(
        tenant_record_id=TENANT,
        actor_tenant_record_id=TENANT,
        resource_tenant_record_id=TENANT,
        actor_reference="keyverse_subject:operator-17",
        resource_reference=RESOURCE_REFERENCE,
        purpose_code="workforce_admin",
        operation_code="correct_record",
        resource_kind="assignment_record",
        requested_fields=REQUESTED_FIELDS,
        granted_scope_codes=frozenset({"orgmetra.people.write"}),
    )

    decision = evaluate_purpose_bound_access(request=request, policy=policy)

    assert type(decision) is AuthorizationDecision
    assert decision.allowed is True
    assert decision.tenant_record_id == TENANT
    assert decision.resource_reference == RESOURCE_REFERENCE
    assert decision.authorized_fields == REQUESTED_FIELDS
