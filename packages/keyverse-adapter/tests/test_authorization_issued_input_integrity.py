"""Issued-input integrity regressions for purpose-bound authorization."""

from __future__ import annotations

from uuid import UUID

import pytest

from orgmetra_keyverse_adapter.authorization import (
    PurposeBoundAccessPolicy,
    PurposeBoundAccessRequest,
    evaluate_purpose_bound_access,
)

TENANT = UUID("10000000-0000-7000-8000-000000000501")


def _policy() -> PurposeBoundAccessPolicy:
    """Build one narrow policy whose creation-time field authority is auditable."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="people_pii_v1",
        resource_kind="person_record",
        purpose_code="hr_operations",
        operation_code="read_person_pii",
        required_scope_code="orgmetra.people.read",
        permitted_fields=frozenset({"work_email"}),
    )


def _request(*, field: str = "work_email") -> PurposeBoundAccessRequest:
    """Build one request with an exact creation-time field and scope snapshot."""
    return PurposeBoundAccessRequest(
        tenant_record_id=TENANT,
        actor_tenant_record_id=TENANT,
        resource_tenant_record_id=TENANT,
        actor_reference="keyverse_subject:sub_jordan_hale",
        resource_reference="person_record:per_01J5EXACTTARGET",
        purpose_code="hr_operations",
        operation_code="read_person_pii",
        resource_kind="person_record",
        requested_fields=frozenset({field}),
        granted_scope_codes=frozenset({"orgmetra.people.read"}),
    )


def _policy_without_constructor() -> PurposeBoundAccessPolicy:
    """Forge valid-looking policy fields without invoking the public constructor."""
    policy = object.__new__(PurposeBoundAccessPolicy)
    object.__setattr__(policy, "tenant_record_id", TENANT)
    object.__setattr__(policy, "policy_version_code", "people_pii_v1")
    object.__setattr__(policy, "resource_kind", "person_record")
    object.__setattr__(policy, "purpose_code", "hr_operations")
    object.__setattr__(policy, "operation_code", "read_person_pii")
    object.__setattr__(policy, "required_scope_code", "orgmetra.people.read")
    object.__setattr__(policy, "permitted_fields", frozenset({"work_email"}))
    return policy


def _request_without_constructor() -> PurposeBoundAccessRequest:
    """Forge valid-looking request fields without invoking the public constructor."""
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


def test_evaluator_rejects_post_construction_policy_widening() -> None:
    """Low-level mutation cannot widen a policy after its governed construction."""
    policy = _policy()
    object.__setattr__(
        policy,
        "permitted_fields",
        frozenset({"work_email", "compensation_amount"}),
    )

    with pytest.raises(ValueError, match="PurposeBoundAccessPolicy changed after validation"):
        evaluate_purpose_bound_access(
            request=_request(field="compensation_amount"),
            policy=policy,
        )


def test_evaluator_rejects_post_construction_request_scope_rewrite() -> None:
    """Low-level mutation cannot replace the authenticated scope snapshot after validation."""
    request = _request()
    object.__setattr__(request, "granted_scope_codes", frozenset({"orgmetra.people.admin"}))

    with pytest.raises(ValueError, match="PurposeBoundAccessRequest changed after validation"):
        evaluate_purpose_bound_access(request=request, policy=_policy())


def test_evaluator_rejects_post_construction_request_field_rewrite() -> None:
    """Low-level mutation cannot change which PII field the issued request asks to expose."""
    request = _request()
    object.__setattr__(request, "requested_fields", frozenset({"compensation_amount"}))

    with pytest.raises(ValueError, match="PurposeBoundAccessRequest changed after validation"):
        evaluate_purpose_bound_access(request=request, policy=_policy())


def test_direct_policy_post_init_cannot_issue_constructor_bypassing_object() -> None:
    """Public lifecycle hooks cannot mint policy authority for a forged exact object."""
    policy = _policy_without_constructor()

    with pytest.raises(TypeError, match="must be initialized through its constructor"):
        PurposeBoundAccessPolicy.__post_init__(policy)

    with pytest.raises(ValueError, match="was not issued by the validated constructor"):
        evaluate_purpose_bound_access(request=_request(), policy=policy)


def test_direct_request_post_init_cannot_issue_constructor_bypassing_object() -> None:
    """Public lifecycle hooks cannot mint request authority for a forged exact object."""
    request = _request_without_constructor()

    with pytest.raises(TypeError, match="must be initialized through its constructor"):
        PurposeBoundAccessRequest.__post_init__(request)

    with pytest.raises(ValueError, match="was not issued by the validated constructor"):
        evaluate_purpose_bound_access(request=request, policy=_policy())


def test_rejected_policy_reinitialization_preserves_issued_value() -> None:
    """A rejected second constructor call cannot rewrite observable policy state."""
    policy = _policy()
    before = (
        policy.tenant_record_id,
        policy.policy_version_code,
        policy.resource_kind,
        policy.purpose_code,
        policy.operation_code,
        policy.required_scope_code,
        policy.permitted_fields,
        repr(policy),
        hash(policy),
    )

    with pytest.raises(TypeError, match="PurposeBoundAccessPolicy is already initialized"):
        PurposeBoundAccessPolicy.__init__(
            policy,
            tenant_record_id=TENANT,
            policy_version_code="people_pii_v2",
            resource_kind="person_record",
            purpose_code="compensation_review",
            operation_code="read_person_pii",
            required_scope_code="orgmetra.people.read",
            permitted_fields=frozenset({"compensation_amount"}),
        )

    after = (
        policy.tenant_record_id,
        policy.policy_version_code,
        policy.resource_kind,
        policy.purpose_code,
        policy.operation_code,
        policy.required_scope_code,
        policy.permitted_fields,
        repr(policy),
        hash(policy),
    )
    assert after == before


def test_invalid_policy_reinitialization_preserves_issued_value() -> None:
    """The issuance guard precedes validation and leaves an issued policy unchanged."""
    policy = _policy()
    before = repr(policy)

    with pytest.raises(TypeError, match="PurposeBoundAccessPolicy is already initialized"):
        PurposeBoundAccessPolicy.__init__(
            policy,
            tenant_record_id=TENANT,
            policy_version_code="contains whitespace",
            resource_kind="person_record",
            purpose_code="hr_operations",
            operation_code="read_person_pii",
            required_scope_code="orgmetra.people.read",
            permitted_fields=frozenset({"work_email"}),
        )

    assert repr(policy) == before
    assert policy.policy_version_code == "people_pii_v1"


def test_rejected_request_reinitialization_preserves_issued_value() -> None:
    """A rejected second constructor call cannot rewrite authenticated request state."""
    request = _request()
    before = (
        request.tenant_record_id,
        request.actor_tenant_record_id,
        request.resource_tenant_record_id,
        request.actor_reference,
        request.resource_reference,
        request.purpose_code,
        request.operation_code,
        request.resource_kind,
        request.requested_fields,
        request.granted_scope_codes,
        repr(request),
        hash(request),
    )

    with pytest.raises(TypeError, match="PurposeBoundAccessRequest is already initialized"):
        PurposeBoundAccessRequest.__init__(
            request,
            tenant_record_id=TENANT,
            actor_tenant_record_id=TENANT,
            resource_tenant_record_id=TENANT,
            actor_reference="keyverse_subject:sub_other_actor",
            resource_reference="person_record:per_01J5EXACTTARGET",
            purpose_code="compensation_review",
            operation_code="read_person_pii",
            resource_kind="person_record",
            requested_fields=frozenset({"compensation_amount"}),
            granted_scope_codes=frozenset({"orgmetra.people.read"}),
        )

    after = (
        request.tenant_record_id,
        request.actor_tenant_record_id,
        request.resource_tenant_record_id,
        request.actor_reference,
        request.resource_reference,
        request.purpose_code,
        request.operation_code,
        request.resource_kind,
        request.requested_fields,
        request.granted_scope_codes,
        repr(request),
        hash(request),
    )
    assert after == before


def test_invalid_request_reinitialization_preserves_issued_value() -> None:
    """The issuance guard precedes validation and leaves an issued request unchanged."""
    request = _request()
    before = repr(request)

    with pytest.raises(TypeError, match="PurposeBoundAccessRequest is already initialized"):
        PurposeBoundAccessRequest.__init__(
            request,
            tenant_record_id=TENANT,
            actor_tenant_record_id=TENANT,
            resource_tenant_record_id=TENANT,
            actor_reference="keyverse_subject:sub_jordan_hale",
            resource_reference="wrong_namespace:per_01J5EXACTTARGET",
            purpose_code="hr_operations",
            operation_code="read_person_pii",
            resource_kind="person_record",
            requested_fields=frozenset({"work_email"}),
            granted_scope_codes=frozenset({"orgmetra.people.read"}),
        )

    assert repr(request) == before
    assert request.resource_reference == "person_record:per_01J5EXACTTARGET"
