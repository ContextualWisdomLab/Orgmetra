"""Runtime-integrity regressions for downstream authorization-decision evidence."""

from __future__ import annotations

from uuid import UUID

import pytest

from orgmetra_keyverse_adapter.authorization import AuthorizationDecision

TENANT = UUID("10000000-0000-7000-8000-000000000501")


class _ForgedUUID(UUID):
    """Carry caller-defined UUID behavior inside downstream authorization evidence."""


class _ForgedText(str):
    """Carry caller-defined text behavior inside downstream authorization evidence."""


class _ForgedFieldSet(frozenset[str]):
    """Carry caller-defined set behavior inside downstream authorization evidence."""


def _decision(**overrides: object) -> AuthorizationDecision:
    """Build one deterministic allow decision for runtime-integrity tests."""
    values: dict[str, object] = {
        "allowed": True,
        "tenant_record_id": TENANT,
        "actor_reference": "keyverse_subject:operator-17",
        "resource_reference": "assignment_record:0198a412800070008000000000000070",
        "policy_version_code": "assignment-correction-v1",
        "purpose_code": "workforce_admin",
        "operation_code": "correct_record",
        "resource_kind": "assignment_record",
        "requested_fields": frozenset({"assignment_category_code"}),
        "authorized_fields": frozenset({"assignment_category_code"}),
        "reason_code": "access_permitted",
        "next_action": "Continue with only the authorized fields.",
    }
    values.update(overrides)
    return AuthorizationDecision(**values)  # type: ignore[arg-type]


def test_decision_rejects_non_boolean_allowed_flag() -> None:
    """Do not let truthy integers masquerade as an authorization verdict."""
    with pytest.raises(ValueError, match="allowed must be a boolean"):
        _decision(allowed=1)


def test_decision_rejects_uuid_subclass() -> None:
    """Tenant evidence must not retain caller-defined UUID runtime behavior."""
    forged = _ForgedUUID(str(TENANT))
    with pytest.raises(ValueError, match="tenant_record_id must be a UUID"):
        _decision(tenant_record_id=forged)


@pytest.mark.parametrize(
    ("field_name", "forged_value"),
    [
        ("actor_reference", _ForgedText("keyverse_subject:operator-17")),
        (
            "resource_reference",
            _ForgedText("assignment_record:0198a412800070008000000000000070"),
        ),
        ("policy_version_code", _ForgedText("assignment-correction-v1")),
        ("purpose_code", _ForgedText("workforce_admin")),
        ("operation_code", _ForgedText("correct_record")),
        ("resource_kind", _ForgedText("assignment_record")),
        ("reason_code", _ForgedText("access_permitted")),
        ("next_action", _ForgedText("Continue with only the authorized fields.")),
    ],
)
def test_decision_rejects_string_subclasses(field_name: str, forged_value: str) -> None:
    """Decision evidence cannot retain caller-defined text runtime behavior."""
    with pytest.raises(ValueError):
        _decision(**{field_name: forged_value})


@pytest.mark.parametrize("field_name", ["requested_fields", "authorized_fields"])
def test_decision_rejects_frozenset_subclasses(field_name: str) -> None:
    """Field evidence cannot override containment or equality after authorization."""
    forged = _ForgedFieldSet({"assignment_category_code"})
    with pytest.raises(ValueError, match=f"{field_name} must be a frozenset"):
        _decision(**{field_name: forged})


@pytest.mark.parametrize("field_name", ["requested_fields", "authorized_fields"])
def test_decision_rejects_string_subclasses_inside_field_sets(field_name: str) -> None:
    """Each authorized field identifier must be an exact built-in string."""
    forged = frozenset({_ForgedText("assignment_category_code")})
    with pytest.raises(ValueError, match=f"{field_name} must contain only"):
        _decision(**{field_name: forged})


def test_allow_decision_requires_exact_requested_authorized_field_equality() -> None:
    """An allow verdict cannot silently authorize fewer or different fields than requested."""
    with pytest.raises(ValueError, match="allow decision must authorize exactly the requested fields"):
        _decision(authorized_fields=frozenset({"legal_name"}))


def test_deny_decision_cannot_carry_authorized_fields() -> None:
    """A deny verdict cannot retain a non-empty authorized field set."""
    with pytest.raises(ValueError, match="deny decision must not authorize fields"):
        _decision(
            allowed=False,
            authorized_fields=frozenset({"assignment_category_code"}),
            reason_code="field_not_allowed",
            next_action="Request only fields allowed for this purpose.",
        )


def test_allow_decision_rejects_denial_reason() -> None:
    """An allow verdict cannot carry a denial reason into downstream audit evidence."""
    with pytest.raises(ValueError, match="allow decision must use access_permitted reason"):
        _decision(reason_code="field_not_allowed")


def test_deny_decision_rejects_success_reason() -> None:
    """A deny verdict cannot masquerade as successful authorization in audit evidence."""
    with pytest.raises(ValueError, match="deny decision must use a governed denial reason"):
        _decision(
            allowed=False,
            authorized_fields=frozenset(),
            reason_code="access_permitted",
        )


def test_decision_preserves_bounded_actionable_text_as_non_authoritative_guidance() -> None:
    """Recovery guidance may vary without changing the governed verdict or reason code."""
    decision = _decision(next_action="Continue after logging the reviewed evidence.")
    assert decision.next_action == "Continue after logging the reviewed evidence."


def test_decision_rejects_resource_reference_namespace_mismatch() -> None:
    """Downstream evidence must correlate its opaque target to the declared resource kind."""
    with pytest.raises(ValueError, match="resource_reference namespace must match resource_kind"):
        _decision(resource_reference="employment_record:0198a412800070008000000000000070")


def test_decision_rejects_blank_next_action() -> None:
    """Authorization evidence must preserve an actionable bounded recovery instruction."""
    with pytest.raises(ValueError, match="next_action must be a non-blank string"):
        _decision(next_action="   ")
