"""Consumer-boundary regressions for authorization decision revalidation."""

from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDecision, validate_authorization_decision

TENANT = UUID("10000000-0000-7000-8000-000000000501")
FIELDS = frozenset({"assignment_category_code"})


def _decision() -> AuthorizationDecision:
    """Build one coherent internal decision-data value."""
    return AuthorizationDecision(
        allowed=True,
        tenant_record_id=TENANT,
        actor_reference="keyverse_subject:operator-17",
        resource_reference="assignment_record:0198a412800070008000000000000070",
        policy_version_code="assignment-correction-v1",
        purpose_code="workforce_admin",
        operation_code="correct_record",
        resource_kind="assignment_record",
        requested_fields=FIELDS,
        authorized_fields=FIELDS,
        reason_code="access_permitted",
        next_action="Continue with only the authorized fields.",
    )


def test_consumer_validator_returns_detached_coherent_snapshot() -> None:
    """A durable consumer can revalidate exact current decision semantics."""
    snapshot = validate_authorization_decision(_decision())

    assert snapshot.allowed is True
    assert snapshot.tenant_record_id_int == TENANT.int
    assert snapshot.authorized_fields == FIELDS


def test_consumer_validator_rejects_non_decision_runtime_type() -> None:
    """Caller-defined unrelated objects cannot enter the durable evidence boundary."""
    with pytest.raises(TypeError, match="decision must be an AuthorizationDecision"):
        validate_authorization_decision(object())  # type: ignore[arg-type]


def test_consumer_validator_rejects_noncanonical_allow_next_action() -> None:
    """Post-construction mutation cannot change the canonical allow recovery contract."""
    decision = _decision()
    object.__setattr__(decision, "next_action", "Continue with any fields.")

    with pytest.raises(ValueError, match="allow decision must use the canonical next action"):
        validate_authorization_decision(decision)


def test_decision_rejects_unknown_denial_reason() -> None:
    """Denial evidence must use a governed reason rather than an arbitrary valid code."""
    with pytest.raises(ValueError, match="deny decision must use a known denial reason"):
        AuthorizationDecision(
            allowed=False,
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:operator-17",
            resource_reference="assignment_record:0198a412800070008000000000000070",
            policy_version_code="assignment-correction-v1",
            purpose_code="workforce_admin",
            operation_code="correct_record",
            resource_kind="assignment_record",
            requested_fields=FIELDS,
            authorized_fields=frozenset(),
            reason_code="policy_denied",
            next_action="Request another policy decision.",
        )


def test_decision_binds_denial_next_action_to_reason() -> None:
    """Known denial reasons cannot carry caller-selected recovery instructions."""
    with pytest.raises(ValueError, match="deny decision must use the canonical next action"):
        AuthorizationDecision(
            allowed=False,
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:operator-17",
            resource_reference="assignment_record:0198a412800070008000000000000070",
            policy_version_code="assignment-correction-v1",
            purpose_code="workforce_admin",
            operation_code="correct_record",
            resource_kind="assignment_record",
            requested_fields=FIELDS,
            authorized_fields=frozenset(),
            reason_code="purpose_not_allowed",
            next_action="Request another policy decision.",
        )
