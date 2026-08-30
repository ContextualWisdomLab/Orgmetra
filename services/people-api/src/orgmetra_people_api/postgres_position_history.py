"""PostgreSQL adapter for purpose-bound Position-history reads.

The parent People service owns purpose-bound authorization. This adapter owns
only a read-only, tenant-scoped projection of canonical Orgmetra Position and
Position-version facts, returning typed rows for the parent service to
revalidate before disclosure.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from uuid import UUID

from orgmetra_people_api.position_history import (
    PositionHistoryIntegrityError,
    PositionHistoryRecord,
)

PostgresConnectionFactory = Callable[[], AbstractContextManager[Any]]

_READ_ONLY_SQL = "SET TRANSACTION ISOLATION LEVEL READ COMMITTED, READ ONLY"
_TENANT_CONTEXT_SQL = "SELECT pg_catalog.set_config('orgmetra.tenant_record_id', %s, true)"
_POSITION_HISTORY_SQL = """
SELECT
    position_version.tenant_record_id,
    position_version.position_record_id,
    position_version.position_record_version_id,
    position_anchor.organization_unit_id,
    position_anchor.job_profile_id,
    position_version.position_status_code,
    position_version.effective_from,
    position_version.effective_to,
    position_version.recorded_from AT TIME ZONE 'UTC' AS recorded_from_utc,
    position_version.recorded_to AT TIME ZONE 'UTC' AS recorded_to_utc
FROM public.position_record_version AS position_version
JOIN public.position_record AS position_anchor
  ON position_anchor.tenant_record_id = position_version.tenant_record_id
 AND position_anchor.position_record_id = position_version.position_record_id
WHERE position_version.tenant_record_id = %s
  AND position_version.position_record_id = %s
  AND position_anchor.recorded_from <= %s
  AND (position_anchor.recorded_to IS NULL OR %s < position_anchor.recorded_to)
  AND position_version.recorded_from <= %s
  AND (position_version.recorded_to IS NULL OR %s < position_version.recorded_to)
ORDER BY position_version.effective_from, position_version.position_record_version_id
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
    if type(value) is not datetime or value.tzinfo is not None:
        raise PositionHistoryIntegrityError(
            "database recorded time must be a naive UTC projection"
        )
    return value.replace(tzinfo=timezone.utc)


def _record_from_row(row: object) -> PositionHistoryRecord:
    """Convert one untrusted DB-API row into the parent governed record type."""
    if type(row) is not tuple or len(row) != 10:
        raise PositionHistoryIntegrityError("database Position-history row has an invalid shape")
    (
        tenant_record_id,
        position_record_id,
        position_record_version_id,
        organization_unit_id,
        job_profile_id,
        position_status_code,
        effective_from,
        effective_to,
        recorded_from,
        recorded_to,
    ) = row
    try:
        return PositionHistoryRecord(
            tenant_record_id=tenant_record_id,
            position_record_id=position_record_id,
            position_record_version_id=position_record_version_id,
            organization_unit_id=organization_unit_id,
            job_profile_id=job_profile_id,
            position_status_code=position_status_code,
            effective_from=effective_from,
            effective_to=effective_to,
            recorded_from=_db_utc_instant(recorded_from),
            recorded_to=None if recorded_to is None else _db_utc_instant(recorded_to),
        )
    except ValueError as exc:
        raise PositionHistoryIntegrityError(
            "database Position-history row failed integrity"
        ) from exc


@dataclass(frozen=True, slots=True)
class PostgresPositionHistoryReadPort:
    """Read canonical Position history through a tenant-scoped read-only transaction."""

    connection_factory: PostgresConnectionFactory

    def __post_init__(self) -> None:
        """Reject an unusable connection factory before a protected read can start."""
        if not callable(self.connection_factory):
            raise TypeError("connection_factory must be callable")

    def read_position_history(
        self,
        *,
        tenant_record_id: UUID,
        position_record_id: UUID,
        known_at: datetime,
    ) -> tuple[PositionHistoryRecord, ...]:
        """Return Position versions visible at ``known_at`` without authorizing disclosure."""
        _require_operational_uuid("tenant_record_id", tenant_record_id)
        _require_operational_uuid("position_record_id", position_record_id)
        _require_utc_instant("known_at", known_at)

        with self.connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(_READ_ONLY_SQL)
                cursor.execute(_TENANT_CONTEXT_SQL, (str(tenant_record_id),))
                cursor.execute(
                    _POSITION_HISTORY_SQL,
                    (
                        tenant_record_id,
                        position_record_id,
                        known_at,
                        known_at,
                        known_at,
                        known_at,
                    ),
                )
                rows = cursor.fetchall()

        if type(rows) is not list:
            raise PositionHistoryIntegrityError(
                "database Position-history read must return the default list row collection"
            )

        records: list[PositionHistoryRecord] = []
        for row in rows:
            record = _record_from_row(row)
            if (
                record.tenant_record_id != tenant_record_id
                or record.position_record_id != position_record_id
            ):
                raise PositionHistoryIntegrityError(
                    "database Position-history row does not match the requested target"
                )
            if record.recorded_from > known_at or (
                record.recorded_to is not None and known_at >= record.recorded_to
            ):
                raise PositionHistoryIntegrityError(
                    "database Position-history row is not visible at the requested knowledge cutoff"
                )
            records.append(record)
        return tuple(records)

