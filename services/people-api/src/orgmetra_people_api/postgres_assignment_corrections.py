"""Atomic PostgreSQL adapter for governed Assignment category corrections."""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable
from uuid import UUID

from orgmetra_hris_kernel import (
    AssignmentFact,
    AuditOutboxEvent,
    KernelError,
    correct_assignment_category as build_assignment_category_correction,
    validate_assignment_write,
)
from orgmetra_keyverse_adapter import AuthorizationDecision

from orgmetra_people_api.assignment_correction_mutations import (
    AssignmentCorrectionMutationCommand,
    AssignmentCorrectionMutationResult,
    assignment_correction_command_digest,
)
from orgmetra_people_api.mutations import PeopleMutationIntegrityError, idempotency_record_id
from orgmetra_people_api.postgres_mutations import (
    _INSERT_IDEMPOTENCY_SQL,
    _LOOKUP_IDEMPOTENCY_SQL,
    _POST_LOCK_RECORDED_AT_SQL,
    _READ_IDEMPOTENCY_SQL,
    _READ_WRITE_SQL,
    _TENANT_CONTEXT_SQL,
    _assignment_from_row,
    _employment_version_from_row,
    _position_version_from_row,
    _post_lock_recorded_at,
    _record_audit,
)

PostgresConnectionFactory = Callable[[], AbstractContextManager[Any]]

_CORRECTION_ROUTE = "assignment-category-corrections"
_CORRECTION_FIELDS = frozenset({"assignment_category_code"})

_READ_PREDECESSOR_SQL = """
SELECT
    assignment.assignment_record_id,
    assignment.employment_record_id,
    assignment.person_record_id,
    assignment.position_record_id,
    assignment.allocation_ratio,
    assignment.assignment_category_code,
    assignment.effective_from,
    assignment.effective_to,
    assignment.recorded_from,
    assignment.recorded_to
FROM public.assignment_record AS assignment
WHERE assignment.tenant_record_id = %s
  AND assignment.assignment_record_id = %s
  AND assignment.recorded_to IS NULL
LIMIT 2
""".strip()

_LOCK_EMPLOYMENT_VERSIONS_SQL = """
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
FOR UPDATE OF employment
""".strip()

_LOCK_POSITION_VERSIONS_SQL = """
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

_LOCK_ASSIGNMENT_PORTFOLIO_SQL = """
SELECT
    assignment.assignment_record_id,
    assignment.employment_record_id,
    assignment.person_record_id,
    assignment.position_record_id,
    assignment.allocation_ratio,
    assignment.assignment_category_code,
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
ORDER BY assignment.assignment_record_id
FOR UPDATE OF assignment
""".strip()

_CLOSE_PREDECESSOR_SQL = """
UPDATE public.assignment_record
SET recorded_to = %s
WHERE tenant_record_id = %s
  AND assignment_record_id = %s
  AND recorded_to IS NULL
""".strip()

_INSERT_REPLACEMENT_SQL = """
INSERT INTO public.assignment_record (
    tenant_record_id,
    assignment_record_id,
    employment_record_id,
    person_record_id,
    position_record_id,
    allocation_ratio,
    assignment_category_code,
    effective_from,
    effective_to,
    recorded_from
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
""".strip()

_INSERT_SUPERSESSION_SQL = """
INSERT INTO public.assignment_supersession_record (
    tenant_record_id,
    assignment_supersession_record_id,
    predecessor_assignment_record_id,
    replacement_assignment_record_id,
    recorded_at
) VALUES (%s, %s, %s, %s, %s)
""".strip()

_READ_REPLAY_SUPERSESSION_SQL = """
SELECT
    supersession.assignment_supersession_record_id,
    supersession.replacement_assignment_record_id
FROM public.assignment_supersession_record AS supersession
WHERE supersession.tenant_record_id = %s
  AND supersession.predecessor_assignment_record_id = %s
  AND supersession.replacement_assignment_record_id = %s
LIMIT 2
""".strip()


def _is_operational_uuid(value: object) -> bool:
    """Return whether a database identity is an exact non-reserved UUID."""
    return type(value) is UUID and value.int not in (0, (1 << 128) - 1)


def _is_sha256(value: object) -> bool:
    """Return whether a stored command digest is one exact lowercase SHA-256 token."""
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _require_correction_authorization(
    *,
    authorization: object,
    command: AssignmentCorrectionMutationCommand,
) -> AuthorizationDecision:
    """Require the exact allow decision for the predecessor category correction."""
    if type(authorization) is not AuthorizationDecision:
        raise PeopleMutationIntegrityError("assignment correction requires an exact authorization decision")
    if (
        not authorization.allowed
        or authorization.tenant_record_id != command.tenant_record_id
        or authorization.resource_reference
        != f"assignment_record:{command.predecessor_assignment_record_id.hex}"
        or authorization.resource_kind != "assignment_record"
        or authorization.operation_code != "correct_record"
        or authorization.requested_fields != _CORRECTION_FIELDS
        or authorization.authorized_fields != _CORRECTION_FIELDS
    ):
        raise PeopleMutationIntegrityError("assignment correction authorization does not match the predecessor")
    return authorization


def _assignment_from_locked_row(tenant_record_id: UUID, row: tuple[object, ...]) -> AssignmentFact:
    """Reconstruct one locked Assignment without trusting executable Decimal subclasses."""
    if len(row) != 10 or type(row[4]) is not Decimal:
        raise PeopleMutationIntegrityError("assignment row is invalid")
    return _assignment_from_row(tenant_record_id, row)


def _require_one_predecessor(
    tenant_record_id: UUID,
    rows: list[tuple[object, ...]],
) -> AssignmentFact:
    """Require one recorded-open authoritative predecessor inside tenant scope."""
    if len(rows) != 1:
        raise PeopleMutationIntegrityError("assignment correction predecessor is missing or ambiguous")
    predecessor = _assignment_from_locked_row(tenant_record_id, rows[0])
    if predecessor.recorded.end is not None:
        raise PeopleMutationIntegrityError("assignment correction predecessor is already closed")
    return predecessor


def _require_locked_predecessor(
    *,
    candidate: AssignmentFact,
    portfolio: list[AssignmentFact],
) -> AssignmentFact:
    """Re-resolve the predecessor from the deterministically locked Assignment portfolio."""
    matches = [
        assignment
        for assignment in portfolio
        if assignment.assignment_record_id == candidate.assignment_record_id
    ]
    if len(matches) != 1:
        raise PeopleMutationIntegrityError("assignment correction predecessor is missing or ambiguous")
    predecessor = matches[0]
    if predecessor.recorded.end is not None:
        raise PeopleMutationIntegrityError("assignment correction predecessor is already closed")
    if (
        predecessor.employment_record_id != candidate.employment_record_id
        or predecessor.person_record_id != candidate.person_record_id
        or predecessor.position_record_id != candidate.position_record_id
    ):
        raise PeopleMutationIntegrityError("assignment correction predecessor identity changed during locking")
    return predecessor


def _replayed_correction(
    cursor: Any,
    *,
    command: AssignmentCorrectionMutationCommand,
    authorization: AuthorizationDecision,
) -> AssignmentCorrectionMutationResult | None:
    """Serialize one replay key and return the first committed correction when present."""
    key_parameters = (command.tenant_record_id, _CORRECTION_ROUTE, command.idempotency_key)
    cursor.execute(_LOOKUP_IDEMPOTENCY_SQL, key_parameters)
    cursor.execute(_READ_IDEMPOTENCY_SQL, key_parameters)
    rows = cursor.fetchmany(2)
    if not rows:
        return None
    if len(rows) != 1 or len(rows[0]) != 2:
        raise PeopleMutationIntegrityError("assignment correction idempotency row is invalid")
    replacement_record_id, stored_digest = rows[0]
    if not _is_operational_uuid(replacement_record_id) or not _is_sha256(stored_digest):
        raise PeopleMutationIntegrityError("assignment correction idempotency row is invalid")
    expected_digest = assignment_correction_command_digest(
        command=command,
        authorization=authorization,
    )
    if stored_digest != expected_digest:
        raise PeopleMutationIntegrityError("idempotency key is bound to a different command")
    assert isinstance(replacement_record_id, UUID)
    cursor.execute(
        _READ_REPLAY_SUPERSESSION_SQL,
        (
            command.tenant_record_id,
            command.predecessor_assignment_record_id,
            replacement_record_id,
        ),
    )
    supersession_rows = cursor.fetchmany(2)
    if len(supersession_rows) != 1 or len(supersession_rows[0]) != 2:
        raise PeopleMutationIntegrityError("assignment correction replay provenance is invalid")
    supersession_record_id, linked_replacement_id = supersession_rows[0]
    if (
        not _is_operational_uuid(supersession_record_id)
        or type(linked_replacement_id) is not UUID
        or linked_replacement_id != replacement_record_id
    ):
        raise PeopleMutationIntegrityError("assignment correction replay provenance is invalid")
    assert isinstance(supersession_record_id, UUID)
    return AssignmentCorrectionMutationResult(
        replacement_assignment_record_id=replacement_record_id,
        assignment_supersession_record_id=supersession_record_id,
    )


def _record_correction_idempotency(
    cursor: Any,
    *,
    command: AssignmentCorrectionMutationCommand,
    authorization: AuthorizationDecision,
    replacement_record_id: UUID,
) -> None:
    """Persist semantic replay evidence with the replacement inside the transaction."""
    cursor.execute(
        _INSERT_IDEMPOTENCY_SQL,
        (
            command.tenant_record_id,
            idempotency_record_id(
                tenant_record_id=command.tenant_record_id,
                command_route_value=_CORRECTION_ROUTE,
                idempotency_key=command.idempotency_key,
            ),
            _CORRECTION_ROUTE,
            command.idempotency_key,
            assignment_correction_command_digest(
                command=command,
                authorization=authorization,
            ),
            replacement_record_id,
        ),
    )


@dataclass(frozen=True, slots=True)
class PostgresAssignmentCorrectionMutationPort:
    """Persist one reviewed Assignment category correction in a tenant transaction."""

    connection_factory: PostgresConnectionFactory

    def __post_init__(self) -> None:
        """Reject an unusable database factory before a protected correction starts."""
        if not callable(self.connection_factory):
            raise TypeError("connection_factory must be callable")

    def correct_assignment_category(
        self,
        *,
        command: AssignmentCorrectionMutationCommand,
        authorization: AuthorizationDecision,
    ) -> AssignmentCorrectionMutationResult:
        """Lock, revalidate, replace, link, audit, and bind replay evidence atomically."""
        if type(command) is not AssignmentCorrectionMutationCommand:
            raise TypeError("command must be an exact AssignmentCorrectionMutationCommand")
        decision = _require_correction_authorization(
            authorization=authorization,
            command=command,
        )
        with self.connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(_READ_WRITE_SQL)
                cursor.execute(_TENANT_CONTEXT_SQL, (str(command.tenant_record_id),))
                replayed = _replayed_correction(
                    cursor,
                    command=command,
                    authorization=decision,
                )
                if replayed is not None:
                    return replayed

                cursor.execute(
                    _READ_PREDECESSOR_SQL,
                    (command.tenant_record_id, command.predecessor_assignment_record_id),
                )
                candidate = _require_one_predecessor(
                    command.tenant_record_id,
                    cursor.fetchmany(2),
                )

                cursor.execute(
                    _LOCK_EMPLOYMENT_VERSIONS_SQL,
                    (command.tenant_record_id, candidate.employment_record_id),
                )
                employment_versions = [
                    _employment_version_from_row(command.tenant_record_id, row)
                    for row in cursor.fetchall()
                ]
                cursor.execute(
                    _LOCK_POSITION_VERSIONS_SQL,
                    (command.tenant_record_id, candidate.position_record_id),
                )
                position_versions = [
                    _position_version_from_row(command.tenant_record_id, row)
                    for row in cursor.fetchall()
                ]

                cursor.execute(
                    _LOCK_ASSIGNMENT_PORTFOLIO_SQL,
                    (
                        command.tenant_record_id,
                        candidate.employment_record_id,
                        candidate.position_record_id,
                    ),
                )
                portfolio = [
                    _assignment_from_locked_row(command.tenant_record_id, row)
                    for row in cursor.fetchall()
                ]
                predecessor = _require_locked_predecessor(
                    candidate=candidate,
                    portfolio=portfolio,
                )
                recorded_at = _post_lock_recorded_at(cursor)
                try:
                    closed, replacement, supersession = build_assignment_category_correction(
                        predecessor,
                        replacement_assignment_record_id=command.replacement_assignment_record_id,
                        assignment_supersession_record_id=command.assignment_supersession_record_id,
                        corrected_category_code=command.corrected_category_code,
                        recorded_at=recorded_at,
                    )
                    other_assignments = [
                        assignment
                        for assignment in portfolio
                        if assignment.assignment_record_id != predecessor.assignment_record_id
                    ]
                    validate_assignment_write(
                        replacement,
                        [*other_assignments, closed, replacement],
                        employment_versions,
                        position_versions,
                        known_at=recorded_at,
                    )
                except KernelError as error:
                    raise PeopleMutationIntegrityError(str(error)) from error

                cursor.execute(
                    _CLOSE_PREDECESSOR_SQL,
                    (
                        recorded_at,
                        command.tenant_record_id,
                        predecessor.assignment_record_id,
                    ),
                )
                cursor.execute(
                    _INSERT_REPLACEMENT_SQL,
                    (
                        replacement.tenant_record_id,
                        replacement.assignment_record_id,
                        replacement.employment_record_id,
                        replacement.person_record_id,
                        replacement.position_record_id,
                        replacement.allocation_ratio,
                        replacement.assignment_category_code,
                        replacement.effective.start,
                        replacement.effective.end,
                        recorded_at,
                    ),
                )
                cursor.execute(
                    _INSERT_SUPERSESSION_SQL,
                    (
                        supersession.tenant_record_id,
                        supersession.assignment_supersession_record_id,
                        supersession.predecessor_assignment_record_id,
                        supersession.replacement_assignment_record_id,
                        supersession.recorded_at,
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
                        event_type="orgmetra.people.assignment_category_corrected",
                        resource_reference=(
                            f"assignment_record:{command.predecessor_assignment_record_id}"
                        ),
                        actor_reference=decision.actor_reference,
                        purpose_code=decision.purpose_code,
                        reason_code="assignment_category_corrected",
                        evidence_version_code=command.evidence_version_code,
                        result_code="assignment_category_corrected",
                        occurred_at=recorded_at,
                        high_impact=True,
                        confirmation_reference=command.confirmation_reference,
                    ),
                )
                _record_correction_idempotency(
                    cursor,
                    command=command,
                    authorization=decision,
                    replacement_record_id=replacement.assignment_record_id,
                )
        return AssignmentCorrectionMutationResult(
            replacement_assignment_record_id=command.replacement_assignment_record_id,
            assignment_supersession_record_id=command.assignment_supersession_record_id,
        )
