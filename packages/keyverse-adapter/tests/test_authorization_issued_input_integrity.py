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
