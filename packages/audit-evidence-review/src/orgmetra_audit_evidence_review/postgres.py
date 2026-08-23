"""Least-privileged PostgreSQL reader for governed Orgmetra audit evidence.

The adapter reads only Orgmetra's immutable ``public.audit_event_record`` relation.
It opens a read-only transaction, proves the current database role is neither a
superuser nor an RLS-bypass role, binds the exact tenant into PostgreSQL's
transaction-local RLS context, and issues one bounded parameterized query.  It
never reads HR application tables or another service's database.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any, Callable

from .review import AuditEvidenceQuery, PersistedAuditEvidenceRow

PostgresConnectionFactory = Callable[[], AbstractContextManager[Any]]

_READ_ONLY_SQL = "SET TRANSACTION READ ONLY"
_ROLE_GUARD_SQL = """
SELECT 1
FROM pg_catalog.pg_roles
WHERE rolname = CURRENT_USER
  AND rolsuper IS FALSE
  AND rolbypassrls IS FALSE
""".strip()
_TENANT_CONTEXT_SQL = "SELECT pg_catalog.set_config('orgmetra.tenant_record_id', %s, true)"
_AUDIT_EVIDENCE_SQL = """
SELECT
    tenant_record_id,
    audit_event_record_id,
    canonical_event_json,
    event_envelope_digest,
    recorded_at
FROM public.audit_event_record
WHERE tenant_record_id = %s
  AND recorded_at >= %s
  AND recorded_at < %s
ORDER BY recorded_at ASC, audit_event_record_id ASC
LIMIT %s
""".strip()


@dataclass(frozen=True, slots=True)
class PostgresAuditEvidenceRowReader:
    """Read bounded audit evidence through forced RLS and a least-privileged role.

    ``connection_factory`` must return a DB-API-compatible connection context
    manager. Deployment composition owns pooling, TLS, credentials, and the
    actual ``NOSUPERUSER NOBYPASSRLS`` login role; this adapter verifies that
    role property again before it establishes tenant context or reads evidence.
    """

    connection_factory: PostgresConnectionFactory

    def __post_init__(self) -> None:
        """Reject an unusable connection factory before any audit read is attempted."""
        if not callable(self.connection_factory):
            raise TypeError("connection_factory must be callable")

    def read_rows(self, query: AuditEvidenceQuery) -> tuple[PersistedAuditEvidenceRow, ...]:
        """Return one ordered, tenant-bound page of revalidated immutable audit rows."""
        if type(query) is not AuditEvidenceQuery:
            raise TypeError("query must be an exact AuditEvidenceQuery.")
        verified_query = AuditEvidenceQuery(
            tenant_record_id=query.tenant_record_id,
            query_reference=query.query_reference,
            requester_reference=query.requester_reference,
            purpose_code=query.purpose_code,
            recorded_from=query.recorded_from,
            recorded_before=query.recorded_before,
            limit=query.limit,
        )

        with self.connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(_READ_ONLY_SQL)
                cursor.execute(_ROLE_GUARD_SQL)
                if cursor.fetchone() is None:
                    raise PermissionError(
                        "audit evidence reads require a NOSUPERUSER NOBYPASSRLS database role."
                    )
                cursor.execute(_TENANT_CONTEXT_SQL, (str(verified_query.tenant_record_id),))
                cursor.execute(
                    _AUDIT_EVIDENCE_SQL,
                    (
                        verified_query.tenant_record_id,
                        verified_query.recorded_from,
                        verified_query.recorded_before,
                        verified_query.limit,
                    ),
                )
                rows = cursor.fetchmany(verified_query.limit)

        verified_rows: list[PersistedAuditEvidenceRow] = []
        for row in rows:
            if not isinstance(row, tuple) or len(row) != 5:
                raise ValueError("database row must contain exactly five audit evidence columns.")
            (
                tenant_record_id,
                audit_event_record_id,
                canonical_event_json,
                event_envelope_digest,
                recorded_at,
            ) = row
            verified_rows.append(
                PersistedAuditEvidenceRow(
                    tenant_record_id=tenant_record_id,
                    audit_event_record_id=audit_event_record_id,
                    canonical_event_json=canonical_event_json,
                    event_envelope_digest=event_envelope_digest,
                    recorded_at=recorded_at,
                )
            )
        return tuple(verified_rows)
