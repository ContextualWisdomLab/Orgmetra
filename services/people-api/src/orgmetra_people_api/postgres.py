"""Tenant-bound PostgreSQL persistence adapter for governed People reads.

The adapter deliberately owns only read-side SQL for Orgmetra's canonical HRIS
relations. It enters an explicit read-only transaction, binds the exact tenant
into PostgreSQL's transaction-local RLS setting, and uses parameterized,
fully-qualified queries so caller-controlled identifiers cannot alter SQL or
object resolution. Ambiguous current truth fails closed instead of selecting an
arbitrary employment lineage.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable
from uuid import UUID

from orgmetra_people_api.people import (
    PeopleRecordIntegrityError,
    WorkerPeopleRecord,
    _validate_operational_uuid,
)

PostgresConnectionFactory = Callable[[], AbstractContextManager[Any]]

_READ_ONLY_SQL = "SET TRANSACTION READ ONLY"
_TENANT_CONTEXT_SQL = "SELECT pg_catalog.set_config('orgmetra.tenant_record_id', %s, true)"
_WORKER_READ_SQL = """
SELECT
    conversion.tenant_record_id,
    conversion.candidate_worker_conversion_record_id,
    conversion.candidate_profile_id,
    conversion.person_record_id,
    conversion.employment_record_id,
    person_name.display_name,
    employment_version.employment_status_code
FROM public.candidate_worker_conversion_record AS conversion
JOIN public.person_record AS person
  ON person.tenant_record_id = conversion.tenant_record_id
 AND person.person_record_id = conversion.person_record_id
 AND person.recorded_to IS NULL
JOIN public.person_name_record AS person_name
  ON person_name.tenant_record_id = conversion.tenant_record_id
 AND person_name.person_record_id = conversion.person_record_id
 AND person_name.recorded_to IS NULL
JOIN public.employment_record AS employment
  ON employment.tenant_record_id = conversion.tenant_record_id
 AND employment.employment_record_id = conversion.employment_record_id
 AND employment.person_record_id = conversion.person_record_id
 AND employment.recorded_to IS NULL
JOIN public.employment_record_version AS employment_version
  ON employment_version.tenant_record_id = conversion.tenant_record_id
 AND employment_version.employment_record_id = conversion.employment_record_id
 AND employment_version.recorded_to IS NULL
WHERE conversion.tenant_record_id = %s
  AND conversion.person_record_id = %s
  AND conversion.recorded_to IS NULL
  AND conversion.effective_from <= %s
  AND (conversion.effective_to IS NULL OR conversion.effective_to > %s)
  AND person_name.effective_from <= %s
  AND (person_name.effective_to IS NULL OR person_name.effective_to > %s)
  AND employment_version.effective_from <= %s
  AND (employment_version.effective_to IS NULL OR employment_version.effective_to > %s)
ORDER BY
    conversion.recorded_from DESC,
    person_name.recorded_from DESC,
    employment_version.recorded_from DESC
LIMIT 2
""".strip()


@dataclass(frozen=True, slots=True)
class PostgresPeopleReadPort:
    """Resolve current worker truth through a transaction-local PostgreSQL tenant scope.

    ``connection_factory`` must return a DB-API-compatible connection context
    manager, such as a configured ``psycopg.connect`` callable. Keeping the
    driver behind this factory preserves a small standalone service package
    while allowing deployment code to own pooling, credentials, TLS, and role
    selection.
    """

    connection_factory: PostgresConnectionFactory

    def __post_init__(self) -> None:
        """Reject unusable factories before any protected read can be attempted."""
        if not callable(self.connection_factory):
            raise TypeError("connection_factory must be callable")

    def read_worker(
        self,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        effective_on: date,
    ) -> WorkerPeopleRecord | None:
        """Read one exact worker at a business date under forced tenant RLS.

        The recorded-time predicate is intentionally ``recorded_to IS NULL``:
        customer reads use Orgmetra's current system knowledge while
        ``effective_on`` selects the requested business-time truth. At most two
        rows are fetched so an unexpected duplicate lineage is detected and
        rejected rather than hidden by ``LIMIT 1``.
        """
        _validate_operational_uuid("tenant_record_id", tenant_record_id)
        _validate_operational_uuid("person_record_id", person_record_id)
        if not isinstance(effective_on, date):
            raise ValueError("effective_on must be a business date.")

        with self.connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(_READ_ONLY_SQL)
                cursor.execute(_TENANT_CONTEXT_SQL, (str(tenant_record_id),))
                cursor.execute(
                    _WORKER_READ_SQL,
                    (
                        tenant_record_id,
                        person_record_id,
                        effective_on,
                        effective_on,
                        effective_on,
                        effective_on,
                        effective_on,
                        effective_on,
                    ),
                )
                rows = cursor.fetchmany(2)

        if not rows:
            return None
        if len(rows) != 1:
            raise PeopleRecordIntegrityError("multiple current worker records match the requested target")

        (
            row_tenant_record_id,
            candidate_worker_conversion_record_id,
            candidate_profile_id,
            row_person_record_id,
            employment_record_id,
            display_name,
            employment_status_code,
        ) = rows[0]
        record = WorkerPeopleRecord(
            tenant_record_id=row_tenant_record_id,
            candidate_worker_conversion_record_id=candidate_worker_conversion_record_id,
            candidate_profile_id=candidate_profile_id,
            person_record_id=row_person_record_id,
            employment_record_id=employment_record_id,
            display_name=display_name,
            employment_status_code=employment_status_code,
        )
        if record.tenant_record_id != tenant_record_id or record.person_record_id != person_record_id:
            raise PeopleRecordIntegrityError("database row escaped requested target")
        return record
