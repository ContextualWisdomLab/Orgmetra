"""Post-construction command-integrity regression for the PostgreSQL People port."""

from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDecision
from orgmetra_people_api.mutations import EmploymentMutationCommand
from orgmetra_people_api.postgres_mutations import PostgresPeopleMutationPort

TENANT = UUID("0198a412-a700-7000-8000-000000000001")
PERSON = UUID("0198a412-a700-7000-8000-000000000020")
EMPLOYMENT = UUID("0198a412-a700-7000-8000-000000000030")
EMPLOYMENT_VERSION = UUID("0198a412-a700-7000-8000-000000000031")
AUDIT_EVENT = UUID("0198a412-a700-7000-8000-000000000080")
OUTBOX = UUID("0198a412-a700-7000-8000-000000000081")


class _ExecutableUUID(UUID):
    """Trip if the PostgreSQL authority renders rewritten identity before validation."""

    @property
    def hex(self) -> str:
        """Fail if authorization-reference rendering runs before command validation."""
        raise AssertionError("rewritten UUID hex behavior must not execute")


def _authorization() -> AuthorizationDecision:
    """Build one exact authorization decision for the original employment identity."""
    fields = frozenset({"employment_record"})
    return AuthorizationDecision(
        allowed=True,
        tenant_record_id=TENANT,
        actor_reference="keyverse_subject:operator-227",
        resource_reference=f"employment_record:{EMPLOYMENT.hex}",
        policy_version_code="people-mutation-v1",
        purpose_code="workforce_admin",
        operation_code="create_record",
        resource_kind="employment_record",
        requested_fields=fields,
        authorized_fields=fields,
        reason_code="access_permitted",
        next_action="continue",
    )


def _forbidden_connection_factory() -> object:
    """Fail if rewritten command evidence reaches PostgreSQL transaction work."""
    raise AssertionError("database work must not begin for a rewritten mutation command")


def test_postgres_port_revalidates_exact_command_after_object_setattr_rewrite() -> None:
    """Reject rewritten command identity before callback or database work."""
    command = EmploymentMutationCommand(
        tenant_record_id=TENANT,
        person_record_id=PERSON,
        employment_record_id=EMPLOYMENT,
        employment_record_version_id=EMPLOYMENT_VERSION,
        audit_event_record_id=AUDIT_EVENT,
        outbox_delivery_record_id=OUTBOX,
        employment_status_code="active",
        employment_concurrency_code="exclusive",
        effective_from=date(2026, 9, 5),
        confirmation_reference="human_confirmation:post-construction-227",
        evidence_version_code="employment-evidence-v1",
        idempotency_key="post-construction-runtime-227",
    )
    object.__setattr__(
        command,
        "employment_record_id",
        _ExecutableUUID("0198a412-a700-7000-8000-000000000099"),
    )
    port = PostgresPeopleMutationPort(_forbidden_connection_factory)

    with pytest.raises(ValueError, match="employment_record_id must be an operational UUID"):
        port.create_employment(command=command, authorization=_authorization())
