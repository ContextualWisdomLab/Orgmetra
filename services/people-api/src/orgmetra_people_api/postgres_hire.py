"""Atomic PostgreSQL adapter for materializing one human-confirmed hire.

The adapter writes only Orgmetra-owned canonical HRIS relations. It resolves the
already-sealed selection decision inside the same tenant-bound transaction,
constructs the published ``AuditOutboxEvent`` contract from immutable decision
provenance, persists audit/outbox evidence, and inserts the governed
candidate-to-worker conversion last so database triggers can revalidate the
entire transaction before commit.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from typing import Any, Callable
from uuid import UUID
from zoneinfo import ZoneInfo

from orgmetra_hris_kernel.audit import AuditOutboxEvent
from orgmetra_keyverse_adapter import AuthorizationDecision

from orgmetra_people_api.hire import (
    HireAcceptanceCommand,
    HireAcceptanceResult,
    HireDecisionIntegrityError,
    HireDecisionNotFound,
)
from orgmetra_people_api.mutations import idempotency_record_id

PostgresConnectionFactory = Callable[[], AbstractContextManager[Any]]

_READ_WRITE_SQL = "SET TRANSACTION ISOLATION LEVEL READ COMMITTED, READ WRITE"
_TENANT_CONTEXT_SQL = "SELECT pg_catalog.set_config('orgmetra.tenant_record_id', %s, true)"
_HIRE_MUTATION_FIELDS = frozenset({"candidate_worker_conversion"})
_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$")
_MAX_UUID_INT = (1 << 128) - 1
_HIRE_IDEMPOTENCY_ROUTE = "candidate-worker-conversions"

_DECISION_PROVENANCE_SQL = """
SELECT
    decision.actor_reference,
    decision.purpose_code,
    decision.decision_code,
    decision.confirmation_reference,
    decision.decided_at,
    decision.decision_evidence_set_id,
    pg_catalog.transaction_timestamp()
FROM public.selection_decision AS decision
JOIN public.decision_evidence_set AS evidence
  ON evidence.tenant_record_id = decision.tenant_record_id
 AND evidence.decision_evidence_set_id = decision.decision_evidence_set_id
 AND evidence.sealed_selection_decision_id = decision.selection_decision_id
 AND evidence.sealed_at IS NOT NULL
WHERE decision.tenant_record_id = %s
  AND decision.selection_decision_id = %s
  AND decision.candidate_profile_id = %s
  AND EXISTS (
      SELECT 1
      FROM public.selection_decision_evidence AS evidence_member
      WHERE evidence_member.tenant_record_id = decision.tenant_record_id
        AND evidence_member.decision_evidence_set_id = decision.decision_evidence_set_id
  )
LIMIT 2
""".strip()

_LOOKUP_HIRE_IDEMPOTENCY_SQL = """
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

_READ_HIRE_IDEMPOTENCY_SQL = """
SELECT
    replay.created_record_id,
    replay.command_digest
FROM public.people_mutation_idempotency_record AS replay
WHERE replay.tenant_record_id = %s
  AND replay.command_route = %s
  AND replay.idempotency_key = %s
LIMIT 2
""".strip()

_INSERT_PERSON_SQL = """
INSERT INTO public.person_record (
    tenant_record_id,
    person_record_id,
    recorded_from
) VALUES (%s, %s, %s)
""".strip()

_INSERT_PERSON_NAME_SQL = """
INSERT INTO public.person_name_record (
    tenant_record_id,
    person_name_record_id,
    person_record_id,
    display_name,
    effective_from,
    recorded_from
) VALUES (%s, %s, %s, %s, %s, %s)
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
    effective_from,
    recorded_from
) VALUES (%s, %s, %s, %s, %s, %s)
""".strip()

_RECORD_AUDIT_OUTBOX_SQL = "SELECT public.record_audit_outbox_event(%s, %s, %s, %s, %s, %s)"

_INSERT_CONVERSION_SQL = """
INSERT INTO public.candidate_worker_conversion_record (
    tenant_record_id,
    candidate_worker_conversion_record_id,
    candidate_profile_id,
    person_record_id,
    employment_record_id,
    selection_decision_id,
    audit_event_record_id,
    effective_from,
    recorded_from
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
""".strip()

_INSERT_HIRE_IDEMPOTENCY_SQL = """
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
    """Return whether a value is an Orgmetra operational UUID."""
    return type(value) is UUID and value.int not in (0, _MAX_UUID_INT)


def _is_aware_datetime(value: object) -> bool:
    """Return whether durable time is exact and backed by an inert standard provider."""
    if type(value) is not datetime or value.tzinfo is None:
        return False
    if type(value.tzinfo) not in (timezone, ZoneInfo):
        return False
    return value.utcoffset() is not None


def _validate_authorization(command: HireAcceptanceCommand, authorization: object) -> AuthorizationDecision:
    """Require an exact allow decision for this immutable selection decision."""
    expected_reference = f"selection_decision:{command.selection_decision_id.hex}"
    if type(authorization) is not AuthorizationDecision:
        raise HireDecisionIntegrityError("hire mutation requires a typed authorization decision")
    if (
        not authorization.allowed
        or authorization.tenant_record_id != command.tenant_record_id
        or authorization.resource_reference != expected_reference
        or authorization.resource_kind != "selection_decision"
        or authorization.operation_code != "materialize_worker"
        or authorization.requested_fields != _HIRE_MUTATION_FIELDS
        or authorization.authorized_fields != _HIRE_MUTATION_FIELDS
    ):
        raise HireDecisionIntegrityError("hire mutation authorization does not match the exact decision")
    return authorization


def _hire_command_digest(command: HireAcceptanceCommand, authorization: AuthorizationDecision) -> str:
    """Hash the exact confirmed-hire semantics without storing necessary PII in audit evidence."""
    payload = {
        "actor_reference": authorization.actor_reference,
        "command_route": _HIRE_IDEMPOTENCY_ROUTE,
        "method": "POST",
        "purpose_code": authorization.purpose_code,
        "semantic_command": {
            "audit_event_record_id": str(command.audit_event_record_id),
            "candidate_profile_id": str(command.candidate_profile_id),
            "candidate_worker_conversion_record_id": str(command.candidate_worker_conversion_record_id),
            "display_name": command.display_name,
            "effective_from": command.effective_from.isoformat(),
            "employment_record_id": str(command.employment_record_id),
            "employment_record_version_id": str(command.employment_record_version_id),
            "employment_status_code": command.employment_status_code,
            "outbox_delivery_record_id": str(command.outbox_delivery_record_id),
            "person_name_record_id": str(command.person_name_record_id),
            "person_record_id": str(command.person_record_id),
            "selection_decision_id": str(command.selection_decision_id),
        },
        "tenant_record_id": str(command.tenant_record_id),
    }
    return sha256(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()


def _replayed_hire(
    cursor: Any,
    *,
    command: HireAcceptanceCommand,
    authorization: AuthorizationDecision,
) -> HireAcceptanceResult | None:
    """Serialize one hire key and return the prior exact result when it already committed."""
    key_parameters = (command.tenant_record_id, _HIRE_IDEMPOTENCY_ROUTE, command.idempotency_key)
    cursor.execute(_LOOKUP_HIRE_IDEMPOTENCY_SQL, key_parameters)
    cursor.execute(_READ_HIRE_IDEMPOTENCY_SQL, key_parameters)
    rows = cursor.fetchmany(2)
    if not rows:
        return None
    if len(rows) != 1 or len(rows[0]) != 2:
        raise HireDecisionIntegrityError("hire idempotency row is invalid")
    created_record_id, stored_digest = rows[0]
    if not _is_operational_uuid(created_record_id) or type(stored_digest) is not str:
        raise HireDecisionIntegrityError("hire idempotency row is invalid")
    if stored_digest != _hire_command_digest(command, authorization):
        raise HireDecisionIntegrityError("hire idempotency key is bound to a different command")
    if created_record_id != command.candidate_worker_conversion_record_id:
        raise HireDecisionIntegrityError("hire idempotency result does not match the confirmed conversion")
    assert isinstance(created_record_id, UUID)
    return HireAcceptanceResult(
        person_record_id=command.person_record_id,
        employment_record_id=command.employment_record_id,
        candidate_worker_conversion_record_id=created_record_id,
    )


def _record_hire_idempotency(
    cursor: Any,
    *,
    command: HireAcceptanceCommand,
    authorization: AuthorizationDecision,
) -> None:
    """Persist the exact hire-command digest with the conversion in the current transaction."""
    cursor.execute(
        _INSERT_HIRE_IDEMPOTENCY_SQL,
        (
            command.tenant_record_id,
            idempotency_record_id(
                tenant_record_id=command.tenant_record_id,
                command_route_value=_HIRE_IDEMPOTENCY_ROUTE,
                idempotency_key=command.idempotency_key,
            ),
            _HIRE_IDEMPOTENCY_ROUTE,
            command.idempotency_key,
            _hire_command_digest(command, authorization),
            command.candidate_worker_conversion_record_id,
        ),
    )


@dataclass(frozen=True, slots=True)
class PostgresHireAcceptancePort:
    """Persist confirmed hire facts and governance evidence in one DB transaction.

    ``connection_factory`` must return a DB-API connection context manager whose
    successful exit commits and exceptional exit rolls back, as psycopg
    connections do. Pooling, TLS, credentials, and database roles remain a
    deployment concern outside this service package.
    """

    connection_factory: PostgresConnectionFactory

    def __post_init__(self) -> None:
        """Reject unusable database factories before protected mutation is attempted."""
        if not callable(self.connection_factory):
            raise TypeError("connection_factory must be callable")

    def accept_hire(
        self,
        *,
        command: HireAcceptanceCommand,
        authorization: AuthorizationDecision,
    ) -> HireAcceptanceResult:
        """Materialize one exact confirmed hire or replay its committed result.

        The database-side candidate-conversion trigger independently rechecks
        candidate identity, decision semantics, sealed evidence, human
        confirmation, event provenance, event time, and outbox existence. This
        adapter narrows the same invariants before writing necessary PII so a bad
        decision fails early while the database remains the final integrity
        authority. Tenant/route/key advisory serialization prevents concurrent
        retries from racing the unique idempotency binding.
        """
        if type(command) is not HireAcceptanceCommand:
            raise TypeError("command must be a HireAcceptanceCommand")
        decision = _validate_authorization(command, authorization)

        with self.connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(_READ_WRITE_SQL)
                cursor.execute(_TENANT_CONTEXT_SQL, (str(command.tenant_record_id),))
                replayed = _replayed_hire(cursor, command=command, authorization=decision)
                if replayed is not None:
                    return replayed
                cursor.execute(
                    _DECISION_PROVENANCE_SQL,
                    (
                        command.tenant_record_id,
                        command.selection_decision_id,
                        command.candidate_profile_id,
                    ),
                )
                rows = cursor.fetchmany(2)
                if not rows:
                    raise HireDecisionNotFound("confirmed hire decision with sealed evidence was not found")
                if len(rows) != 1:
                    raise HireDecisionIntegrityError("multiple decision provenance rows matched the hire")
                row = rows[0]
                if len(row) != 7:
                    raise HireDecisionIntegrityError("decision provenance row has an invalid shape")
                (
                    decision_actor_reference,
                    decision_purpose_code,
                    decision_code,
                    confirmation_reference,
                    decided_at,
                    evidence_set_id,
                    transaction_recorded_at,
                ) = row

                if any(
                    type(value) is not str
                    for value in (
                        decision_actor_reference,
                        decision_purpose_code,
                        decision_code,
                        confirmation_reference,
                    )
                ):
                    raise HireDecisionIntegrityError("selection decision provenance text is invalid")
                if decision_code != "hire":
                    raise HireDecisionIntegrityError("selection decision is not an explicit hire")
                if decision_actor_reference != decision.actor_reference:
                    raise HireDecisionIntegrityError("selection decision actor does not match authorized actor")
                if decision_purpose_code != decision.purpose_code:
                    raise HireDecisionIntegrityError("selection decision purpose does not match authorized purpose")
                if _REFERENCE_PATTERN.fullmatch(confirmation_reference) is None:
                    raise HireDecisionIntegrityError("selection decision lacks valid human confirmation")
                if not _is_operational_uuid(evidence_set_id):
                    raise HireDecisionIntegrityError("selection decision evidence set identity is invalid")
                if not _is_aware_datetime(decided_at) or not _is_aware_datetime(transaction_recorded_at):
                    raise HireDecisionIntegrityError("selection decision timestamps are invalid")
                assert isinstance(decided_at, datetime)
                assert isinstance(transaction_recorded_at, datetime)
                assert isinstance(evidence_set_id, UUID)
                if transaction_recorded_at < decided_at:
                    raise HireDecisionIntegrityError("transaction time cannot precede the confirmed hire decision")
                if command.effective_from < decided_at.date():
                    raise HireDecisionIntegrityError("hire effective date cannot precede the confirmed decision")

                event = AuditOutboxEvent(
                    event_id=command.audit_event_record_id,
                    tenant_record_id=command.tenant_record_id,
                    source_service="people_api",
                    event_type="orgmetra.candidate.worker_converted",
                    resource_reference=(
                        "candidate_worker_conversion_record:"
                        f"{command.candidate_worker_conversion_record_id}"
                    ),
                    actor_reference=decision_actor_reference,
                    purpose_code=decision_purpose_code,
                    reason_code="candidate_hire_confirmed",
                    evidence_version_code=f"decision_evidence_set:{evidence_set_id}",
                    result_code="worker_created",
                    occurred_at=transaction_recorded_at,
                    high_impact=True,
                    confirmation_reference=confirmation_reference,
                )

                cursor.execute(
                    _INSERT_PERSON_SQL,
                    (
                        command.tenant_record_id,
                        command.person_record_id,
                        transaction_recorded_at,
                    ),
                )
                cursor.execute(
                    _INSERT_PERSON_NAME_SQL,
                    (
                        command.tenant_record_id,
                        command.person_name_record_id,
                        command.person_record_id,
                        command.display_name,
                        command.effective_from,
                        transaction_recorded_at,
                    ),
                )
                cursor.execute(
                    _INSERT_EMPLOYMENT_SQL,
                    (
                        command.tenant_record_id,
                        command.employment_record_id,
                        command.person_record_id,
                        transaction_recorded_at,
                    ),
                )
                cursor.execute(
                    _INSERT_EMPLOYMENT_VERSION_SQL,
                    (
                        command.tenant_record_id,
                        command.employment_record_version_id,
                        command.employment_record_id,
                        command.employment_status_code,
                        command.effective_from,
                        transaction_recorded_at,
                    ),
                )
                cursor.execute(
                    _RECORD_AUDIT_OUTBOX_SQL,
                    (
                        command.tenant_record_id,
                        command.audit_event_record_id,
                        command.outbox_delivery_record_id,
                        event.canonical_json(),
                        event.content_digest(),
                        "orgmetra_domain_events",
                    ),
                )
                cursor.execute(
                    _INSERT_CONVERSION_SQL,
                    (
                        command.tenant_record_id,
                        command.candidate_worker_conversion_record_id,
                        command.candidate_profile_id,
                        command.person_record_id,
                        command.employment_record_id,
                        command.selection_decision_id,
                        command.audit_event_record_id,
                        command.effective_from,
                        transaction_recorded_at,
                    ),
                )
                _record_hire_idempotency(cursor, command=command, authorization=decision)

        return HireAcceptanceResult(
            person_record_id=command.person_record_id,
            employment_record_id=command.employment_record_id,
            candidate_worker_conversion_record_id=command.candidate_worker_conversion_record_id,
        )
