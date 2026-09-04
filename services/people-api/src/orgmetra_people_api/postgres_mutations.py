"""Atomic PostgreSQL adapter for governed People employment, position, and assignment writes.

The adapter writes only Orgmetra-owned canonical HRIS relations. Employment and
assignment paths require a current ``candidate_worker_conversion_record`` and
never insert ``candidate_worker_link``. Every accepted write calls
``record_audit_outbox_event`` in the same tenant-bound transaction.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Callable
from uuid import UUID
from zoneinfo import ZoneInfo

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
from orgmetra_keyverse_adapter import AuthorizationDecision

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
    """Return whether a value is an exact operational UUID."""
    return type(value) is UUID and value.int not in (0, _MAX_UUID_INT)


def _is_aware_datetime(value: object) -> bool:
    """Return whether durable time is exact and backed by an inert standard provider."""
    if type(value) is not datetime or value.tzinfo is None:
        return False
    if type(value.tzinfo) not in (timezone, ZoneInfo):
        return False
    return value.utcoffset() is not None


def _unpack_fixed_rows(
    value: object,
    *,
    row_width: int,
    error_message: str,
) -> tuple[tuple[object, ...], ...]:
    """Detach exact built-in DB row containers before projection values are inspected."""
    if type(value) not in (list, tuple):
        raise PeopleMutationIntegrityError(error_message)
    detached: list[tuple[object, ...]] = []
    for row in value:
        if type(row) not in (list, tuple) or len(row) != row_width:
            raise PeopleMutationIntegrityError(error_message)
        detached.append(tuple(row))
    return tuple(detached)


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
    rows = _unpack_fixed_rows(
        cursor.fetchmany(2),
        row_width=2,
        error_message="idempotency row is invalid",
    )
    if not rows:
        return None
    if len(rows) != 1:
        raise PeopleMutationIntegrityError("idempotency row is invalid")
    created_record_id, stored_digest = rows[0]
    if not _is_operational_uuid(created_record_id) or type(stored_digest) is not str:
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
    """Require an exact allow decision for the intended mutation target."""
    if type(authorization) is not AuthorizationDecision:
        raise PeopleMutationIntegrityError("people mutation requires a typed authorization decision")
    if (
        not authorization.allowed
        or authorization.tenant_record_id != tenant_record_id
        or authorization.resource_reference != resource_reference
        or authorization.resource_kind != resource_kind
        or authorization.operation_code != "create_record"
        or authorization.requested_fields != requested_fields
        or authorization.authorized_fields != requested_fields
    ):
        raise PeopleMutationIntegrityError("people mutation authorization does not match the exact record")
    return authorization


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
        or type(status_code) is not str
        or type(concurrency_code) is not str
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
        or type(status_code) is not str
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


def _require_one_conversion(rows: object) -> tuple[UUID, datetime]:
    """Require exactly one current conversion row and a usable transaction timestamp."""
    detached = _unpack_fixed_rows(
        rows,
        row_width=2,
        error_message="conversion row has an invalid shape",
    )
    if not detached:
        raise PeopleMutationIntegrityError("person has no governed candidate-worker conversion")
    if len(detached) != 1:
        raise PeopleMutationIntegrityError("multiple candidate-worker conversions matched the person")
    conversion_id, recorded_at = detached[0]
    if not _is_operational_uuid(conversion_id) or not _is_aware_datetime(recorded_at):
        raise PeopleMutationIntegrityError("conversion identity or transaction time is invalid")
    assert isinstance(conversion_id, UUID)
    assert isinstance(recorded_at, datetime)
    return conversion_id, recorded_at


def _post_lock_recorded_at(cursor: Any) -> datetime:
    """Read one database clock instant only after the relevant conflict lock is held."""
    cursor.execute(_POST_LOCK_RECORDED_AT_SQL)
    rows = _unpack_fixed_rows(
        cursor.fetchmany(2),
        row_width=1,
        error_message="post-lock database clock row is invalid",
    )
    if len(rows) != 1 or not _is_aware_datetime(rows[0][0]):
        raise PeopleMutationIntegrityError("post-lock database clock row is invalid")
    recorded_at = rows[0][0]
    assert isinstance(recorded_at, datetime)
    return recorded_at


@dataclass(frozen=True, slots=True)
class PostgresPeopleMutationPort:
    """Persist People mutations and governance evidence in one DB transaction.

    ``connection_factory`` must return a DB-API connection context manager whose
    successful exit commits and exceptional exit rolls back. Fixed query
    projections must arrive as exact built-in list/tuple batches and rows;
    custom row factories must normalize before this trust boundary.
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
        if type(command) is not EmploymentMutationCommand:
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
                existing_rows = _unpack_fixed_rows(
                    cursor.fetchall(),
                    row_width=9,
                    error_message="employment version row has an invalid shape",
                )
                existing = [
                    _employment_version_from_row(command.tenant_record_id, row)
                    for row in existing_rows
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
        if type(command) is not PositionMutationCommand:
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
                rows = _unpack_fixed_rows(
                    cursor.fetchmany(2),
                    row_width=3,
                    error_message="position parent row is invalid",
                )
                if not rows:
                    raise PeopleMutationNotFound("organization unit or job profile was not found")
                if len(rows) != 1:
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
        if type(command) is not AssignmentMutationCommand:
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
                employment_rows = _unpack_fixed_rows(
                    cursor.fetchall(),
                    row_width=9,
                    error_message="employment version row has an invalid shape",
                )
                employment_versions = [
                    _employment_version_from_row(command.tenant_record_id, row)
                    for row in employment_rows
                ]
                cursor.execute(
                    _NAMED_POSITION_VERSIONS_SQL,
                    (command.tenant_record_id, command.position_record_id),
                )
                position_rows = _unpack_fixed_rows(
                    cursor.fetchall(),
                    row_width=7,
                    error_message="position version row has an invalid shape",
                )
                position_versions = [
                    _position_version_from_row(command.tenant_record_id, row)
                    for row in position_rows
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
                assignment_rows = _unpack_fixed_rows(
                    cursor.fetchall(),
                    row_width=9,
                    error_message="assignment row has an invalid shape",
                )
                existing_assignments = [
                    _assignment_from_row(command.tenant_record_id, row)
                    for row in assignment_rows
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
