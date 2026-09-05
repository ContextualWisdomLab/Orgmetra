"""Runtime-integrity regressions for purpose-bound authorization decision data."""

from __future__ import annotations

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


class _ForgedUUID(UUID):
    """Carry caller-defined UUID behavior inside authorization evidence input."""


class _ForgedText(str):
    """Carry caller-defined text behavior inside authorization evidence input."""


class _ForgedFieldSet(frozenset[str]):
    """Carry caller-defined set behavior inside authorization evidence input."""


def _policy(**overrides: object) -> PurposeBoundAccessPolicy:
    """Build one deterministic trusted policy for decision-integrity tests."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "policy_version_code": "assignment-correction-v1",
        "resource_kind": "assignment_record",
        "purpose_code": "workforce_admin",
        "operation_code": "correct_record",
        "required_scope_code": "orgmetra.people.write",
        "permitted_fields": REQUESTED_FIELDS,
    }
    values.update(overrides)
    return PurposeBoundAccessPolicy(**values)  # type: ignore[arg-type]


def _request(**overrides: object) -> PurposeBoundAccessRequest:
    """Build one deterministic request value for decision-integrity tests."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "actor_tenant_record_id": TENANT,
        "resource_tenant_record_id": TENANT,
        "actor_reference": "keyverse_subject:operator-17",
        "resource_reference": RESOURCE_REFERENCE,
        "purpose_code": "workforce_admin",
        "operation_code": "correct_record",
        "resource_kind": "assignment_record",
        "requested_fields": REQUESTED_FIELDS,
        "granted_scope_codes": frozenset({"orgmetra.people.write"}),
    }
    values.update(overrides)
    return PurposeBoundAccessRequest(**values)  # type: ignore[arg-type]


def _decision() -> AuthorizationDecision:
    """Return one allow decision from the normal evaluator path."""
    return evaluate_purpose_bound_access(request=_request(), policy=_policy())


def _validate_decision(**overrides: object) -> tuple[object, ...]:
    """Exercise the pure evidence validator without asserting object provenance."""
    values: dict[str, object] = {
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
    values.update(overrides)
    return authorization_module._validated_decision_snapshot(**values)


def test_decision_cannot_be_subclassed_to_override_runtime_behavior() -> None:
    """Caller-defined decision classes cannot override validated field semantics."""
    with pytest.raises(TypeError, match="AuthorizationDecision must not be subclassed"):
        type("_ForgedDecision", (AuthorizationDecision,), {})


def test_consumer_revalidation_detects_low_level_decision_mutation() -> None:
    """A durable consumer can fail closed if trusted-process code corrupts decision data."""
    decision = _decision()
    object.__setattr__(decision, "allowed", False)

    with pytest.raises(ValueError, match="deny decision must not authorize fields"):
        authorization_module.validate_authorization_decision(decision)


def test_decision_detaches_caller_owned_exact_uuid() -> None:
    """Later low-level UUID mutation cannot rewrite constructed decision data."""
    tenant = UUID(str(TENANT))
    decision = AuthorizationDecision(
        allowed=True,
        tenant_record_id=tenant,
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
    object.__setattr__(tenant, "int", 0)

    assert decision.tenant_record_id == TENANT


@pytest.mark.parametrize("forged_int", [-1, 1 << 128, "invalid"])
def test_decision_validator_rejects_low_level_corrupted_exact_uuid(forged_int: object) -> None:
    """The snapshot validator rejects an exact UUID with corrupted integer state."""
    tenant = UUID(str(TENANT))
    object.__setattr__(tenant, "int", forged_int)
    with pytest.raises(ValueError, match="tenant_record_id must contain a valid UUID integer"):
        _validate_decision(tenant_record_id=tenant)


def test_decision_preserves_value_semantics_and_deterministic_repr() -> None:
    """Validation preserves equality, hashing, and diagnostic representation."""
    left = _decision()
    right = _decision()
    assert left == right
    assert not (left == object())
    assert hash(left) == hash(right)
    assert repr(left).startswith("AuthorizationDecision(allowed=True")
    assert "assignment_category_code" in repr(left)


def test_decision_validator_rejects_non_boolean_allowed_flag() -> None:
    """Truthy integers cannot masquerade as an authorization verdict."""
    with pytest.raises(ValueError, match="allowed must be a boolean"):
        _validate_decision(allowed=1)


def test_decision_validator_rejects_uuid_subclass() -> None:
    """Decision data cannot retain caller-defined UUID runtime behavior."""
    forged = _ForgedUUID(str(TENANT))
    with pytest.raises(ValueError, match="tenant_record_id must be a UUID"):
        _validate_decision(tenant_record_id=forged)


@pytest.mark.parametrize(
    ("field_name", "forged_value"),
    [
        ("actor_reference", _ForgedText("keyverse_subject:operator-17")),
        ("resource_reference", _ForgedText(RESOURCE_REFERENCE)),
        ("policy_version_code", _ForgedText("assignment-correction-v1")),
        ("purpose_code", _ForgedText("workforce_admin")),
        ("operation_code", _ForgedText("correct_record")),
        ("resource_kind", _ForgedText("assignment_record")),
        ("reason_code", _ForgedText("access_permitted")),
        ("next_action", _ForgedText("Continue with only the authorized fields.")),
    ],
)
def test_decision_validator_rejects_string_subclasses(field_name: str, forged_value: str) -> None:
    """Decision data cannot retain caller-defined text runtime behavior."""
    with pytest.raises(ValueError):
        _validate_decision(**{field_name: forged_value})


@pytest.mark.parametrize("field_name", ["requested_fields", "authorized_fields"])
def test_decision_validator_rejects_frozenset_subclasses(field_name: str) -> None:
    """Field evidence cannot override containment or equality behavior."""
    forged = _ForgedFieldSet({"assignment_category_code"})
    with pytest.raises(ValueError, match=f"{field_name} must be a frozenset"):
        _validate_decision(**{field_name: forged})


@pytest.mark.parametrize("field_name", ["requested_fields", "authorized_fields"])
def test_decision_validator_rejects_string_subclasses_inside_field_sets(field_name: str) -> None:
    """Each field identifier must be an exact built-in string."""
    forged = frozenset({_ForgedText("assignment_category_code")})
    with pytest.raises(ValueError, match=f"{field_name} must contain only"):
        _validate_decision(**{field_name: forged})


def test_allow_decision_requires_exact_requested_authorized_field_equality() -> None:
    """An allow verdict cannot silently authorize fewer or different fields."""
    with pytest.raises(ValueError, match="allow decision must authorize exactly the requested fields"):
        _validate_decision(authorized_fields=frozenset({"legal_name"}))


def test_deny_decision_cannot_carry_authorized_fields() -> None:
    """A deny verdict cannot retain a non-empty authorized field set."""
    with pytest.raises(ValueError, match="deny decision must not authorize fields"):
        _validate_decision(
            allowed=False,
            authorized_fields=REQUESTED_FIELDS,
            reason_code="field_not_allowed",
            next_action=(
                "Request only fields allowed for this purpose or obtain a separately reviewed field policy."
            ),
        )


def test_allow_decision_rejects_denial_reason() -> None:
    """An allow verdict cannot carry a denial reason into downstream evidence."""
    with pytest.raises(ValueError, match="allow decision must use access_permitted reason"):
        _validate_decision(reason_code="field_not_allowed")


def test_deny_decision_rejects_success_reason() -> None:
    """A deny verdict cannot masquerade as successful authorization evidence."""
    with pytest.raises(ValueError, match="deny decision must use a known denial reason"):
        _validate_decision(
            allowed=False,
            authorized_fields=frozenset(),
            reason_code="access_permitted",
        )


def test_decision_validator_accepts_governed_denial_reason_and_action() -> None:
    """A denial snapshot preserves the evaluator's exact reason-to-recovery contract."""
    next_action = (
        "Use an approved purpose for this policy or obtain a separately governed policy decision."
    )
    snapshot = _validate_decision(
        allowed=False,
        authorized_fields=frozenset(),
        reason_code="purpose_not_allowed",
        next_action=next_action,
    )
    assert snapshot[10] == "purpose_not_allowed"
    assert snapshot[11] == next_action


def test_decision_validator_rejects_noncanonical_allow_action() -> None:
    """Allow evidence cannot replace the evaluator's governed recovery instruction."""
    with pytest.raises(ValueError, match="allow decision must use the canonical next action"):
        _validate_decision(next_action="Continue after logging the reviewed evidence.")


def test_decision_validator_rejects_resource_reference_namespace_mismatch() -> None:
    """Downstream evidence must correlate its target to the declared resource kind."""
    with pytest.raises(ValueError, match="resource_reference namespace must match resource_kind"):
        _validate_decision(resource_reference="employment_record:0198a412800070008000000000000070")


def test_decision_validator_rejects_blank_next_action() -> None:
    """Authorization evidence must preserve a bounded recovery instruction."""
    with pytest.raises(ValueError, match="next_action must be a non-blank string"):
        _validate_decision(next_action="   ")
