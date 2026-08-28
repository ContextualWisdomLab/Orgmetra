"""PostgreSQL persistence adapter for purpose-bound Assignment-history reads.

The parent service owns authorization. This adapter owns only a read-only,
tenant-scoped projection of canonical Orgmetra ``assignment_record`` truth and
returns typed rows for the parent service to revalidate before disclosure.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from uuid import UUID

from orgmetra_people_api.assignment_history import (
    AssignmentHistoryIntegrityError,
    AssignmentHistoryRecord,
)

PostgresConnectionFactory = Callable[[], AbstractContextManager[Any]]

_READ_ONLY_SQL = "SET TRANSACTION ISOLATION LEVEL READ COMMITTED, READ ONLY"
_TENANT_CONTEXT_SQL = "SELECT pg_catalog.set_config('orgmetra.tenant_record_id', %s, true)"
_ASSIGNMENT_HISTORY_SQL = """
SELECT
    assignment.tenant_record_id,
    assignment.assignment_record_id,
    assignment.employment_record_id,
    assignment.person_record_id,
    assignment.position_record_id,
    assignment.allocation_ratio,
    assignment.effective_from,
    assignment.effective_to,
    assignment.recorded_from AT TIME ZONE 'UTC' AS recorded_from_utc,
    assignment.recorded_to AT TIME ZONE 'UTC' AS recorded_to_utc
FROM public.assignment_record AS assignment
WHERE assignment.tenant_record_id = %s
  AND assignment.person_record_id = %s
  AND assignment.recorded_from <= %s
  AND (assignment.recorded_to IS NULL OR %s < assignment.recorded_to)
ORDER BY assignment.effective_from, assignment.assignment_record_id
""".strip()
_MAX_UUID_INT = (1 << 128) - 1


def _require_operational_uuid(field_name: str, value: object) -> None:
    """Require an exact non-sentinel UUID before any database access."""
    if type(value) is not UUID:
        raise ValueError(f"{field_name} must be an operational UUID.")
    if value.int in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be an operational UUID.")


def _require_utc_instant(field_name: str, value: object) -> None:
    """Require exact built-in UTC time before using it as a history cutoff."""
    if type(value) is not datetime:
        raise ValueError(f"{field_name} must be a timezone-aware UTC datetime.")
    if type(value.tzinfo) is not timezone:
        raise ValueError(f"{field_name} must be a timezone-aware UTC datetime.")
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must be a timezone-aware UTC datetime.")


def _db_utc_instant(value: object) -> datetime:
    """Attach built-in UTC only to PostgreSQL's explicit naive UTC projection."""
    if type(value) is not datetime:
        raise AssignmentHistoryIntegrityError(
            "database recorded time must be a naive UTC projection"
        )
    if value.tzinfo is not None:
        raise AssignmentHistoryIntegrityError(
            "database recorded time must be a naive UTC projection"
        )
    return value.replace(tzinfo=timezone.utc)


def _record_from_row(row: object) -> AssignmentHistoryRecord:
    """Convert one untrusted DB-API row into the parent governed record type."""
    if type(row) is not tuple or len(row) != 10:
        raise AssignmentHistoryIntegrityError("database assignment-history row has an invalid shape")
    (
        tenant_record_id,
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
    try:
        return AssignmentHistoryRecord(
            tenant_record_id=tenant_record_id,
            assignment_record_id=assignment_record_id,
            employment_record_id=employment_record_id,
            person_record_id=person_record_id,
            position_record_id=position_record_id,
            allocation_ratio=allocation_ratio,
            effective_from=effective_from,
            effective_to=effective_to,
            recorded_from=_db_utc_instant(recorded_from),
            recorded_to=None if recorded_to is None else _db_utc_instant(recorded_to),
        )
    except ValueError as exc:
        raise AssignmentHistoryIntegrityError(
            "database assignment-history row failed integrity"
        ) from exc


@dataclass(frozen=True, slots=True)
class PostgresAssignmentHistoryReadPort:
    """Read canonical Assignment history through one tenant-scoped read-only transaction."""

    connection_factory: PostgresConnectionFactory

    def __post_init__(self) -> None:
        """Reject an unusable connection factory before a protected read can start."""
        if not callable(self.connection_factory):
            raise TypeError("connection_factory must be callable")

    def read_assignment_history(
        self,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        known_at: datetime,
    ) -> tuple[AssignmentHistoryRecord, ...]:
        """Return rows visible at ``known_at`` without authorizing disclosure itself."""
        _require_operational_uuid("tenant_record_id", tenant_record_id)
        _require_operational_uuid("person_record_id", person_record_id)
        _require_utc_instant("known_at", known_at)

        with self.connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(_READ_ONLY_SQL)
                cursor.execute(_TENANT_CONTEXT_SQL, (str(tenant_record_id),))
                cursor.execute(
                    _ASSIGNMENT_HISTORY_SQL,
                    (tenant_record_id, person_record_id, known_at, known_at),
                )
                rows = cursor.fetchall()

        if type(rows) is not list:
            raise AssignmentHistoryIntegrityError(
                "database assignment-history read must return the default list row collection"
            )

        records: list[AssignmentHistoryRecord] = []
        for row in rows:
            record = _record_from_row(row)
            if (
                record.tenant_record_id != tenant_record_id
                or record.person_record_id != person_record_id
            ):
                raise AssignmentHistoryIntegrityError(
                    "database assignment-history row does not match the requested target"
                )
            if record.recorded_from > known_at or (
                record.recorded_to is not None and known_at >= record.recorded_to
            ):
                raise AssignmentHistoryIntegrityError(
                    "database assignment-history row is not visible at the requested knowledge cutoff"
                )
            records.append(record)
        return tuple(records)
