"""PostgreSQL adapter for the governed Employment separation transaction."""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import replace
from typing import Any, Callable, NoReturn
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDecision

from orgmetra_people_api.mutations import PeopleMutationNotFound
from orgmetra_people_api.separation import (
    EmploymentSeparationCommand,
    EmploymentSeparationIntegrityError,
    EmploymentSeparationPersistenceIntegrityError,
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
_MAX_UUID_INT = (1 << 128) - 1


def _is_operational_uuid(value: object) -> bool:
    """Return whether UUID evidence has an inert operational integer payload."""
    if type(value) is not UUID:
        return False
    identity = value.int
    return type(identity) is int and 0 < identity < _MAX_UUID_INT


def _require_authorization(
    *,
    authorization: object,
    command: EmploymentSeparationCommand,
) -> AuthorizationDecision:
    """Validate and detach allow evidence for the governed separation operation."""
    if type(authorization) is not AuthorizationDecision:
        raise EmploymentSeparationPersistenceIntegrityError(
            "Employment separation requires typed authorization evidence"
        )

    allowed = authorization.allowed
    tenant_record_id = authorization.tenant_record_id
    actor_reference = authorization.actor_reference
    resource_reference = authorization.resource_reference
    policy_version_code = authorization.policy_version_code
    purpose_code = authorization.purpose_code
    operation_code = authorization.operation_code
    resource_kind = authorization.resource_kind
    requested_fields = authorization.requested_fields
    authorized_fields = authorization.authorized_fields
    reason_code = authorization.reason_code
    next_action = authorization.next_action

    if (
        type(allowed) is not bool
        or not _is_operational_uuid(tenant_record_id)
        or type(actor_reference) is not str
        or type(resource_reference) is not str
        or type(policy_version_code) is not str
        or type(purpose_code) is not str
        or type(operation_code) is not str
        or type(resource_kind) is not str
        or type(requested_fields) is not frozenset
        or type(authorized_fields) is not frozenset
        or type(reason_code) is not str
        or type(next_action) is not str
        or any(type(field) is not str for field in requested_fields)
        or any(type(field) is not str for field in authorized_fields)
    ):
        raise EmploymentSeparationPersistenceIntegrityError(
            "Employment separation authorization evidence is invalid"
        )

    tenant_identity = tenant_record_id.int
    assert type(tenant_identity) is int
    decision = AuthorizationDecision(
        allowed=allowed,
        tenant_record_id=UUID(int=tenant_identity),
        actor_reference=actor_reference,
        resource_reference=resource_reference,
        policy_version_code=policy_version_code,
        purpose_code=purpose_code,
        operation_code=operation_code,
        resource_kind=resource_kind,
        requested_fields=frozenset(tuple(requested_fields)),
        authorized_fields=frozenset(tuple(authorized_fields)),
        reason_code=reason_code,
        next_action=next_action,
    )
    if (
        not decision.allowed
        or decision.tenant_record_id != command.tenant_record_id
        or decision.resource_reference != f"employment_record:{command.employment_record_id.hex}"
        or decision.purpose_code != "workforce_admin"
        or decision.operation_code != "separate_record"
        or decision.resource_kind != "employment_record"
        or decision.requested_fields != _EMPLOYMENT_FIELDS
        or decision.authorized_fields != _EMPLOYMENT_FIELDS
    ):
        raise EmploymentSeparationPersistenceIntegrityError(
            "Employment separation authorization does not match the exact record"
        )
    return decision


def _require_transactional_connection(connection: object) -> None:
    """Require the governed write to run inside an implicit database transaction."""
    if getattr(connection, "autocommit", None) is not False:
        raise RuntimeError("Employment separation requires autocommit disabled.")


def _one_result_row(cursor: Any) -> tuple[object, object, object, object]:
    """Detach exactly one built-in database row before validating result evidence."""
    rows = cursor.fetchmany(2)
    if type(rows) not in (list, tuple) or len(rows) != 1:
        raise EmploymentSeparationPersistenceIntegrityError(
            "Employment separation database result is invalid"
        )
    row = rows[0]
    if type(row) not in (list, tuple) or len(row) != 4:
        raise EmploymentSeparationPersistenceIntegrityError(
            "Employment separation database result is invalid"
        )
    return row[0], row[1], row[2], row[3]


def _validated_result(
    *,
    row: tuple[object, object, object, object],
    expected_employment_record_id: object,
) -> EmploymentSeparationResult:
    """Validate persistence evidence while the transaction can still roll back."""
    try:
        result = EmploymentSeparationResult(
            employment_record_id=row[0],  # type: ignore[arg-type]
            separated_employment_record_version_id=row[1],  # type: ignore[arg-type]
            recorded_at=row[2],  # type: ignore[arg-type]
            replayed=row[3],  # type: ignore[arg-type]
        )
    except (TypeError, ValueError) as error:
        raise EmploymentSeparationPersistenceIntegrityError(
            "Employment separation database result is invalid"
        ) from error
    if result.employment_record_id != expected_employment_record_id:
        raise EmploymentSeparationPersistenceIntegrityError(
            "Employment separation database identity does not match command"
        )
    return result


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
    direct People/audit/outbox DML. The returned connection must expose exact
    ``autocommit is False`` before cursor acquisition so the transaction mode and
    transaction-local tenant context govern the complete function invocation.
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
                _require_transactional_connection(connection)
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
                    result = _validated_result(
                        row=row,
                        expected_employment_record_id=detached_command.employment_record_id,
                    )
        except Exception as error:
            _translate_database_error(error)

        return result
