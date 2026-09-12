"""PostgreSQL adapter for the governed Employment separation transaction."""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import replace
from typing import Any, Callable, NoReturn

from orgmetra_keyverse_adapter import AuthorizationDecision

from orgmetra_people_api.mutations import PeopleMutationNotFound
from orgmetra_people_api.separation import (
    EmploymentSeparationCommand,
    EmploymentSeparationIntegrityError,
    EmploymentSeparationResult,
)

PostgresConnectionFactory = Callable[[], AbstractContextManager[Any]]

_READ_WRITE_SQL = "SET TRANSACTION ISOLATION LEVEL READ COMMITTED, READ WRITE"
_TENANT_CONTEXT_SQL = "SELECT pg_catalog.set_config('orgmetra.tenant_record_id', %s, true)"
_SEPARATE_EMPLOYMENT_SQL = """
SELECT
    employment_record_id,
    separated_employment_record_version_id,
    recorded_at,
    replayed
FROM public.separate_employment_record_once(
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
""".strip()
_EMPLOYMENT_FIELDS = frozenset({"employment_record"})


def _require_authorization(
    *,
    authorization: object,
    command: EmploymentSeparationCommand,
) -> AuthorizationDecision:
    """Require exact allow evidence for the governed separation operation."""
    if type(authorization) is not AuthorizationDecision:
        raise EmploymentSeparationIntegrityError("Employment separation requires typed authorization evidence")
    if (
        not authorization.allowed
        or authorization.tenant_record_id != command.tenant_record_id
        or authorization.resource_reference != f"employment_record:{command.employment_record_id.hex}"
        or authorization.purpose_code != "workforce_admin"
        or authorization.operation_code != "separate_record"
        or authorization.resource_kind != "employment_record"
        or authorization.requested_fields != _EMPLOYMENT_FIELDS
        or authorization.authorized_fields != _EMPLOYMENT_FIELDS
    ):
        raise EmploymentSeparationIntegrityError("Employment separation authorization does not match the exact record")
    return authorization


def _one_result_row(cursor: Any) -> tuple[object, object, object, object]:
    """Detach exactly one built-in database row before validating result evidence."""
    rows = cursor.fetchmany(2)
    if type(rows) not in (list, tuple) or len(rows) != 1:
        raise EmploymentSeparationIntegrityError("Employment separation database result is invalid")
    row = rows[0]
    if type(row) not in (list, tuple) or len(row) != 4:
        raise EmploymentSeparationIntegrityError("Employment separation database result is invalid")
    return row[0], row[1], row[2], row[3]


def _translate_database_error(error: Exception) -> NoReturn:
    """Translate only reviewed business SQLSTATEs; permission failures remain operational errors."""
    sqlstate = getattr(error, "sqlstate", None)
    if sqlstate == "23503":
        raise PeopleMutationNotFound("Employment separation target was not found") from error
    if sqlstate in {"40001", "23505", "55000", "22023"}:
        raise EmploymentSeparationIntegrityError("Employment separation conflicts with authoritative state") from error
    raise error


class PostgresEmploymentSeparationPort(tuple):
    """Invoke only the governed separation function inside one tenant-bound transaction.

    The database login is expected to receive the released
    ``orgmetra_employment_separation_executor`` capability operationally. This
    adapter never assumes the privileged function-owner role and never issues
    direct People/audit/outbox DML.
    """

    __slots__ = ()

    def __new__(
        cls,
        connection_factory: PostgresConnectionFactory,
    ) -> PostgresEmploymentSeparationPort:
        """Validate and structurally bind the executable database capability."""
        if not callable(connection_factory):
            raise TypeError("connection_factory must be callable")
        return tuple.__new__(cls, (connection_factory,))

    def separate_employment(
        self,
        *,
        command: EmploymentSeparationCommand,
        authorization: AuthorizationDecision,
    ) -> EmploymentSeparationResult:
        """Persist or replay one authorized Employment separation."""
        if type(command) is not EmploymentSeparationCommand:
            raise TypeError("command must be an EmploymentSeparationCommand")
        detached_command = replace(command)
        decision = _require_authorization(authorization=authorization, command=detached_command)
        connection_factory = tuple.__getitem__(self, 0)

        try:
            with connection_factory() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(_READ_WRITE_SQL)
                    cursor.execute(_TENANT_CONTEXT_SQL, (str(detached_command.tenant_record_id),))
                    cursor.execute(
                        _SEPARATE_EMPLOYMENT_SQL,
                        (
                            detached_command.tenant_record_id,
                            detached_command.person_record_id,
                            detached_command.employment_record_id,
                            detached_command.expected_employment_record_version_id,
                            detached_command.separation_effective_on,
                            detached_command.separation_reason_code,
                            detached_command.evidence_reference,
                            detached_command.evidence_version_code,
                            decision.actor_reference,
                            decision.purpose_code,
                            detached_command.confirmation_reference,
                            detached_command.idempotency_key,
                            detached_command.audit_event_record_id,
                            detached_command.outbox_delivery_record_id,
                        ),
                    )
                    row = _one_result_row(cursor)
        except Exception as error:
            _translate_database_error(error)

        try:
            result = EmploymentSeparationResult(
                employment_record_id=row[0],  # type: ignore[arg-type]
                separated_employment_record_version_id=row[1],  # type: ignore[arg-type]
                recorded_at=row[2],  # type: ignore[arg-type]
                replayed=row[3],  # type: ignore[arg-type]
            )
        except (TypeError, ValueError) as error:
            raise EmploymentSeparationIntegrityError("Employment separation database result is invalid") from error
        if result.employment_record_id != detached_command.employment_record_id:
            raise EmploymentSeparationIntegrityError("Employment separation database identity does not match command")
        return result
