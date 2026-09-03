"""Regression contracts for exact employing-organization authorization evidence binding."""

from types import SimpleNamespace
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import (
    AuthorizationDecision,
    PurposeBoundAccessPolicy,
    PurposeBoundAccessRequest,
    require_purpose_bound_access,
)
from orgmetra_people_api.authorization import organization_unit_scope_code
from orgmetra_people_api.hire import HireDecisionIntegrityError
from orgmetra_people_api.mutations import PeopleMutationIntegrityError
from orgmetra_people_api.postgres_hire import _validate_authorization as validate_hire_authorization
from orgmetra_people_api.postgres_mutations import _require_authorization as require_mutation_authorization

TENANT = UUID("0198a412-8200-7000-8000-000000000001")
EMPLOYMENT = UUID("0198a412-8200-7000-8000-000000000030")
SELECTION_DECISION = UUID("0198a412-8200-7000-8000-000000000081")
ORGANIZATION = UUID("0198a412-8200-7000-8000-000000000050")
OTHER_ORGANIZATION = UUID("0198a412-8200-7000-8000-000000000051")
TARGET_SCOPE = organization_unit_scope_code(ORGANIZATION)
OTHER_TARGET_SCOPE = organization_unit_scope_code(OTHER_ORGANIZATION)
ACTOR = "keyverse_subject:operator-17"


def _allowed_decision(
    *,
    resource_kind: str,
    resource_reference: str,
    operation_code: str,
    requested_fields: frozenset[str],
    target_scope: str,
) -> AuthorizationDecision:
    """Return a real policy-evaluator decision bound to one exact target scope."""
    policy = PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="target-binding-v1",
        resource_kind=resource_kind,
        purpose_code="workforce_admin",
        operation_code=operation_code,
        required_scope_code="orgmetra.people.write",
        permitted_fields=requested_fields,
    )
    request = PurposeBoundAccessRequest(
        tenant_record_id=TENANT,
        actor_tenant_record_id=TENANT,
        resource_tenant_record_id=TENANT,
        actor_reference=ACTOR,
        resource_reference=resource_reference,
        purpose_code="workforce_admin",
        operation_code=operation_code,
        resource_kind=resource_kind,
        requested_fields=requested_fields,
        granted_scope_codes=frozenset({"orgmetra.people.write", target_scope}),
        required_target_scope_code=target_scope,
    )
    return require_purpose_bound_access(request=request, policy=policy)


def test_allow_decision_preserves_exact_target_scope_as_evidence() -> None:
    """An allow decision must prove which governed organization target was checked."""
    decision = _allowed_decision(
        resource_kind="employment_record",
        resource_reference=f"employment_record:{EMPLOYMENT.hex}",
        operation_code="create_record",
        requested_fields=frozenset({"employment_record"}),
        target_scope=TARGET_SCOPE,
    )

    assert decision.required_target_scope_code == TARGET_SCOPE


def test_employment_persistence_rejects_allow_for_different_organization_scope() -> None:
    """The DB adapter must not trust an allow decision bound to another organization."""
    decision = _allowed_decision(
        resource_kind="employment_record",
        resource_reference=f"employment_record:{EMPLOYMENT.hex}",
        operation_code="create_record",
        requested_fields=frozenset({"employment_record"}),
        target_scope=OTHER_TARGET_SCOPE,
    )

    with pytest.raises(PeopleMutationIntegrityError, match="authorization"):
        require_mutation_authorization(
            authorization=decision,
            tenant_record_id=TENANT,
            resource_reference=f"employment_record:{EMPLOYMENT.hex}",
            resource_kind="employment_record",
            requested_fields=frozenset({"employment_record"}),
            required_target_scope_code=TARGET_SCOPE,
        )


def test_hire_persistence_rejects_allow_for_different_organization_scope() -> None:
    """Confirmed-hire persistence independently binds the allow to its employer target."""
    decision = _allowed_decision(
        resource_kind="selection_decision",
        resource_reference=f"selection_decision:{SELECTION_DECISION.hex}",
        operation_code="materialize_worker",
        requested_fields=frozenset({"candidate_worker_conversion"}),
        target_scope=OTHER_TARGET_SCOPE,
    )
    command = SimpleNamespace(
        tenant_record_id=TENANT,
        selection_decision_id=SELECTION_DECISION,
        employing_organization_unit_id=ORGANIZATION,
    )

    with pytest.raises(HireDecisionIntegrityError, match="authorization"):
        validate_hire_authorization(command, decision)  # type: ignore[arg-type]


def test_matching_target_scope_is_accepted_by_both_persistence_validators() -> None:
    """The added defense-in-depth check must preserve correctly bound callers."""
    employment_decision = _allowed_decision(
        resource_kind="employment_record",
        resource_reference=f"employment_record:{EMPLOYMENT.hex}",
        operation_code="create_record",
        requested_fields=frozenset({"employment_record"}),
        target_scope=TARGET_SCOPE,
    )
    assert require_mutation_authorization(
        authorization=employment_decision,
        tenant_record_id=TENANT,
        resource_reference=f"employment_record:{EMPLOYMENT.hex}",
        resource_kind="employment_record",
        requested_fields=frozenset({"employment_record"}),
        required_target_scope_code=TARGET_SCOPE,
    ) is employment_decision

    hire_decision = _allowed_decision(
        resource_kind="selection_decision",
        resource_reference=f"selection_decision:{SELECTION_DECISION.hex}",
        operation_code="materialize_worker",
        requested_fields=frozenset({"candidate_worker_conversion"}),
        target_scope=TARGET_SCOPE,
    )
    command = SimpleNamespace(
        tenant_record_id=TENANT,
        selection_decision_id=SELECTION_DECISION,
        employing_organization_unit_id=ORGANIZATION,
    )
    assert validate_hire_authorization(command, hire_decision) is hire_decision  # type: ignore[arg-type]
