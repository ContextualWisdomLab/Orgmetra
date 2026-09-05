"""Tenant-bound PostgreSQL read adapter for the workforce-validation registry.

The adapter reads only the canonical ``workforce_validation.validity_study``
relation. Deployment code owns pooling, TLS, credentials and assumption of the
least-privilege runtime role; this boundary owns transaction-local tenant RLS,
parameterized SQL, target snapshots and fail-closed row reconstruction.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any, Callable
from uuid import UUID

from orgmetra_workforce_validation_api.registry import (
    ValidityStudyIntegrityError,
    ValidityStudyRecord,
    _restore_operational_uuid,
    _store_operational_uuid,
)

PostgresConnectionFactory = Callable[[], AbstractContextManager[Any]]

_READ_ONLY_SQL = "SET TRANSACTION READ ONLY"
_TENANT_CONTEXT_SQL = "SELECT pg_catalog.set_config('orgmetra.tenant_record_id', %s, true)"
_REGISTRY_READ_SQL = """
SELECT
    tenant_record_id,
    validity_study_id,
    criterion_blueprint_id,
    study_status_code,
    recorded_from,
    recorded_to
FROM workforce_validation.validity_study
WHERE tenant_record_id = %s
  AND validity_study_id = %s
  AND recorded_to IS NULL
LIMIT 2
""".strip()


class PostgresValidityStudyReadPort(tuple):
    """Read one current validity-study header under forced tenant RLS.

    ``connection_factory`` must return a DB-API-compatible connection context
    manager configured by deployment code. Tuple-backed storage prevents a
    retained port reference from replacing that accepted dependency after
    validation. The adapter snapshots UUID identity before invoking the factory so
    retained caller UUID aliases cannot change the authorized SQL target during
    connection acquisition.
    """

    __slots__ = ()

    def __new__(
        cls,
        *,
        connection_factory: PostgresConnectionFactory,
    ) -> PostgresValidityStudyReadPort:
        """Validate and structurally bind the executable connection dependency."""
        if not callable(connection_factory):
            raise TypeError("connection_factory must be callable")
        return tuple.__new__(cls, (connection_factory,))

    @property
    def connection_factory(self) -> PostgresConnectionFactory:
        """Return the structurally bound connection dependency."""
        return self[0]

    def read_validity_study(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
    ) -> ValidityStudyRecord | None:
        """Return one exact current owner record or ``None`` for the tenant target."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)

        sql_tenant_id = _restore_operational_uuid("tenant_record_id", tenant_identity)
        sql_study_id = _restore_operational_uuid("validity_study_id", study_identity)

        with self.connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(_READ_ONLY_SQL)
                cursor.execute(_TENANT_CONTEXT_SQL, (str(sql_tenant_id),))
                cursor.execute(_REGISTRY_READ_SQL, (sql_tenant_id, sql_study_id))
                rows = cursor.fetchmany(2)

        if not rows:
            return None
        if len(rows) != 1:
            raise ValidityStudyIntegrityError("multiple current validity-study rows match the target")

        row = rows[0]
        if type(row) is not tuple or len(row) != 6:
            raise ValidityStudyIntegrityError("repository returned a non-canonical validity-study row")

        try:
            record = ValidityStudyRecord(
                tenant_record_id=row[0],
                validity_study_id=row[1],
                criterion_blueprint_id=row[2],
                study_status_code=row[3],
                recorded_from=row[4],
                recorded_to=row[5],
            )
        except (TypeError, ValueError) as exc:
            raise ValidityStudyIntegrityError("repository returned an invalid validity-study row") from exc

        if (
            _store_operational_uuid("record tenant_record_id", record.tenant_record_id)
            != tenant_identity
            or _store_operational_uuid("record validity_study_id", record.validity_study_id)
            != study_identity
        ):
            raise ValidityStudyIntegrityError("repository returned a validity-study row for another target")
        return record
