"""Regression coverage for target-specific authorization denial guidance."""

from uuid import UUID

from orgmetra_keyverse_adapter.authorization import (
    PurposeBoundAccessPolicy,
    PurposeBoundAccessRequest,
    evaluate_purpose_bound_access,
)


def test_missing_target_scope_tells_operator_to_obtain_target_scope() -> None:
    """A target-scope denial must not mislabel the missing grant as operation scope."""
    tenant = UUID("10000000-0000-7000-8000-000000000501")
    target_scope = "orgmetra.people.write.organization_unit_0198a412820070008000000000000050"
    policy = PurposeBoundAccessPolicy(
        tenant_record_id=tenant,
        policy_version_code="people_write_v1",
        resource_kind="employment_record",
        purpose_code="hr_operations",
        operation_code="create_employment",
        required_scope_code="orgmetra.people.write",
        permitted_fields=frozenset({"employing_organization_unit_id"}),
    )
    request = PurposeBoundAccessRequest(
        tenant_record_id=tenant,
        actor_tenant_record_id=tenant,
        resource_tenant_record_id=tenant,
        actor_reference="keyverse_subject:sub_operator",
        resource_reference="employment_record:emp_target",
        purpose_code="hr_operations",
        operation_code="create_employment",
        resource_kind="employment_record",
        requested_fields=frozenset({"employing_organization_unit_id"}),
        granted_scope_codes=frozenset({"orgmetra.people.write"}),
        required_target_scope_code=target_scope,
    )

    decision = evaluate_purpose_bound_access(request=request, policy=policy)

    assert decision.allowed is False
    assert decision.reason_code == "required_scope_missing"
    assert decision.next_action == (
        "Obtain the exact Keyverse scope for the governed target before retrying; "
        "the operation scope alone cannot authorize that target."
    )
