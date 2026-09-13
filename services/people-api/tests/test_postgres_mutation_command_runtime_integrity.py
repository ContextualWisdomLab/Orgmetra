"""Adversarial runtime-integrity contracts for PostgreSQL People mutation commands."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDecision
from orgmetra_people_api.mutations import (
    AssignmentMutationCommand,
    EmploymentMutationCommand,
    PositionMutationCommand,
)
from orgmetra_people_api.postgres_mutations import PostgresPeopleMutationPort

TENANT = UUID("0198a412-7100-7000-8000-000000000001")
PERSON = UUID("0198a412-7100-7000-8000-000000000020")
EMPLOYMENT = UUID("0198a412-7100-7000-8000-000000000030")
EMPLOYMENT_VERSION = UUID("0198a412-7100-7000-8000-000000000031")
ORGANIZATION = UUID("0198a412-7100-7000-8000-000000000040")
JOB = UUID("0198a412-7100-7000-8000-000000000041")
POSITION = UUID("0198a412-7100-7000-8000-000000000050")
POSITION_VERSION = UUID("0198a412-7100-7000-8000-000000000051")
ASSIGNMENT = UUID("0198a412-7100-7000-8000-000000000060")
AUDIT = UUID("0198a412-7100-7000-8000-000000000070")
OUTBOX = UUID("0198a412-7100-7000-8000-000000000071")


class ForgedEmploymentMutationCommand(EmploymentMutationCommand):
    """Represent a validation-bypassing caller-defined employment command subtype."""


class ForgedPositionMutationCommand(PositionMutationCommand):
    """Represent a validation-bypassing caller-defined position command subtype."""


class ForgedAssignmentMutationCommand(AssignmentMutationCommand):
    """Represent a validation-bypassing caller-defined assignment command subtype."""


def _authorization(resource_kind: str, record_id: UUID) -> AuthorizationDecision:
    """Build one exact-scope allow decision for a People mutation target."""
    fields = frozenset({resource_kind})
    return AuthorizationDecision(
        allowed=True,
        tenant_record_id=TENANT,
        actor_reference="keyverse_subject:operator-17",
        resource_reference=f"{resource_kind}:{record_id.hex}",
        policy_version_code="people-mutation-v1",
        purpose_code="workforce_admin",
        operation_code="create_record",
        resource_kind=resource_kind,
        requested_fields=fields,
        authorized_fields=fields,
        reason_code="access_permitted",
        next_action="continue",
    )


def _forbidden_connection_factory() -> object:
    """Fail if a forged command crosses the persistence authority into database work."""
    raise AssertionError("database work must not begin for a forged People mutation command")


def test_postgres_employment_port_rejects_command_subclass_before_database_work() -> None:
    """Require the employment persistence authority to accept only its exact command type."""
    command = ForgedEmploymentMutationCommand(
        tenant_record_id=TENANT,
        person_record_id=PERSON,
        employment_record_id=EMPLOYMENT,
        employment_record_version_id=EMPLOYMENT_VERSION,
        audit_event_record_id=AUDIT,
        outbox_delivery_record_id=OUTBOX,
        employment_status_code="active",
        employment_concurrency_code="exclusive",
        effective_from=date(2026, 8, 22),
        confirmation_reference="human_confirmation:employment-1",
        evidence_version_code="employment-evidence-v1",
        idempotency_key="employment-runtime-guard",
    )
    port = PostgresPeopleMutationPort(_forbidden_connection_factory)

    with pytest.raises(TypeError, match="command must be an EmploymentMutationCommand"):
        port.create_employment(
            command=command,
            authorization=_authorization("employment_record", EMPLOYMENT),
        )


def test_postgres_position_port_rejects_command_subclass_before_database_work() -> None:
    """Require the position persistence authority to accept only its exact command type."""
    command = ForgedPositionMutationCommand(
        tenant_record_id=TENANT,
        organization_unit_id=ORGANIZATION,
        job_profile_id=JOB,
        position_record_id=POSITION,
        position_record_version_id=POSITION_VERSION,
        audit_event_record_id=AUDIT,
        outbox_delivery_record_id=OUTBOX,
        position_status_code="open",
        effective_from=date(2026, 8, 22),
        confirmation_reference="human_confirmation:position-1",
        evidence_version_code="position-evidence-v1",
        idempotency_key="position-runtime-guard",
    )
    port = PostgresPeopleMutationPort(_forbidden_connection_factory)

    with pytest.raises(TypeError, match="command must be a PositionMutationCommand"):
        port.create_position(
            command=command,
            authorization=_authorization("position_record", POSITION),
        )


def test_postgres_assignment_port_rejects_command_subclass_before_database_work() -> None:
    """Require the assignment persistence authority to accept only its exact command type."""
    command = ForgedAssignmentMutationCommand(
        tenant_record_id=TENANT,
        employment_record_id=EMPLOYMENT,
        person_record_id=PERSON,
        position_record_id=POSITION,
        assignment_record_id=ASSIGNMENT,
        audit_event_record_id=AUDIT,
        outbox_delivery_record_id=OUTBOX,
        allocation_ratio=Decimal("1.0000"),
        effective_from=date(2026, 8, 22),
        confirmation_reference="human_confirmation:assignment-1",
        evidence_version_code="assignment-evidence-v1",
        idempotency_key="assignment-runtime-guard",
    )
    port = PostgresPeopleMutationPort(_forbidden_connection_factory)

    with pytest.raises(TypeError, match="command must be an AssignmentMutationCommand"):
        port.create_assignment(
            command=command,
            authorization=_authorization("assignment_record", ASSIGNMENT),
        )
