"""Trust-boundary regressions for purpose-bound authorization decisions."""

from __future__ import annotations

from uuid import UUID

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


def _decision_values() -> dict[str, object]:
    """Return one semantically coherent PII-minimized allow decision payload."""
    return {
        "allowed": True,
        "tenant_record_id": TENANT,
        "actor_reference": "keyverse_subject:operator-17",
        "resource_reference": RESOURCE_REFERENCE,
        "policy_version_code": "assignment-correction-v1",
        "purpose_code": "workforce_admin",
        "operation_code": "correct_record",
        "resource_kind": "assignment_record",
        "requested_fields": REQUESTED_FIELDS,
        "authorized_fields": REQUESTED_FIELDS,
        "reason_code": "access_permitted",
        "next_action": "Continue with only the authorized fields.",
    }


def test_direct_decision_construction_validates_data_but_does_not_claim_provenance() -> None:
    """A Python decision object is validated evidence data, not an unforgeable capability."""
    decision = AuthorizationDecision(**_decision_values())  # type: ignore[arg-type]

    assert decision.allowed is True
    assert decision.tenant_record_id == TENANT
    assert decision.authorized_fields == REQUESTED_FIELDS


def test_authorization_module_exposes_no_mutable_issuance_registry() -> None:
    """No Python mapping or id-set may be represented as authorization issuance authority."""
    for attribute_name in (
        "_DECISION_SNAPSHOT_REGISTRY",
        "_DECISION_ISSUANCE_IDS",
        "_POLICY_SNAPSHOT_REGISTRY",
        "_REQUEST_SNAPSHOT_REGISTRY",
        "_POLICY_CONSTRUCTION_IDS",
        "_REQUEST_CONSTRUCTION_IDS",
    ):
        assert not hasattr(authorization_module, attribute_name)
    assert evaluate_purpose_bound_access.__closure__ is None


def test_governed_evaluator_builds_decision_from_current_trusted_policy_and_request() -> None:
    """The normal service path still evaluates every narrowing attribute before allow."""
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
