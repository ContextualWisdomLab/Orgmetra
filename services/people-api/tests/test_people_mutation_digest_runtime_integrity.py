"""Runtime-integrity regressions for People mutation idempotency evidence."""

from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDecision
from orgmetra_people_api.mutations import (
    EmploymentMutationCommand,
    idempotency_record_id,
    mutation_command_digest,
)

TENANT = UUID("0198a412-8000-7000-8000-000000000001")


class _ForgedUUID(UUID):
    """Attempt to select idempotency identity with caller-controlled string rendering."""

    def __str__(self) -> str:
        """Render another tenant identifier while retaining the original UUID value."""
        return "0198a412-8000-7000-8000-ffffffffffff"


class _ForgedDecision(AuthorizationDecision):
    """Attempt to rewrite immutable authorization evidence during digest construction."""

    def __getattribute__(self, name: str) -> object:
        """Forge only the actor value observed by digest construction."""
        if name == "actor_reference":
            return "keyverse_subject:forged-actor"
        return super().__getattribute__(name)


def _command() -> EmploymentMutationCommand:
    """Build one exact employment mutation command."""
    return EmploymentMutationCommand(
        tenant_record_id=TENANT,
        person_record_id=UUID("0198a412-8000-7000-8000-000000000020"),
        employment_record_id=UUID("0198a412-8000-7000-8000-000000000030"),
        employment_record_version_id=UUID("0198a412-8000-7000-8000-000000000031"),
        audit_event_record_id=UUID("0198a412-8000-7000-8000-000000000080"),
        outbox_delivery_record_id=UUID("0198a412-8000-7000-8000-000000000081"),
        employment_status_code="active",
        employment_concurrency_code="exclusive",
        effective_from=date(2026, 8, 21),
        confirmation_reference="human_confirmation:runtime-21",
        evidence_version_code="decision_evidence_set:v1",
        idempotency_key="mutation-runtime-key-21",
    )


def _decision() -> AuthorizationDecision:
    """Build one exact authorized mutation decision."""
    employment_id = _command().employment_record_id
    return AuthorizationDecision(
        allowed=True,
        tenant_record_id=TENANT,
        actor_reference="keyverse_subject:operator-21",
        resource_reference=f"employment_record:{employment_id.hex}",
        policy_version_code="people-mutation-v1",
        purpose_code="workforce_admin",
        operation_code="create_record",
        resource_kind="employment_record",
        requested_fields=frozenset({"employment_record"}),
        authorized_fields=frozenset({"employment_record"}),
        reason_code="access_permitted",
        next_action="Continue with only the authorized fields.",
    )


def test_idempotency_record_id_rejects_uuid_subclass_before_tenant_key_derivation() -> None:
    """Idempotency identity cannot be derived from caller-controlled tenant rendering."""
    forged = _ForgedUUID("0198a412-8000-7000-8000-000000000001")
    with pytest.raises(ValueError, match="tenant_record_id must be an operational UUID"):
        idempotency_record_id(
            tenant_record_id=forged,
            command_route_value="employment-records",
            idempotency_key="mutation-runtime-key-21",
        )


def test_mutation_digest_rejects_authorization_decision_subclasses() -> None:
    """Digest evidence must use the exact decision produced by the authorization adapter."""
    base = _decision()
    forged = _ForgedDecision(
        allowed=base.allowed,
        tenant_record_id=base.tenant_record_id,
        actor_reference=base.actor_reference,
        resource_reference=base.resource_reference,
        policy_version_code=base.policy_version_code,
        purpose_code=base.purpose_code,
        operation_code=base.operation_code,
        resource_kind=base.resource_kind,
        requested_fields=base.requested_fields,
        authorized_fields=base.authorized_fields,
        reason_code=base.reason_code,
        next_action=base.next_action,
    )
    with pytest.raises(TypeError, match="authorization must be an AuthorizationDecision"):
        mutation_command_digest(command=_command(), authorization=forged)
