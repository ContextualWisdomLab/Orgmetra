"""Transactional PostgreSQL persistence for the first Orgmetra people slice."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import date, datetime
from string import ascii_lowercase, digits
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg import Connection, Error as PsycopgError, IntegrityError
from psycopg.errors import InsufficientPrivilege

from .context import PurposeContext
from .errors import (
    RepositoryAuthorizationError,
    RepositoryConflictError,
    RepositoryUnavailableError,
)
from .models import AuditEvent, CandidateSnapshot, CandidateWorkerLink, PersonSnapshot

ConnectFactory = Callable[..., Connection[Any]]
IdentifierFactory = Callable[[], UUID]
_ALLOWED_CODE_CHARACTERS = frozenset(ascii_lowercase + digits + "_")


class PostgresPeopleRepository:
    """Persist tenant-scoped people facts and atomic audit evidence.

    The host authenticates the actor and authorizes the purpose before
    constructing :class:`PurposeContext`. Every operation binds the tenant to a
    transaction-local PostgreSQL setting consumed by row-level security.
    """

    def __init__(
        self,
        dsn: str,
        *,
        connect_factory: ConnectFactory = psycopg.connect,
        identifier_factory: IdentifierFactory = uuid4,
    ) -> None:
        """Create a repository without opening a database connection."""

        normalized_dsn = dsn.strip()
        if not normalized_dsn:
            raise ValueError("dsn must contain a non-whitespace value")
        self._dsn = normalized_dsn
        self._connect_factory = connect_factory
        self._identifier_factory = identifier_factory

    def create_tenant(self, context: PurposeContext, tenant_name: str) -> UUID:
        """Create one tenant idempotently and return its opaque identifier."""

        normalized_name = _normalize_text(tenant_name, "tenant_name", 200)
        with self._transaction(context) as connection:
            inserted = connection.execute(
                """
                INSERT INTO tenant_record (
                    tenant_record_id, tenant_name, created_at
                ) VALUES (%s, %s, now())
                ON CONFLICT (tenant_record_id) DO NOTHING
                RETURNING tenant_record_id
                """,
                (context.tenant_reference, normalized_name),
            ).fetchone()
            if inserted is None:
                existing = connection.execute(
                    "SELECT tenant_name FROM tenant_record WHERE tenant_record_id = %s",
                    (context.tenant_reference,),
                ).fetchone()
                if existing is None or existing[0] != normalized_name:
                    raise RepositoryConflictError(
                        "tenant identity already exists with different data"
                    )
                return context.tenant_reference

            self._record_audit(
                connection,
                context,
                action_code="tenant_created",
                resource_type_code="tenant_record",
                resource_record_id=context.tenant_reference,
            )
            return context.tenant_reference

    def create_person(
        self,
        context: PurposeContext,
        *,
        person_record_id: UUID,
        display_name: str,
        effective_from: date,
        effective_to: date | None = None,
        recorded_at: datetime | None = None,
    ) -> PersonSnapshot:
        """Create one person record idempotently within the caller's tenant."""

        normalized_name = _normalize_text(display_name, "display_name", 300)
        _validate_effective_period(effective_from, effective_to)
        with self._transaction(context) as connection:
            row = connection.execute(
                """
                INSERT INTO person_record (
                    tenant_record_id, person_record_id, display_name,
                    effective_from, effective_to, recorded_from, recorded_to
                ) VALUES (%s, %s, %s, %s, %s, COALESCE(%s, now()), NULL)
                ON CONFLICT (person_record_id) DO NOTHING
                RETURNING person_record_id, display_name, effective_from,
                          effective_to, recorded_from
                """,
                (
                    context.tenant_reference,
                    person_record_id,
                    normalized_name,
                    effective_from,
                    effective_to,
                    recorded_at,
                ),
            ).fetchone()
            if row is None:
                existing = self._select_person(connection, person_record_id)
                if existing is None or (
                    existing.display_name,
                    existing.effective_from,
                    existing.effective_to,
                ) != (normalized_name, effective_from, effective_to):
                    raise RepositoryConflictError(
                        "person identity already exists with different data"
                    )
                return existing

            snapshot = _person_snapshot(row)
            self._record_audit(
                connection,
                context,
                action_code="person_created",
                resource_type_code="person_record",
                resource_record_id=person_record_id,
            )
            return snapshot

    def get_person(
        self, context: PurposeContext, person_record_id: UUID
    ) -> PersonSnapshot | None:
        """Return the current visible person record or ``None``."""

        with self._transaction(context) as connection:
            return self._select_person(connection, person_record_id)

    def create_candidate(
        self,
        context: PurposeContext,
        *,
        candidate_profile_id: UUID,
        application_status_code: str,
    ) -> CandidateSnapshot:
        """Create one candidate profile idempotently within a tenant."""

        normalized_status = _normalize_code(
            application_status_code, "application_status_code"
        )
        with self._transaction(context) as connection:
            row = connection.execute(
                """
                INSERT INTO candidate_profile (
                    tenant_record_id, candidate_profile_id,
                    application_status_code, recorded_at
                ) VALUES (%s, %s, %s, now())
                ON CONFLICT (candidate_profile_id) DO NOTHING
                RETURNING candidate_profile_id, application_status_code,
                          recorded_at
                """,
                (
                    context.tenant_reference,
                    candidate_profile_id,
                    normalized_status,
                ),
            ).fetchone()
            if row is None:
                existing = connection.execute(
                    """
                    SELECT candidate_profile_id, application_status_code,
                           recorded_at
                    FROM candidate_profile
                    WHERE candidate_profile_id = %s
                    """,
                    (candidate_profile_id,),
                ).fetchone()
                if existing is None or existing[1] != normalized_status:
                    raise RepositoryConflictError(
                        "candidate identity already exists with different data"
                    )
                return CandidateSnapshot(*existing)

            snapshot = CandidateSnapshot(*row)
            self._record_audit(
                connection,
                context,
                action_code="candidate_created",
                resource_type_code="candidate_profile",
                resource_record_id=candidate_profile_id,
            )
            return snapshot

    def link_candidate_to_worker(
        self,
        context: PurposeContext,
        *,
        candidate_profile_id: UUID,
        person_record_id: UUID,
        candidate_worker_link_id: UUID | None = None,
    ) -> CandidateWorkerLink:
        """Append an idempotent candidate-to-worker identity link."""

        link_id = candidate_worker_link_id or self._identifier_factory()
        with self._transaction(context) as connection:
            row = connection.execute(
                """
                INSERT INTO candidate_worker_link (
                    tenant_record_id, candidate_worker_link_id,
                    candidate_profile_id, person_record_id, linked_at
                ) VALUES (%s, %s, %s, %s, now())
                ON CONFLICT (candidate_profile_id) DO NOTHING
                RETURNING candidate_worker_link_id, candidate_profile_id,
                          person_record_id, linked_at
                """,
                (
                    context.tenant_reference,
                    link_id,
                    candidate_profile_id,
                    person_record_id,
                ),
            ).fetchone()
            if row is None:
                existing = connection.execute(
                    """
                    SELECT candidate_worker_link_id, candidate_profile_id,
                           person_record_id, linked_at
                    FROM candidate_worker_link
                    WHERE candidate_profile_id = %s
                    """,
                    (candidate_profile_id,),
                ).fetchone()
                if existing is None or existing[2] != person_record_id:
                    raise RepositoryConflictError(
                        "candidate is already linked to a different worker"
                    )
                return CandidateWorkerLink(*existing)

            link = CandidateWorkerLink(*row)
            self._record_audit(
                connection,
                context,
                action_code="candidate_worker_linked",
                resource_type_code="candidate_worker_link",
                resource_record_id=link.candidate_worker_link_id,
            )
            return link

    def list_audit_events(
        self, context: PurposeContext, resource_record_id: UUID
    ) -> tuple[AuditEvent, ...]:
        """Return audit events visible for one resource in occurrence order."""

        with self._transaction(context) as connection:
            rows = connection.execute(
                """
                SELECT audit_event_id, action_code, resource_type_code,
                       resource_record_id, actor_reference, purpose_code,
                       occurred_at
                FROM audit_event
                WHERE resource_record_id = %s
                ORDER BY occurred_at, audit_event_id
                """,
                (resource_record_id,),
            ).fetchall()
            return tuple(AuditEvent(*row) for row in rows)

    def _select_person(
        self, connection: Connection[Any], person_record_id: UUID
    ) -> PersonSnapshot | None:
        """Read one current person row through the active RLS context."""

        row = connection.execute(
            """
            SELECT person_record_id, display_name, effective_from,
                   effective_to, recorded_from
            FROM person_record
            WHERE person_record_id = %s AND recorded_to IS NULL
            """,
            (person_record_id,),
        ).fetchone()
        return None if row is None else _person_snapshot(row)

    def _record_audit(
        self,
        connection: Connection[Any],
        context: PurposeContext,
        *,
        action_code: str,
        resource_type_code: str,
        resource_record_id: UUID,
    ) -> None:
        """Append non-content audit evidence in the caller's transaction."""

        connection.execute(
            """
            INSERT INTO audit_event (
                audit_event_id, tenant_record_id, actor_reference,
                purpose_code, correlation_reference, decision_reference,
                evidence_reference, action_code, resource_type_code,
                resource_record_id, occurred_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            """,
            (
                self._identifier_factory(),
                context.tenant_reference,
                context.actor_reference,
                context.purpose_code,
                context.correlation_reference,
                context.decision_reference,
                context.evidence_reference,
                action_code,
                resource_type_code,
                resource_record_id,
            ),
        )

    @contextmanager
    def _transaction(
        self, context: PurposeContext
    ) -> Iterator[Connection[Any]]:
        """Open one fail-closed transaction and bind its tenant context."""

        try:
            with self._connect_factory(self._dsn, autocommit=False) as connection:
                with connection.transaction():
                    connection.execute(
                        "SELECT set_config(%s, %s, true)",
                        (
                            "orgmetra.tenant_reference",
                            str(context.tenant_reference),
                        ),
                    )
                    yield connection
        except InsufficientPrivilege as exc:
            raise RepositoryAuthorizationError(
                "PostgreSQL denied the purpose-bound repository operation"
            ) from exc
        except IntegrityError as exc:
            raise RepositoryConflictError(
                "PostgreSQL rejected an identity or relationship constraint"
            ) from exc
        except PsycopgError as exc:
            raise RepositoryUnavailableError(
                "PostgreSQL could not complete the repository operation"
            ) from exc


def _normalize_text(value: str, field_name: str, maximum_length: int) -> str:
    """Normalize a required text value and enforce its public bound."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must contain a non-whitespace value")
    if len(normalized) > maximum_length:
        raise ValueError(f"{field_name} must not exceed {maximum_length} characters")
    return normalized


def _normalize_code(value: str, field_name: str) -> str:
    """Normalize a bounded ASCII machine-readable code."""

    normalized = _normalize_text(value, field_name, 64)
    if not all(character in _ALLOWED_CODE_CHARACTERS for character in normalized):
        raise ValueError(
            f"{field_name} must use lower-case ASCII letters, digits, and underscores"
        )
    return normalized


def _validate_effective_period(
    effective_from: date, effective_to: date | None
) -> None:
    """Require a positive half-open effective-time interval."""

    if effective_to is not None and effective_to <= effective_from:
        raise ValueError("effective_to must be later than effective_from")


def _person_snapshot(row: tuple[Any, ...]) -> PersonSnapshot:
    """Convert one validated database row to an immutable projection."""

    return PersonSnapshot(*row)
