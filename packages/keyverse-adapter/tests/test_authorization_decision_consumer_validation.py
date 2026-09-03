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
