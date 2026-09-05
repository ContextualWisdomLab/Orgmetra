"""Post-construction command-integrity regressions for the PostgreSQL People port."""

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
from test_postgres_people_mutations import FakeConnection, RECORDED_AT, ScriptedCursor

TENANT = UUID("0198a412-a700-7000-8000-000000000001")
PERSON = UUID("0198a412-a700-7000-8000-000000000020")
EMPLOYMENT = UUID("0198a412-a700-7000-8000-000000000030")
EMPLOYMENT_VERSION = UUID("0198a412-a700-7000-8000-000000000031")
ORGANIZATION = UUID("0198a412-a700-7000-8000-000000000040")
MUTATED_ORGANIZATION = UUID("0198a412-a700-7000-8000-000000000041")
JOB_PROFILE = UUID("0198a412-a700-7000-8000-000000000050")
POSITION = UUID("0198a412-a700-7000-8000-000000000060")
POSITION_VERSION = UUID("0198a412-a700-7000-8000-000000000061")
ASSIGNMENT = UUID("0198a412-a700-7000-8000-000000000070")
AUDIT_EVENT = UUID("0198a412-a700-7000-8000-000000000080")
OUTBOX = UUID("0198a412-a700-7000-8000-000000000081")


class _ExecutableUUID(UUID):
    """Trip if the PostgreSQL authority renders rewritten identity before validation."""

    @property
    def hex(self) -> str:
        """Fail if authorization-reference rendering runs before command validation."""
        raise AssertionError("rewritten UUID hex behavior must not execute")


def _authorization(*, resource_kind: str, record_id: UUID) -> AuthorizationDecision:
    """Build one exact authorization decision for an original mutation identity."""
    fields = frozenset({resource_kind})
    return AuthorizationDecision(
        allowed=True,
        tenant_record_id=TENANT,
        actor_reference="keyverse_subject:operator-227",
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
    """Fail if rewritten command evidence reaches PostgreSQL transaction work."""
    raise AssertionError("database work must not begin for a rewritten mutation command")


def test_postgres_employment_revalidates_exact_command_after_object_setattr_rewrite() -> None:
    """Reject rewritten Employment identity before callback or database work."""
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
        confirmation_reference="human_confirmation:post-construction-227-employment",
        evidence_version_code="employment-evidence-v1",
        idempotency_key="post-construction-runtime-227-employment",
    )
    object.__setattr__(
        command,
        "employment_record_id",
        _ExecutableUUID("0198a412-a700-7000-8000-000000000099"),
    )
    port = PostgresPeopleMutationPort(_forbidden_connection_factory)

    with pytest.raises(ValueError, match="employment_record_id must be an operational UUID"):
        port.create_employment(
            command=command,
            authorization=_authorization(resource_kind="employment_record", record_id=EMPLOYMENT),
        )


def test_postgres_position_revalidates_exact_command_after_object_setattr_rewrite() -> None:
    """Reject rewritten Position identity before callback or database work."""
    command = PositionMutationCommand(
        tenant_record_id=TENANT,
        organization_unit_id=ORGANIZATION,
        job_profile_id=JOB_PROFILE,
        position_record_id=POSITION,
        position_record_version_id=POSITION_VERSION,
        audit_event_record_id=AUDIT_EVENT,
        outbox_delivery_record_id=OUTBOX,
        position_status_code="open",
        effective_from=date(2026, 9, 5),
        confirmation_reference="human_confirmation:post-construction-227-position",
        evidence_version_code="position-evidence-v1",
        idempotency_key="post-construction-runtime-227-position",
    )
    object.__setattr__(
        command,
        "position_record_id",
        _ExecutableUUID("0198a412-a700-7000-8000-000000000098"),
    )
    port = PostgresPeopleMutationPort(_forbidden_connection_factory)

    with pytest.raises(ValueError, match="position_record_id must be an operational UUID"):
        port.create_position(
            command=command,
            authorization=_authorization(resource_kind="position_record", record_id=POSITION),
        )


def test_postgres_assignment_revalidates_exact_command_after_object_setattr_rewrite() -> None:
    """Reject rewritten Assignment identity before callback or database work."""
    command = AssignmentMutationCommand(
        tenant_record_id=TENANT,
        employment_record_id=EMPLOYMENT,
        person_record_id=PERSON,
        position_record_id=POSITION,
        assignment_record_id=ASSIGNMENT,
        audit_event_record_id=AUDIT_EVENT,
        outbox_delivery_record_id=OUTBOX,
        allocation_ratio=Decimal("1.0000"),
        effective_from=date(2026, 9, 5),
        confirmation_reference="human_confirmation:post-construction-227-assignment",
        evidence_version_code="assignment-evidence-v1",
        idempotency_key="post-construction-runtime-227-assignment",
    )
    object.__setattr__(
        command,
        "assignment_record_id",
        _ExecutableUUID("0198a412-a700-7000-8000-000000000097"),
    )
    port = PostgresPeopleMutationPort(_forbidden_connection_factory)

    with pytest.raises(ValueError, match="assignment_record_id must be an operational UUID"):
        port.create_assignment(
            command=command,
            authorization=_authorization(resource_kind="assignment_record", record_id=ASSIGNMENT),
        )


def test_postgres_position_detaches_validated_command_before_connection_factory_callback() -> None:
    """Keep one validated Position snapshot across the caller-owned connection callback."""
    command = PositionMutationCommand(
        tenant_record_id=TENANT,
        organization_unit_id=ORGANIZATION,
        job_profile_id=JOB_PROFILE,
        position_record_id=POSITION,
        position_record_version_id=POSITION_VERSION,
        audit_event_record_id=AUDIT_EVENT,
        outbox_delivery_record_id=OUTBOX,
        position_status_code="open",
        effective_from=date(2026, 9, 5),
        confirmation_reference="human_confirmation:post-construction-229-position",
        evidence_version_code="position-evidence-v1",
        idempotency_key="post-construction-runtime-229-position",
    )
    cursor = ScriptedCursor(
        [[], [(ORGANIZATION, JOB_PROFILE, RECORDED_AT)]],
        [],
    )
    connection = FakeConnection(cursor)

    def mutating_connection_factory() -> FakeConnection:
        """Rewrite the caller's still-valid command only after authorization has completed."""
        object.__setattr__(command, "organization_unit_id", MUTATED_ORGANIZATION)
        return connection

    port = PostgresPeopleMutationPort(mutating_connection_factory)
    result = port.create_position(
        command=command,
        authorization=_authorization(resource_kind="position_record", record_id=POSITION),
    )

    assert result.position_record_id == POSITION
    parent_query = next(
        execution for execution in cursor.executions if "FROM public.organization_unit AS organization" in execution[0]
    )
    assert parent_query[1] == (JOB_PROFILE, TENANT, ORGANIZATION)
    insert_position = next(
        execution for execution in cursor.executions if execution[0].startswith("INSERT INTO public.position_record (")
    )
    assert insert_position[1] is not None
    assert insert_position[1][2] == ORGANIZATION
