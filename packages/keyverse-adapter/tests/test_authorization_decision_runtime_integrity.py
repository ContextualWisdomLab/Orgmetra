"""Runtime-integrity regressions for evaluator-issued authorization decisions."""

from __future__ import annotations

import gc
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


class _ForgedUUID(UUID):
    """Carry caller-defined UUID behavior inside authorization evidence input."""


class _ForgedText(str):
    """Carry caller-defined text behavior inside authorization evidence input."""


class _ForgedFieldSet(frozenset[str]):
    """Carry caller-defined set behavior inside authorization evidence input."""


def _policy(**overrides: object) -> PurposeBoundAccessPolicy:
    """Build one deterministic issued policy for decision-integrity tests."""
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
    """Build one deterministic issued request for decision-integrity tests."""
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
    """Return one allow decision issued only by the governed evaluator."""
    return evaluate_purpose_bound_access(request=_request(), policy=_policy())


def _validate_decision(**overrides: object) -> tuple[object, ...]:
    """Exercise the internal pure evidence validator without minting authority."""
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


def test_decision_cannot_be_subclassed_to_bypass_validation() -> None:
    """Caller-defined decision classes must not override issued evidence behavior."""
    with pytest.raises(TypeError, match="AuthorizationDecision must not be subclassed"):

        class _ForgedDecision(AuthorizationDecision):
            pass


def test_decision_resists_object_setattr_after_valid_evaluation() -> None:
    """Low-level attribute writes cannot replace already-issued authorization evidence."""
    decision = _decision()
    with pytest.raises((AttributeError, TypeError)):
        object.__setattr__(decision, "allowed", False)
    assert decision.allowed is True
    assert decision.reason_code == "access_permitted"


def test_decision_detaches_caller_owned_exact_uuid() -> None:
    """Later low-level UUID mutation must not rewrite an evaluator-issued decision."""
    tenant = UUID(str(TENANT))
    decision = evaluate_purpose_bound_access(
        request=_request(
            tenant_record_id=tenant,
            actor_tenant_record_id=tenant,
            resource_tenant_record_id=tenant,
        ),
        policy=_policy(tenant_record_id=tenant),
    )
    object.__setattr__(tenant, "int", 0)
    assert decision.tenant_record_id == TENANT


@pytest.mark.parametrize("forged_int", [-1, 1 << 128, "invalid"])
def test_decision_validator_rejects_low_level_corrupted_exact_uuid(forged_int: object) -> None:
    """The internal snapshot validator rejects an exact UUID with corrupted integer state."""
    tenant = UUID(str(TENANT))
    object.__setattr__(tenant, "int", forged_int)
    with pytest.raises(ValueError, match="tenant_record_id must contain a valid UUID integer"):
        _validate_decision(tenant_record_id=tenant)


def test_decision_rejects_unissued_low_level_instance() -> None:
    """Bypassing evaluation must not yield readable authorization evidence."""
    forged = object.__new__(AuthorizationDecision)
    with pytest.raises(ValueError, match="was not issued by purpose-bound evaluation"):
        _ = forged.allowed


def test_decision_cannot_be_reinitialized_with_new_evidence() -> None:
    """A previously issued decision cannot be replaced through a second initializer call."""
    decision = _decision()
    with pytest.raises(TypeError, match="already initialized"):
        AuthorizationDecision.__init__(
            decision,
            allowed=False,
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:operator-17",
            resource_reference=RESOURCE_REFERENCE,
            policy_version_code="assignment-correction-v1",
            purpose_code="workforce_admin",
            operation_code="correct_record",
            resource_kind="assignment_record",
            requested_fields=REQUESTED_FIELDS,
            authorized_fields=frozenset(),
            reason_code="field_not_allowed",
            next_action="Request only fields allowed for this purpose.",
        )


def test_decision_preserves_value_semantics_and_deterministic_repr() -> None:
    """Issuance hardening preserves equality, hashing, and diagnostic representation."""
    left = _decision()
    right = _decision()
    assert left == right
    assert not (left == object())
    assert hash(left) == hash(right)
    assert repr(left).startswith("AuthorizationDecision(allowed=True")
    assert "assignment_category_code" in repr(left)


def test_decision_registry_does_not_retain_dead_evidence() -> None:
    """Lifecycle bookkeeping must not keep evaluator-issued evidence alive."""
    decision = _decision()
    reference = weakref.ref(decision)
    del decision
    gc.collect()
    assert reference() is None


def test_decision_validator_rejects_non_boolean_allowed_flag() -> None:
    """Truthy integers cannot masquerade as an authorization verdict."""
    with pytest.raises(ValueError, match="allowed must be a boolean"):
        _validate_decision(allowed=1)


def test_decision_validator_rejects_uuid_subclass() -> None:
    """Decision snapshots cannot retain caller-defined UUID runtime behavior."""
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
    """Decision snapshots cannot retain caller-defined text runtime behavior."""
    with pytest.raises(ValueError):
        _validate_decision(**{field_name: forged_value})


@pytest.mark.parametrize("field_name", ["requested_fields", "authorized_fields"])
def test_decision_validator_rejects_frozenset_subclasses(field_name: str) -> None:
    """Field evidence cannot override containment or equality after evaluation."""
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
            next_action="Request only fields allowed for this purpose.",
        )


def test_allow_decision_rejects_denial_reason() -> None:
    """An allow verdict cannot carry a denial reason into downstream evidence."""
    with pytest.raises(ValueError, match="allow decision must use access_permitted reason"):
        _validate_decision(reason_code="field_not_allowed")


def test_deny_decision_rejects_success_reason() -> None:
    """A deny verdict cannot masquerade as successful authorization evidence."""
    with pytest.raises(ValueError, match="deny decision must not use access_permitted reason"):
        _validate_decision(
            allowed=False,
            authorized_fields=frozenset(),
            reason_code="access_permitted",
        )


def test_decision_validator_accepts_bounded_internal_denial_reason() -> None:
    """The pure validator preserves a bounded denial code without minting authority."""
    snapshot = _validate_decision(
        allowed=False,
        authorized_fields=frozenset(),
        reason_code="access_denied",
        next_action="stop",
    )
    assert snapshot[10] == "access_denied"


def test_decision_validator_preserves_bounded_actionable_text() -> None:
    """Recovery guidance validation remains independent of the governed verdict."""
    snapshot = _validate_decision(next_action="Continue after logging the reviewed evidence.")
    assert snapshot[11] == "Continue after logging the reviewed evidence."


def test_decision_validator_rejects_resource_reference_namespace_mismatch() -> None:
    """Downstream evidence must correlate its target to the declared resource kind."""
    with pytest.raises(ValueError, match="resource_reference namespace must match resource_kind"):
        _validate_decision(resource_reference="employment_record:0198a412800070008000000000000070")


def test_decision_validator_rejects_blank_next_action() -> None:
    """Authorization evidence must preserve a bounded recovery instruction."""
    with pytest.raises(ValueError, match="next_action must be a non-blank string"):
        _validate_decision(next_action="   ")
