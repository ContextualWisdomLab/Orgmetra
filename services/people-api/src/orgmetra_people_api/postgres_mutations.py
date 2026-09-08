"""Atomic PostgreSQL adapter for governed People employment, position, and assignment writes.

The adapter writes only Orgmetra-owned canonical HRIS relations. Employment and
assignment paths require a current ``candidate_worker_conversion_record`` and
never insert ``candidate_worker_link``. Every accepted write calls
``record_audit_outbox_event`` in the same tenant-bound transaction.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable
from uuid import UUID

from orgmetra_hris_kernel import (
    AssignmentFact,
    AuditOutboxEvent,
    DateInterval,
    EmploymentVersion,
    KernelError,
    PositionVersion,
    RecordedInterval,
    validate_assignment_write,
    validate_person_employment_exclusivity,
)
from orgmetra_keyverse_adapter import AuthorizationDecision, validate_authorization_decision

from orgmetra_people_api.mutations import (
    AssignmentMutationCommand,
    AssignmentMutationResult,
    EmploymentMutationCommand,
    EmploymentMutationResult,
    PeopleMutationIntegrityError,
    PeopleMutationNotFound,
    PositionMutationCommand,
    PositionMutationResult,
    command_route,
    idempotency_record_id,
    mutation_command_digest,
)

PostgresConnectionFactory = Callable[[], AbstractContextManager[Any]]

_READ_WRITE_SQL = "SET TRANSACTION ISOLATION LEVEL READ COMMITTED, READ WRITE"
_TENANT_CONTEXT_SQL = "SELECT pg_catalog.set_config('orgmetra.tenant_record_id', %s, true)"
_RECORD_AUDIT_OUTBOX_SQL = "SELECT public.record_audit_outbox_event(%s, %s, %s, %s, %s, %s)"
_POST_LOCK_RECORDED_AT_SQL = "SELECT pg_catalog.clock_timestamp()"
_MAX_UUID_INT = (1 << 128) - 1
_EMPLOYMENT_FIELDS = frozenset({"employment_record"})
_POSITION_FIELDS = frozenset({"position_record"})
_ASSIGNMENT_FIELDS = frozenset({"assignment_record"})

_CONVERSION_SQL = """
SELECT
    conversion.candidate_worker_conversion_record_id,
    pg_catalog.transaction_timestamp()
FROM public.candidate_worker_conversion_record AS conversion
WHERE conversion.tenant_record_id = %s
  AND conversion.person_record_id = %s
  AND conversion.recorded_to IS NULL
LIMIT 2
FOR UPDATE OF conversion
""".strip()

_EMPLOYMENT_VERSIONS_SQL = """
SELECT
    employment.employment_record_id,
    version.employment_record_version_id,
    employment.person_record_id,
    version.employment_status_code,
    version.employment_concurrency_code,
    version.effective_from,
    version.effective_to,
    version.recorded_from,
    version.recorded_to
FROM public.employment_record AS employment
JOIN public.employment_record_version AS version
  ON version.tenant_record_id = employment.tenant_record_id
 AND version.employment_record_id = employment.employment_record_id
WHERE employment.tenant_record_id = %s
  AND employment.person_record_id = %s
""".strip()

_INSERT_EMPLOYMENT_SQL = """
INSERT INTO public.employment_record (
    tenant_record_id,
    employment_record_id,
    person_record_id,
    recorded_from
) VALUES (%s, %s, %s, %s)
""".strip()

_INSERT_EMPLOYMENT_VERSION_SQL = """
INSERT INTO public.employment_record_version (
    tenant_record_id,
    employment_record_version_id,
    employment_record_id,
    employment_status_code,
    employment_concurrency_code,
    effective_from,
    recorded_from
) VALUES (%s, %s, %s, %s, %s, %s, %s)
""".strip()

_POSITION_PARENTS_SQL = """
SELECT
    organization.organization_unit_id,
    job.job_profile_id,
    pg_catalog.transaction_timestamp()
FROM public.organization_unit AS organization
JOIN public.job_profile AS job
  ON job.tenant_record_id = organization.tenant_record_id
 AND job.job_profile_id = %s
WHERE organization.tenant_record_id = %s
  AND organization.organization_unit_id = %s
LIMIT 2
""".strip()

_INSERT_POSITION_SQL = """
INSERT INTO public.position_record (
    tenant_record_id,
    position_record_id,
    organization_unit_id,
    job_profile_id,
    recorded_from
) VALUES (%s, %s, %s, %s, %s)
""".strip()

_INSERT_POSITION_VERSION_SQL = """
INSERT INTO public.position_record_version (
    tenant_record_id,
    position_record_version_id,
    position_record_id,
    position_status_code,
    effective_from,
    recorded_from
) VALUES (%s, %s, %s, %s, %s, %s)
""".strip()

_NAMED_EMPLOYMENT_VERSIONS_SQL = """
SELECT
    employment.employment_record_id,
    version.employment_record_version_id,
    employment.person_record_id,
    version.employment_status_code,
    version.employment_concurrency_code,
    version.effective_from,
    version.effective_to,
    version.recorded_from,
    version.recorded_to
FROM public.employment_record AS employment
JOIN public.employment_record_version AS version
  ON version.tenant_record_id = employment.tenant_record_id
 AND version.employment_record_id = employment.employment_record_id
WHERE employment.tenant_record_id = %s
  AND employment.employment_record_id = %s
""".strip()

_NAMED_POSITION_VERSIONS_SQL = """
SELECT
    version.position_record_id,
    version.position_record_version_id,
    version.position_status_code,
    version.effective_from,
    version.effective_to,
    version.recorded_from,
    version.recorded_to
FROM public.position_record AS position
JOIN public.position_record_version AS version
  ON version.tenant_record_id = position.tenant_record_id
 AND version.position_record_id = position.position_record_id
WHERE position.tenant_record_id = %s
  AND position.position_record_id = %s
FOR UPDATE OF position
""".strip()

_EXISTING_ASSIGNMENTS_SQL = """
SELECT
    assignment.assignment_record_id,
    assignment.employment_record_id,
    assignment.person_record_id,
    assignment.position_record_id,
    assignment.allocation_ratio,
    assignment.effective_from,
    assignment.effective_to,
    assignment.recorded_from,
    assignment.recorded_to
FROM public.assignment_record AS assignment
WHERE assignment.tenant_record_id = %s
  AND (
        assignment.employment_record_id = %s
     OR assignment.position_record_id = %s
  )
""".strip()

_INSERT_ASSIGNMENT_SQL = """
INSERT INTO public.assignment_record (
    tenant_record_id,
    assignment_record_id,
    employment_record_id,
    person_record_id,
    position_record_id,
    allocation_ratio,
    effective_from,
    recorded_from
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
""".strip()

_LOOKUP_IDEMPOTENCY_SQL = """
WITH command_key AS (
    SELECT
        %s::uuid AS tenant_record_id,
        %s::text AS command_route,
        %s::text AS idempotency_key
)
SELECT pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended(
        command_key.tenant_record_id::text
        || E'\\x1f' || command_key.command_route
        || E'\\x1f' || command_key.idempotency_key,
        0
    )
)
FROM command_key
""".strip()

_READ_IDEMPOTENCY_SQL = """
SELECT
    replay.created_record_id,
    replay.command_digest
FROM public.people_mutation_idempotency_record AS replay
WHERE replay.tenant_record_id = %s
  AND replay.command_route = %s
  AND replay.idempotency_key = %s
LIMIT 2
""".strip()

_INSERT_IDEMPOTENCY_SQL = """
INSERT INTO public.people_mutation_idempotency_record (
    tenant_record_id,
    people_mutation_idempotency_record_id,
    command_route,
    idempotency_key,
    command_digest,
    created_record_id,
    recorded_from
) VALUES (%s, %s, %s, %s, %s, %s, pg_catalog.transaction_timestamp())
""".strip()


def _is_operational_uuid(value: object) -> bool:
    """Return whether a value is an Orgmetra operational UUID."""
    return isinstance(value, UUID) and value.int not in (0, _MAX_UUID_INT)


def _is_aware_datetime(value: object) -> bool:
    """Return whether a value is a timezone-aware datetime with a real offset."""
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _replayed_record_id(
    cursor: Any,
    *,
    command: EmploymentMutationCommand | PositionMutationCommand | AssignmentMutationCommand,
    authorization: AuthorizationDecision,
) -> UUID | None:
    """Serialize one key, then return its committed record identity when present."""
    route = command_route(command)
    digest = mutation_command_digest(command=command, authorization=authorization)
    key_parameters = (command.tenant_record_id, route, command.idempotency_key)
    cursor.execute(_LOOKUP_IDEMPOTENCY_SQL, key_parameters)
    cursor.execute(_READ_IDEMPOTENCY_SQL, key_parameters)
    rows = cursor.fetchmany(2)
    if not rows:
        return None
    if len(rows) != 1 or len(rows[0]) != 2:
        raise PeopleMutationIntegrityError("idempotency row is invalid")
    created_record_id, stored_digest = rows[0]
    if not _is_operational_uuid(created_record_id) or not isinstance(stored_digest, str):
        raise PeopleMutationIntegrityError("idempotency row is invalid")
    if stored_digest != digest:
        raise PeopleMutationIntegrityError("idempotency key is bound to a different command")
    assert isinstance(created_record_id, UUID)
    return created_record_id


def _record_idempotency(
    cursor: Any,
    *,
    command: EmploymentMutationCommand | PositionMutationCommand | AssignmentMutationCommand,
    authorization: AuthorizationDecision,
    created_record_id: UUID,
) -> None:
    """Persist the command digest with the created HRIS identity in the current transaction."""
    route = command_route(command)
    cursor.execute(
        _INSERT_IDEMPOTENCY_SQL,
        (
            command.tenant_record_id,
            idempotency_record_id(
                tenant_record_id=command.tenant_record_id,
                command_route_value=route,
                idempotency_key=command.idempotency_key,
            ),
            route,
            command.idempotency_key,
            mutation_command_digest(command=command, authorization=authorization),
            created_record_id,
        ),
    )


def _require_authorization(
    *,
    authorization: object,
    tenant_record_id: UUID,
    resource_reference: str,
    resource_kind: str,
    requested_fields: frozenset[str],
) -> AuthorizationDecision:
    """Revalidate and detach the exact allow decision before opening a transaction."""
    try:
        snapshot = validate_authorization_decision(authorization)  # type: ignore[arg-type]
    except (TypeError, ValueError) as error:
        raise PeopleMutationIntegrityError("people mutation requires coherent authorization evidence") from error
    if (
        not snapshot.allowed
        or snapshot.tenant_record_id_int != tenant_record_id.int
        or snapshot.resource_reference != resource_reference
        or snapshot.resource_kind != resource_kind
        or snapshot.operation_code != "create_record"
        or snapshot.requested_fields != requested_fields
        or snapshot.authorized_fields != requested_fields
    ):
        raise PeopleMutationIntegrityError("people mutation authorization does not match the exact record")
    return AuthorizationDecision(
        allowed=snapshot.allowed,
        tenant_record_id=UUID(int=snapshot.tenant_record_id_int),
        actor_reference=snapshot.actor_reference,
        resource_reference=snapshot.resource_reference,
        policy_version_code=snapshot.policy_version_code,
        purpose_code=snapshot.purpose_code,
        operation_code=snapshot.operation_code,
        resource_kind=snapshot.resource_kind,
        requested_fields=snapshot.requested_fields,
        authorized_fields=snapshot.authorized_fields,
        reason_code=snapshot.reason_code,
        next_action=snapshot.next_action,
    )


def _record_audit(
    cursor: Any,
    *,
    command_tenant: UUID,
    event_id: UUID,
    outbox_id: UUID,
    event: AuditOutboxEvent,
) -> None:
    """Persist the canonical audit/outbox pair inside the current transaction."""
    cursor.execute(
        _RECORD_AUDIT_OUTBOX_SQL,
        (
            command_tenant,
            event_id,
            outbox_id,
            event.canonical_json(),
            event.content_digest(),
            "orgmetra_domain_events",
        ),
    )


def _employment_version_from_row(tenant_record_id: UUID, row: tuple[object, ...]) -> EmploymentVersion:
    """Reconstruct one employment version used by the exclusivity kernel."""
    if len(row) != 9:
        raise PeopleMutationIntegrityError("employment version row has an invalid shape")
    (
        employment_record_id,
        employment_record_version_id,
        person_record_id,
        status_code,
        concurrency_code,
        effective_from,
        effective_to,
        recorded_from,
        recorded_to,
    ) = row
    if (
        not _is_operational_uuid(employment_record_id)
        or not _is_operational_uuid(employment_record_version_id)
        or not _is_operational_uuid(person_record_id)
        or not isinstance(status_code, str)
        or not isinstance(concurrency_code, str)
        or type(effective_from) is not date
        or (effective_to is not None and type(effective_to) is not date)
        or not _is_aware_datetime(recorded_from)
        or (recorded_to is not None and not _is_aware_datetime(recorded_to))
    ):
        raise PeopleMutationIntegrityError("employment version row is invalid")
    assert isinstance(employment_record_id, UUID)
    assert isinstance(employment_record_version_id, UUID)
    assert isinstance(person_record_id, UUID)
    assert isinstance(effective_from, date)
    assert isinstance(recorded_from, datetime)
    return EmploymentVersion(
        tenant_record_id=tenant_record_id,
        employment_record_id=employment_record_id,
        employment_record_version_id=employment_record_version_id,
        person_record_id=person_record_id,
        employment_status_code=status_code,
        effective=DateInterval(effective_from, effective_to if isinstance(effective_to, date) else None),
        recorded=RecordedInterval(recorded_from, recorded_to if isinstance(recorded_to, datetime) else None),
        employment_concurrency_code=concurrency_code,
    )


def _position_version_from_row(tenant_record_id: UUID, row: tuple[object, ...]) -> PositionVersion:
    """Reconstruct one position version used by the assignment kernel."""
    if len(row) != 7:
        raise PeopleMutationIntegrityError("position version row has an invalid shape")
    (
        position_record_id,
        position_record_version_id,
        status_code,
        effective_from,
        effective_to,
        recorded_from,
        recorded_to,
    ) = row
    if (
        not _is_operational_uuid(position_record_id)
        or not _is_operational_uuid(position_record_version_id)
        or not isinstance(status_code, str)
        or type(effective_from) is not date
        or (effective_to is not None and type(effective_to) is not date)
        or not _is_aware_datetime(recorded_from)
        or (recorded_to is not None and not _is_aware_datetime(recorded_to))
    ):
        raise PeopleMutationIntegrityError("position version row is invalid")
    assert isinstance(position_record_id, UUID)
    assert isinstance(position_record_version_id, UUID)
    assert isinstance(effective_from, date)
    assert isinstance(recorded_from, datetime)
    return PositionVersion(
        tenant_record_id=tenant_record_id,
        position_record_id=position_record_id,
        position_record_version_id=position_record_version_id,
        position_status_code=status_code,
        effective=DateInterval(effective_from, effective_to if isinstance(effective_to, date) else None),
        recorded=RecordedInterval(recorded_from, recorded_to if isinstance(recorded_to, datetime) else None),
    )


def _assignment_from_row(tenant_record_id: UUID, row: tuple[object, ...]) -> AssignmentFact:
    """Reconstruct one assignment fact used by the assignment kernel."""
    if len(row) != 9:
        raise PeopleMutationIntegrityError("assignment row has an invalid shape")
    (
        assignment_record_id,
        employment_record_id,
        person_record_id,
        position_record_id,
        allocation_ratio,
        effective_from,
        effective_to,
        recorded_from,
        recorded_to,
    ) = row
    if (
        not _is_operational_uuid(assignment_record_id)
        or not _is_operational_uuid(employment_record_id)
        or not _is_operational_uuid(person_record_id)
        or not _is_operational_uuid(position_record_id)
        or not isinstance(allocation_ratio, Decimal)
        or type(effective_from) is not date
        or (effective_to is not None and type(effective_to) is not date)
        or not _is_aware_datetime(recorded_from)
        or (recorded_to is not None and not _is_aware_datetime(recorded_to))
    ):
        raise PeopleMutationIntegrityError("assignment row is invalid")
    assert isinstance(assignment_record_id, UUID)
    assert isinstance(employment_record_id, UUID)
    assert isinstance(person_record_id, UUID)
    assert isinstance(position_record_id, UUID)
    assert isinstance(effective_from, date)
    assert isinstance(recorded_from, datetime)
    return AssignmentFact(
        tenant_record_id=tenant_record_id,
        assignment_record_id=assignment_record_id,
        employment_record_id=employment_record_id,
        person_record_id=person_record_id,
        position_record_id=position_record_id,
        allocation_ratio=allocation_ratio,
        effective=DateInterval(effective_from, effective_to if isinstance(effective_to, date) else None),
        recorded=RecordedInterval(recorded_from, recorded_to if isinstance(recorded_to, datetime) else None),
    )


def _require_one_conversion(rows: list[tuple[object, ...]]) -> tuple[UUID, datetime]:
    """Require exactly one current conversion row and a usable transaction timestamp."""
    if not rows:
        raise PeopleMutationIntegrityError("person has no governed candidate-worker conversion")
    if len(rows) != 1:
        raise PeopleMutationIntegrityError("multiple candidate-worker conversions matched the person")
    if len(rows[0]) != 2:
        raise PeopleMutationIntegrityError("conversion row has an invalid shape")
    conversion_id, recorded_at = rows[0]
    if not _is_operational_uuid(conversion_id) or not _is_aware_datetime(recorded_at):
        raise PeopleMutationIntegrityError("conversion identity or transaction time is invalid")
    assert isinstance(conversion_id, UUID)
    assert isinstance(recorded_at, datetime)
    return conversion_id, recorded_at


def _post_lock_recorded_at(cursor: Any) -> datetime:
    """Read one database clock instant only after the relevant conflict lock is held."""
    cursor.execute(_POST_LOCK_RECORDED_AT_SQL)
    rows = cursor.fetchmany(2)
    if len(rows) != 1 or len(rows[0]) != 1 or not _is_aware_datetime(rows[0][0]):
        raise PeopleMutationIntegrityError("post-lock database clock row is invalid")
    recorded_at = rows[0][0]
    assert isinstance(recorded_at, datetime)
    return recorded_at


@dataclass(frozen=True, slots=True)
class PostgresPeopleMutationPort:
    """Persist People mutations and governance evidence in one DB transaction.

    ``connection_factory`` must return a DB-API connection context manager whose
    successful exit commits and exceptional exit rolls back.
    """

    connection_factory: PostgresConnectionFactory

    def __post_init__(self) -> None:
        """Reject unusable database factories before protected mutation is attempted."""
        if not callable(self.connection_factory):
            raise TypeError("connection_factory must be callable")

    def create_employment(
        self,
        *,
        command: EmploymentMutationCommand,
        authorization: AuthorizationDecision,
    ) -> EmploymentMutationResult:
        """Persist one employment after conversion and exclusivity checks."""
        if not isinstance(command, EmploymentMutationCommand):
            raise TypeError("command must be an EmploymentMutationCommand")
        decision = _require_authorization(
            authorization=authorization,
            tenant_record_id=command.tenant_record_id,
            resource_reference=f"employment_record:{command.employment_record_id.hex}",
            resource_kind="employment_record",
            requested_fields=_EMPLOYMENT_FIELDS,
        )
        with self.connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(_READ_WRITE_SQL)
                cursor.execute(_TENANT_CONTEXT_SQL, (str(command.tenant_record_id),))
                replayed = _replayed_record_id(cursor, command=command, authorization=decision)
                if replayed is not None:
                    return EmploymentMutationResult(employment_record_id=replayed)
                cursor.execute(_CONVERSION_SQL, (command.tenant_record_id, command.person_record_id))
                _require_one_conversion(cursor.fetchmany(2))
                recorded_at = _post_lock_recorded_at(cursor)
                cursor.execute(
                    _EMPLOYMENT_VERSIONS_SQL,
                    (command.tenant_record_id, command.person_record_id),
                )
                existing = [
                    _employment_version_from_row(command.tenant_record_id, row)
                    for row in cursor.fetchall()
                ]
                proposed = EmploymentVersion(
                    tenant_record_id=command.tenant_record_id,
                    employment_record_id=command.employment_record_id,
                    employment_record_version_id=command.employment_record_version_id,
                    person_record_id=command.person_record_id,
                    employment_status_code=command.employment_status_code,
                    effective=DateInterval(command.effective_from),
                    recorded=RecordedInterval(recorded_at),
                    employment_concurrency_code=command.employment_concurrency_code,
                )
                try:
                    validate_person_employment_exclusivity(
                        [*existing, proposed],
                        tenant_record_id=command.tenant_record_id,
                        person_record_id=command.person_record_id,
                        known_at=recorded_at,
                    )
                except KernelError as error:
                    raise PeopleMutationIntegrityError(str(error)) from error
                cursor.execute(
                    _INSERT_EMPLOYMENT_SQL,
                    (
                        command.tenant_record_id,
                        command.employment_record_id,
                        command.person_record_id,
                        recorded_at,
                    ),
                )
                cursor.execute(
                    _INSERT_EMPLOYMENT_VERSION_SQL,
                    (
                        command.tenant_record_id,
                        command.employment_record_version_id,
                        command.employment_record_id,
                        command.employment_status_code,
                        command.employment_concurrency_code,
                        command.effective_from,
                        recorded_at,
                    ),
                )
                _record_audit(
                    cursor,
                    command_tenant=command.tenant_record_id,
                    event_id=command.audit_event_record_id,
                    outbox_id=command.outbox_delivery_record_id,
                    event=AuditOutboxEvent(
                        event_id=command.audit_event_record_id,
                        tenant_record_id=command.tenant_record_id,
                        source_service="people_api",
                        event_type="orgmetra.people.employment_created",
                        resource_reference=f"employment_record:{command.employment_record_id}",
                        actor_reference=decision.actor_reference,
                        purpose_code=decision.purpose_code,
                        reason_code="employment_record_created",
                        evidence_version_code=command.evidence_version_code,
                        result_code="employment_created",
                        occurred_at=recorded_at,
                        high_impact=True,
                        confirmation_reference=command.confirmation_reference,
                    ),
                )
                _record_idempotency(
                    cursor,
                    command=command,
                    authorization=decision,
                    created_record_id=command.employment_record_id,
                )
        return EmploymentMutationResult(employment_record_id=command.employment_record_id)

    def create_position(
        self,
        *,
        command: PositionMutationCommand,
        authorization: AuthorizationDecision,
    ) -> PositionMutationResult:
        """Persist one position after organization and job parent checks."""
        if not isinstance(command, PositionMutationCommand):
            raise TypeError("command must be a PositionMutationCommand")
        decision = _require_authorization(
            authorization=authorization,
            tenant_record_id=command.tenant_record_id,
            resource_reference=f"position_record:{command.position_record_id.hex}",
            resource_kind="position_record",
            requested_fields=_POSITION_FIELDS,
        )
        with self.connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(_READ_WRITE_SQL)
                cursor.execute(_TENANT_CONTEXT_SQL, (str(command.tenant_record_id),))
                replayed = _replayed_record_id(cursor, command=command, authorization=decision)
                if replayed is not None:
                    return PositionMutationResult(position_record_id=replayed)
                cursor.execute(
                    _POSITION_PARENTS_SQL,
                    (command.job_profile_id, command.tenant_record_id, command.organization_unit_id),
                )
                rows = cursor.fetchmany(2)
                if not rows:
                    raise PeopleMutationNotFound("organization unit or job profile was not found")
                if len(rows) != 1 or len(rows[0]) != 3:
                    raise PeopleMutationIntegrityError("position parent row is invalid")
                organization_unit_id, job_profile_id, recorded_at = rows[0]
                if (
                    organization_unit_id != command.organization_unit_id
                    or job_profile_id != command.job_profile_id
                    or not _is_aware_datetime(recorded_at)
                ):
                    raise PeopleMutationIntegrityError("position parent identity is invalid")
                assert isinstance(recorded_at, datetime)
                cursor.execute(
                    _INSERT_POSITION_SQL,
                    (
                        command.tenant_record_id,
                        command.position_record_id,
                        command.organization_unit_id,
                        command.job_profile_id,
                        recorded_at,
                    ),
                )
                cursor.execute(
                    _INSERT_POSITION_VERSION_SQL,
                    (
                        command.tenant_record_id,
                        command.position_record_version_id,
                        command.position_record_id,
                        command.position_status_code,
                        command.effective_from,
                        recorded_at,
                    ),
                )
                _record_audit(
                    cursor,
                    command_tenant=command.tenant_record_id,
                    event_id=command.audit_event_record_id,
                    outbox_id=command.outbox_delivery_record_id,
                    event=AuditOutboxEvent(
                        event_id=command.audit_event_record_id,
                        tenant_record_id=command.tenant_record_id,
                        source_service="people_api",
                        event_type="orgmetra.people.position_created",
                        resource_reference=f"position_record:{command.position_record_id}",
                        actor_reference=decision.actor_reference,
                        purpose_code=decision.purpose_code,
                        reason_code="position_record_created",
                        evidence_version_code=command.evidence_version_code,
                        result_code="position_created",
                        occurred_at=recorded_at,
                        high_impact=True,
                        confirmation_reference=command.confirmation_reference,
                    ),
                )
                _record_idempotency(
                    cursor,
                    command=command,
                    authorization=decision,
                    created_record_id=command.position_record_id,
                )
        return PositionMutationResult(position_record_id=command.position_record_id)

    def create_assignment(
        self,
        *,
        command: AssignmentMutationCommand,
        authorization: AuthorizationDecision,
    ) -> AssignmentMutationResult:
        """Persist one assignment after conversion and kernel coverage checks."""
        if not isinstance(command, AssignmentMutationCommand):
            raise TypeError("command must be an AssignmentMutationCommand")
        decision = _require_authorization(
            authorization=authorization,
            tenant_record_id=command.tenant_record_id,
            resource_reference=f"assignment_record:{command.assignment_record_id.hex}",
            resource_kind="assignment_record",
            requested_fields=_ASSIGNMENT_FIELDS,
        )
        with self.connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(_READ_WRITE_SQL)
                cursor.execute(_TENANT_CONTEXT_SQL, (str(command.tenant_record_id),))
                replayed = _replayed_record_id(cursor, command=command, authorization=decision)
                if replayed is not None:
                    return AssignmentMutationResult(assignment_record_id=replayed)
                cursor.execute(_CONVERSION_SQL, (command.tenant_record_id, command.person_record_id))
                _require_one_conversion(cursor.fetchmany(2))
                cursor.execute(
                    _NAMED_EMPLOYMENT_VERSIONS_SQL,
                    (command.tenant_record_id, command.employment_record_id),
                )
                employment_versions = [
                    _employment_version_from_row(command.tenant_record_id, row)
                    for row in cursor.fetchall()
                ]
                cursor.execute(
                    _NAMED_POSITION_VERSIONS_SQL,
                    (command.tenant_record_id, command.position_record_id),
                )
                position_versions = [
                    _position_version_from_row(command.tenant_record_id, row)
                    for row in cursor.fetchall()
                ]
                recorded_at = _post_lock_recorded_at(cursor)
                cursor.execute(
                    _EXISTING_ASSIGNMENTS_SQL,
                    (
                        command.tenant_record_id,
                        command.employment_record_id,
                        command.position_record_id,
                    ),
                )
                existing_assignments = [
                    _assignment_from_row(command.tenant_record_id, row)
                    for row in cursor.fetchall()
                ]
                proposed = AssignmentFact(
                    tenant_record_id=command.tenant_record_id,
                    assignment_record_id=command.assignment_record_id,
                    employment_record_id=command.employment_record_id,
                    person_record_id=command.person_record_id,
                    position_record_id=command.position_record_id,
                    allocation_ratio=command.allocation_ratio,
                    effective=DateInterval(command.effective_from),
                    recorded=RecordedInterval(recorded_at),
                )
                try:
                    validate_assignment_write(
                        proposed,
                        [*existing_assignments, proposed],
                        employment_versions,
                        position_versions,
                        known_at=recorded_at,
                    )
                except KernelError as error:
                    raise PeopleMutationIntegrityError(str(error)) from error
                cursor.execute(
                    _INSERT_ASSIGNMENT_SQL,
                    (
                        command.tenant_record_id,
                        command.assignment_record_id,
                        command.employment_record_id,
                        command.person_record_id,
                        command.position_record_id,
                        command.allocation_ratio,
                        command.effective_from,
                        recorded_at,
                    ),
                )
                _record_audit(
                    cursor,
                    command_tenant=command.tenant_record_id,
                    event_id=command.audit_event_record_id,
                    outbox_id=command.outbox_delivery_record_id,
                    event=AuditOutboxEvent(
                        event_id=command.audit_event_record_id,
                        tenant_record_id=command.tenant_record_id,
                        source_service="people_api",
                        event_type="orgmetra.people.assignment_created",
                        resource_reference=f"assignment_record:{command.assignment_record_id}",
                        actor_reference=decision.actor_reference,
                        purpose_code=decision.purpose_code,
                        reason_code="assignment_record_created",
                        evidence_version_code=command.evidence_version_code,
                        result_code="assignment_created",
                        occurred_at=recorded_at,
                        high_impact=True,
                        confirmation_reference=command.confirmation_reference,
                    ),
                )
                _record_idempotency(
                    cursor,
                    command=command,
                    authorization=decision,
                    created_record_id=command.assignment_record_id,
                )
        return AssignmentMutationResult(assignment_record_id=command.assignment_record_id)