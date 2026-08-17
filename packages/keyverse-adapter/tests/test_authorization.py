"""Purpose-bound authorization tests for tenant-safe, field-minimized HR access."""

from dataclasses import replace
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter.authorization import (
    AuthorizationDeniedError,
    PurposeBoundAccessPolicy,
    PurposeBoundAccessRequest,
    evaluate_purpose_bound_access,
    require_purpose_bound_access,
)

TENANT = UUID("10000000-0000-7000-8000-000000000501")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000502")
POLICY = PurposeBoundAccessPolicy(
    tenant_record_id=TENANT,
    policy_version_code="people_pii_v1",
    resource_kind="person_record",
    purpose_code="hr_operations",
    operation_code="read_person_pii",
    required_scope_code="orgmetra.people.read",
    permitted_fields=frozenset({"legal_name", "work_email"}),
)
REQUEST = PurposeBoundAccessRequest(
    tenant_record_id=TENANT,
    actor_tenant_record_id=TENANT,
    resource_tenant_record_id=TENANT,
    actor_reference="keyverse_subject:sub_jordan_hale",
    purpose_code="hr_operations",
    operation_code="read_person_pii",
    resource_kind="person_record",
    requested_fields=frozenset({"work_email"}),
    granted_scope_codes=frozenset({"orgmetra.people.read"}),
)


def test_exact_tenant_purpose_scope_and_field_subset_is_authorized() -> None:
    """Allow only the requested field subset after every policy attribute matches."""
    decision = require_purpose_bound_access(request=REQUEST, policy=POLICY)

    assert decision.allowed is True
    assert decision.reason_code == "access_permitted"
    assert decision.authorized_fields == frozenset({"work_email"})
    assert decision.requested_fields == REQUEST.requested_fields
    assert decision.policy_version_code == "people_pii_v1"
    assert decision.actor_reference == REQUEST.actor_reference
    assert decision.next_action == "Continue with only the authorized fields."


@pytest.mark.parametrize(
    ("request", "reason_code", "next_action"),
    [
        (
            replace(REQUEST, resource_tenant_record_id=OTHER_TENANT),
            "tenant_scope_mismatch",
            "Re-resolve the actor, request context, resource, and policy in one tenant before retrying.",
        ),
        (
            replace(REQUEST, actor_tenant_record_id=OTHER_TENANT),
            "tenant_scope_mismatch",
            "Re-resolve the actor, request context, resource, and policy in one tenant before retrying.",
        ),
        (
            replace(REQUEST, purpose_code="payroll_processing"),
            "purpose_not_allowed",
            "Use an approved purpose for this policy or obtain a separately governed policy decision.",
        ),
        (
            replace(REQUEST, operation_code="export_person_pii"),
            "operation_not_allowed",
            "Use the operation authorized by this policy or obtain a narrower policy for the requested action.",
        ),
        (
            replace(REQUEST, resource_kind="employment_record"),
            "resource_not_allowed",
            "Resolve the policy for the requested resource kind before retrying.",
        ),
        (
            replace(REQUEST, granted_scope_codes=frozenset({"orgmetra.people.write"})),
            "required_scope_missing",
            "Obtain the operation-specific Keyverse scope; a purpose header alone cannot authorize access.",
        ),
        (
            replace(REQUEST, requested_fields=frozenset({"work_email", "home_address"})),
            "field_not_allowed",
            "Request only fields allowed for this purpose or obtain a separately reviewed field policy.",
        ),
    ],
)
def test_fail_closed_decisions_explain_the_next_safe_action(
    request: PurposeBoundAccessRequest,
    reason_code: str,
    next_action: str,
) -> None:
    """Deny mismatched ABAC attributes without silently widening access."""
    decision = evaluate_purpose_bound_access(request=request, policy=POLICY)

    assert decision.allowed is False
    assert decision.authorized_fields == frozenset()
    assert decision.reason_code == reason_code
    assert decision.next_action == next_action

    with pytest.raises(AuthorizationDeniedError) as caught:
        require_purpose_bound_access(request=request, policy=POLICY)
    assert caught.value.reason_code == reason_code
    assert caught.value.next_action == next_action
    assert caught.value.decision == decision


def test_policy_tenant_mismatch_is_denied_before_resource_attributes() -> None:
    """Never apply another tenant's policy even when all visible request fields match."""
    foreign_policy = replace(POLICY, tenant_record_id=OTHER_TENANT)
    decision = evaluate_purpose_bound_access(request=REQUEST, policy=foreign_policy)

    assert decision.allowed is False
    assert decision.reason_code == "tenant_scope_mismatch"


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("tenant_record_id", UUID(int=0)),
        ("tenant_record_id", UUID(int=(1 << 128) - 1)),
        ("tenant_record_id", "not-a-uuid"),
        ("policy_version_code", "bad version"),
        ("resource_kind", "person"),
        ("purpose_code", "HR Operations"),
        ("operation_code", "read-person-pii"),
        ("required_scope_code", "people.read"),
        ("permitted_fields", frozenset()),
        ("permitted_fields", frozenset({"legal-name"})),
        ("permitted_fields", {"legal_name"}),
    ],
)
def test_policy_rejects_ambiguous_or_wildcard_like_attributes(
    field_name: str,
    invalid_value: object,
) -> None:
    """Keep persisted policy inputs immutable, explicit, and machine-checkable."""
    with pytest.raises(ValueError):
        replace(POLICY, **{field_name: invalid_value})


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("tenant_record_id", UUID(int=0)),
        ("actor_tenant_record_id", UUID(int=(1 << 128) - 1)),
        ("resource_tenant_record_id", "not-a-uuid"),
        ("actor_reference", "jordan-hale"),
        ("purpose_code", "*"),
        ("operation_code", "read-person-pii"),
        ("resource_kind", "person"),
        ("requested_fields", frozenset()),
        ("requested_fields", frozenset({"legal-name"})),
        ("requested_fields", {"legal_name"}),
        ("granted_scope_codes", frozenset()),
        ("granted_scope_codes", frozenset({"people.read"})),
        ("granted_scope_codes", {"orgmetra.people.read"}),
    ],
)
def test_request_rejects_untrusted_or_ambiguous_authorization_attributes(
    field_name: str,
    invalid_value: object,
) -> None:
    """Reject malformed identity, tenant, purpose, field, and token-scope inputs."""
    with pytest.raises(ValueError):
        replace(REQUEST, **{field_name: invalid_value})


def test_authorization_decision_exposes_only_governance_metadata() -> None:
    """The decision is auditable without copying person-field values into the adapter."""
    decision = evaluate_purpose_bound_access(request=REQUEST, policy=POLICY)

    assert decision.tenant_record_id == TENANT
    assert decision.purpose_code == "hr_operations"
    assert decision.operation_code == "read_person_pii"
    assert decision.resource_kind == "person_record"
    assert not hasattr(decision, "resource_value")
