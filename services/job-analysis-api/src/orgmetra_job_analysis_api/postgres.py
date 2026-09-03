"""Tenant-bound PostgreSQL adapter for job-analysis snapshot persistence.

The adapter owns write-side and read-side SQL for the 3NF snapshot relations.
Writes bind tenant RLS, require the existing job (and optional position or
criterion) identity, persist the Idempotency-Key on the write-command row, and
call ``record_audit_outbox_event(...)`` in the same transaction as the
authoritative insert. A missing parent identity fails closed.
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

from orgmetra_hris_kernel import (
    AuditOutboxEvent,
    EvidenceSource,
    FunctionalJobAnalysisProfile,
    JobAnalysisSnapshot,
    KSAORequirement,
    TaskEvidence,
    TaskKSAOLink,
)

from orgmetra_job_analysis_api.snapshot import (
    JobAnalysisIdempotencyConflict,
    JobAnalysisIntegrityError,
    JobAnalysisScopeMissing,
    _validate_idempotency_key,
    command_digest,
    snapshot_from_document,
    validate_operational_uuid,
)

PostgresConnectionFactory = Callable[[], AbstractContextManager[Any]]

_REQUEST_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_EXPECTED_AUDIT_SOURCE_SERVICE = "job_analysis_api"
_EXPECTED_AUDIT_EVENT_TYPE = "orgmetra.job_architecture.snapshot_recorded"
_EXPECTED_AUDIT_REASON_CODE = "snapshot_persisted"
_EXPECTED_AUDIT_RESULT_CODE = "recorded"
_TENANT_CONTEXT_SQL = "SELECT pg_catalog.set_config('orgmetra.tenant_record_id', %s, true)"
_READ_ONLY_SQL = "SET TRANSACTION READ ONLY"
_IDEMPOTENCY_LOOKUP_SQL = """
WITH idempotency_lock AS MATERIALIZED (
    SELECT pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(pg_catalog.concat(%s, ':', %s), 0)
    )
)
SELECT
    command_record.request_digest_sha256,
    command_record.analysis_record_id,
    command_record.actor_reference,
    command_record.purpose_code
FROM idempotency_lock
LEFT JOIN LATERAL (
    SELECT request_digest_sha256, analysis_record_id, actor_reference, purpose_code
    FROM public.job_analysis_write_command
    WHERE tenant_record_id = %s
      AND idempotency_key = %s
    LIMIT 1
) AS command_record ON TRUE
""".strip()
_JOB_SCOPE_SQL = """
SELECT job_profile_id
FROM public.job_profile
WHERE tenant_record_id = %s
  AND job_profile_id = %s
  AND recorded_to IS NULL
LIMIT 1
""".strip()
_POSITION_SCOPE_SQL = """
SELECT position_record_id, job_profile_id
FROM public.position_record
WHERE tenant_record_id = %s
  AND position_record_id = %s
  AND recorded_to IS NULL
LIMIT 1
""".strip()
_CRITERION_SCOPE_SQL = """
SELECT criterion_blueprint_id, job_profile_id
FROM public.criterion_blueprint
WHERE tenant_record_id = %s
  AND criterion_blueprint_id = %s
  AND recorded_to IS NULL
LIMIT 1
""".strip()
_INSERT_SNAPSHOT_SQL = """
INSERT INTO public.job_analysis_snapshot (
    tenant_record_id, analysis_record_id, job_profile_id, position_record_id,
    criterion_blueprint_id, analysis_version_code, status_code, effective_from,
    recorded_at, reviewed_by_reference, reviewed_at, content_digest_sha256,
    data_function_code, people_function_code, things_function_code,
    fja_source_uri, fja_source_title, fja_source_version_code, fja_retrieved_at,
    fja_content_digest_sha256, fja_origin_code
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
""".strip()
_INSERT_TASK_SQL = """
INSERT INTO public.job_analysis_task_item (
    tenant_record_id, analysis_record_id, task_record_id, task_statement,
    importance_level, difficulty_level, source_uri, source_title,
    source_version_code, retrieved_at, content_digest_sha256, origin_code
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
""".strip()
_INSERT_KSAO_SQL = """
INSERT INTO public.job_analysis_ksao_item (
    tenant_record_id, analysis_record_id, ksao_record_id, category_code,
    requirement_statement, importance_level, proficiency_level, source_uri,
    source_title, source_version_code, retrieved_at, content_digest_sha256,
    origin_code
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
""".strip()
_INSERT_LINK_SQL = """
INSERT INTO public.job_analysis_task_ksao_link (
    tenant_record_id, analysis_record_id, task_record_id, ksao_record_id,
    relationship_strength, essential_for_task
) VALUES (
    %s, %s, %s, %s, %s, %s
)
""".strip()
_INSERT_COMMAND_SQL = """
INSERT INTO public.job_analysis_write_command (
    tenant_record_id, write_command_id, analysis_record_id, idempotency_key,
    request_digest_sha256, actor_reference, purpose_code
) VALUES (
    %s, %s, %s, %s, %s, %s, %s
)
""".strip()
_AUDIT_OUTBOX_SQL = """
SELECT public.record_audit_outbox_event(%s, %s, %s, %s, %s, %s)
""".strip()
_READ_SNAPSHOT_SQL = """
SELECT
    tenant_record_id, analysis_record_id, job_profile_id, analysis_version_code,
    status_code, effective_from, recorded_at, reviewed_by_reference, reviewed_at,
    content_digest_sha256, data_function_code, people_function_code,
    things_function_code, fja_source_uri, fja_source_title,
    fja_source_version_code, fja_retrieved_at, fja_content_digest_sha256,
    fja_origin_code
FROM public.job_analysis_snapshot
WHERE tenant_record_id = %s
  AND analysis_record_id = %s
LIMIT 2
""".strip()
_READ_TASKS_SQL = """
SELECT
    task_record_id, task_statement, importance_level, difficulty_level,
    source_uri, source_title, source_version_code, retrieved_at,
    content_digest_sha256, origin_code
FROM public.job_analysis_task_item
WHERE tenant_record_id = %s
  AND analysis_record_id = %s
ORDER BY task_record_id
""".strip()
_READ_KSAOS_SQL = """
SELECT
    ksao_record_id, category_code, requirement_statement, importance_level,
    proficiency_level, source_uri, source_title, source_version_code,
    retrieved_at, content_digest_sha256, origin_code
FROM public.job_analysis_ksao_item
WHERE tenant_record_id = %s
  AND analysis_record_id = %s
ORDER BY ksao_record_id
""".strip()
_READ_LINKS_SQL = """
SELECT task_record_id, ksao_record_id, relationship_strength, essential_for_task
FROM public.job_analysis_task_ksao_link
WHERE tenant_record_id = %s
  AND analysis_record_id = %s
ORDER BY task_record_id, ksao_record_id
""".strip()


def _utc(value: datetime) -> datetime:
    """Normalize an already-validated instant to UTC for persistence binding."""
    return value.astimezone(timezone.utc)


def _source_params(source: EvidenceSource) -> tuple[object, ...]:
    """Return bound evidence-source columns in insert order."""
    return (
        source.source_uri,
        source.source_title,
        source.source_version_code,
        _utc(source.retrieved_at),
        source.content_digest_sha256,
        source.origin_code,
    )


def _validate_durable_command_scalars(
    *,
    idempotency_key: object,
    request_digest: object,
    actor_reference: object,
    purpose_code: object,
) -> None:
    """Reject malformed durable command text before acquiring PostgreSQL resources."""
    if type(idempotency_key) is not str:
        raise ValueError("idempotency_key must be exact built-in text.")
    _validate_idempotency_key(idempotency_key)
    if type(request_digest) is not str or _REQUEST_DIGEST_PATTERN.fullmatch(request_digest) is None:
        raise ValueError("request_digest must be an exact lowercase SHA-256 digest.")
    if type(actor_reference) is not str:
        raise ValueError("actor_reference must be exact built-in text.")
    if type(purpose_code) is not str:
        raise ValueError("purpose_code must be exact built-in text.")


def _detach_durable_snapshot(snapshot: JobAnalysisSnapshot) -> JobAnalysisSnapshot:
    """Rebuild exact snapshot evidence before any executable database boundary runs."""
    tenant_record_id = validate_operational_uuid(
        "snapshot.tenant_record_id",
        snapshot.tenant_record_id,
    )
    canonical_json = snapshot.canonical_json()
    document = json.loads(canonical_json)
    detached = snapshot_from_document(document, tenant_record_id=tenant_record_id)
    if detached.canonical_json() != canonical_json:
        raise JobAnalysisIntegrityError("detached snapshot does not match canonical evidence")
    return detached


@dataclass(frozen=True, slots=True)
class _DurableAuditEvidence:
    """Detached Job Analysis audit evidence frozen before PostgreSQL acquisition."""

    event_id: UUID
    tenant_record_id: UUID
    source_service: str
    event_type: str
    resource_reference: str
    actor_reference: str
    purpose_code: str
    reason_code: str
    evidence_version_code: str
    result_code: str
    high_impact: bool
    confirmation_reference: str | None
    canonical_json: str
    content_digest: str


def _snapshot_durable_audit_authority(
    audit_event: AuditOutboxEvent,
) -> _DurableAuditEvidence:
    """Freeze exact audit authority, semantics, and canonical bytes before DB acquisition."""
    event_id = validate_operational_uuid("audit_event.event_id", audit_event.event_id)
    tenant_record_id = validate_operational_uuid(
        "audit_event.tenant_record_id",
        audit_event.tenant_record_id,
    )
    audit_text: dict[str, str] = {}
    for field_name in (
        "source_service",
        "event_type",
        "resource_reference",
        "actor_reference",
        "purpose_code",
        "reason_code",
        "evidence_version_code",
        "result_code",
    ):
        value = getattr(audit_event, field_name)
        if type(value) is not str:
            raise ValueError(f"audit_event.{field_name} must be exact built-in text.")
        audit_text[field_name] = value
    high_impact = audit_event.high_impact
    confirmation_reference = audit_event.confirmation_reference
    canonical_json = audit_event.canonical_json()
    canonical_event = json.loads(canonical_json)
    if (
        canonical_event.get("id") != str(event_id)
        or canonical_event.get("orgmetratenant") != str(tenant_record_id)
        or canonical_event.get("subject") != audit_text["resource_reference"]
        or canonical_event.get("orgmetraactor") != audit_text["actor_reference"]
        or canonical_event.get("orgmetrapurpose") != audit_text["purpose_code"]
    ):
        raise JobAnalysisIntegrityError(
            "canonical audit evidence does not match validated authority"
        )
    if (
        canonical_event.get("source") != f"urn:orgmetra:{audit_text['source_service']}"
        or canonical_event.get("type") != audit_text["event_type"]
        or canonical_event.get("orgmetrareason") != audit_text["reason_code"]
        or canonical_event.get("orgmetraevidence") != audit_text["evidence_version_code"]
        or canonical_event.get("data")
        != {
            "result_code": audit_text["result_code"],
            "high_impact": high_impact,
        }
        or canonical_event.get("orgmetraconfirmation") != confirmation_reference
    ):
        raise JobAnalysisIntegrityError(
            "canonical audit evidence does not match validated semantics"
        )
    content_digest = sha256(canonical_json.encode("utf-8")).hexdigest()
    return _DurableAuditEvidence(
        event_id=event_id,
        tenant_record_id=tenant_record_id,
        source_service=audit_text["source_service"],
        event_type=audit_text["event_type"],
        resource_reference=audit_text["resource_reference"],
        actor_reference=audit_text["actor_reference"],
        purpose_code=audit_text["purpose_code"],
        reason_code=audit_text["reason_code"],
        evidence_version_code=audit_text["evidence_version_code"],
        result_code=audit_text["result_code"],
        high_impact=high_impact,
        confirmation_reference=confirmation_reference,
        canonical_json=canonical_json,
        content_digest=content_digest,
    )


def _is_unique_violation(error: Exception) -> bool:
    """Return whether a PostgreSQL DB-API error reports SQLSTATE 23505."""
    return getattr(error, "sqlstate", getattr(error, "pgcode", None)) == "23505"


def _constraint_name(error: Exception) -> str | None:
    """Return a driver-provided PostgreSQL constraint name when available."""
    diagnostic = getattr(error, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)
    return constraint_name if isinstance(constraint_name, str) else None


@dataclass(frozen=True, slots=True)
class PostgresJobAnalysisPort:
    """Persist and reconstruct snapshots through parameterized PostgreSQL SQL.

    ``connection_factory`` must return a DB-API-compatible connection context
    manager. Deployment code owns pooling, credentials, TLS, and role selection.
    """

    connection_factory: PostgresConnectionFactory

    def __post_init__(self) -> None:
        """Reject unusable factories before any protected write or read."""
        if not callable(self.connection_factory):
            raise TypeError("connection_factory must be callable")

    def persist_snapshot(
        self,
        *,
        snapshot: JobAnalysisSnapshot,
        idempotency_key: str,
        request_digest: str,
        actor_reference: str,
        purpose_code: str,
        position_record_id: UUID | None,
        criterion_blueprint_id: UUID | None,
        audit_event: AuditOutboxEvent,
        outbox_delivery_record_id: UUID,
        write_command_id: UUID,
    ) -> JobAnalysisSnapshot:
        """Insert one snapshot or replay an identical Idempotency-Key command.

        The Idempotency-Key is written to ``job_analysis_write_command``. A
        reused key with a different digest, actor, or purpose is rejected.
        ``record_audit_outbox_event`` runs only for a new write, inside the same
        transaction.
        """
        if type(snapshot) is not JobAnalysisSnapshot:
            raise TypeError("snapshot must be an exact JobAnalysisSnapshot")
        if type(audit_event) is not AuditOutboxEvent:
            raise TypeError("audit_event must be an exact AuditOutboxEvent")
        _validate_durable_command_scalars(
            idempotency_key=idempotency_key,
            request_digest=request_digest,
            actor_reference=actor_reference,
            purpose_code=purpose_code,
        )
        snapshot = _detach_durable_snapshot(snapshot)
        audit_evidence = _snapshot_durable_audit_authority(audit_event)
        write_command_id = validate_operational_uuid("write_command_id", write_command_id)
        outbox_delivery_record_id = validate_operational_uuid(
            "outbox_delivery_record_id",
            outbox_delivery_record_id,
        )
        if position_record_id is not None:
            position_record_id = validate_operational_uuid("position_record_id", position_record_id)
        if criterion_blueprint_id is not None:
            criterion_blueprint_id = validate_operational_uuid(
                "criterion_blueprint_id",
                criterion_blueprint_id,
            )
        expected_request_digest = command_digest(
            snapshot=snapshot,
            position_record_id=position_record_id,
            criterion_blueprint_id=criterion_blueprint_id,
        )
        if request_digest != expected_request_digest:
            raise JobAnalysisIntegrityError(
                "request_digest does not match detached snapshot command"
            )
        expected_resource_reference = f"job_analysis_snapshot:{snapshot.analysis_record_id.hex}"
        if (
            audit_evidence.tenant_record_id != snapshot.tenant_record_id
            or audit_evidence.resource_reference != expected_resource_reference
            or audit_evidence.actor_reference != actor_reference
            or audit_evidence.purpose_code != purpose_code
        ):
            raise JobAnalysisIntegrityError(
                "audit event does not match the job-analysis write authority"
            )
        if (
            audit_evidence.source_service != _EXPECTED_AUDIT_SOURCE_SERVICE
            or audit_evidence.event_type != _EXPECTED_AUDIT_EVENT_TYPE
            or audit_evidence.reason_code != _EXPECTED_AUDIT_REASON_CODE
            or audit_evidence.evidence_version_code != snapshot.analysis_version_code
            or audit_evidence.result_code != _EXPECTED_AUDIT_RESULT_CODE
            or audit_evidence.high_impact is not False
            or audit_evidence.confirmation_reference is not None
        ):
            raise JobAnalysisIntegrityError(
                "audit event does not match the job-analysis snapshot semantics"
            )

        with self.connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(_TENANT_CONTEXT_SQL, (str(snapshot.tenant_record_id),))
                cursor.execute(
                    _IDEMPOTENCY_LOOKUP_SQL,
                    (
                        snapshot.tenant_record_id,
                        idempotency_key,
                        snapshot.tenant_record_id,
                        idempotency_key,
                    ),
                )
                existing = cursor.fetchone()
                if existing is not None and existing[0] is not None:
                    stored_digest, stored_analysis_id, *stored_authority = existing
                    if stored_digest != request_digest:
                        raise JobAnalysisIdempotencyConflict(
                            "idempotency key is bound to a different snapshot digest"
                        )
                    try:
                        stored_analysis_id = validate_operational_uuid(
                            "stored analysis_record_id",
                            stored_analysis_id,
                        )
                    except ValueError as error:
                        raise JobAnalysisIntegrityError(
                            "idempotent command has invalid analysis_record_id"
                        ) from error
                    if stored_analysis_id != snapshot.analysis_record_id:
                        raise JobAnalysisIntegrityError(
                            "idempotent command analysis_record_id does not match detached snapshot"
                        )
                    if stored_authority:
                        stored_actor_reference, stored_purpose_code = stored_authority
                        if stored_actor_reference != actor_reference:
                            raise JobAnalysisIdempotencyConflict(
                                "idempotency key is bound to a different actor"
                            )
                        if stored_purpose_code != purpose_code:
                            raise JobAnalysisIdempotencyConflict(
                                "idempotency key is bound to a different purpose"
                            )
                    replayed = self._load_snapshot(
                        cursor,
                        tenant_record_id=snapshot.tenant_record_id,
                        analysis_record_id=stored_analysis_id,
                    )
                    if replayed is None:
                        raise JobAnalysisIntegrityError("idempotent command lost its snapshot")
                    replayed_digest = command_digest(
                        snapshot=replayed,
                        position_record_id=position_record_id,
                        criterion_blueprint_id=criterion_blueprint_id,
                    )
                    if replayed_digest != request_digest:
                        raise JobAnalysisIntegrityError(
                            "idempotent replay snapshot does not match recorded command digest"
                        )
                    return replayed

                try:
                    cursor.execute(
                        _JOB_SCOPE_SQL,
                        (snapshot.tenant_record_id, snapshot.job_record_id),
                    )
                    if cursor.fetchone() is None:
                        raise JobAnalysisScopeMissing("job_profile does not exist in the tenant")
                    if position_record_id is not None:
                        cursor.execute(
                            _POSITION_SCOPE_SQL,
                            (snapshot.tenant_record_id, position_record_id),
                        )
                        position_row = cursor.fetchone()
                        if position_row is None or position_row[1] != snapshot.job_record_id:
                            raise JobAnalysisScopeMissing("position_record is missing or not bound to the job")
                    if criterion_blueprint_id is not None:
                        cursor.execute(
                            _CRITERION_SCOPE_SQL,
                            (snapshot.tenant_record_id, criterion_blueprint_id),
                        )
                        criterion_row = cursor.fetchone()
                        if criterion_row is None or criterion_row[1] != snapshot.job_record_id:
                            raise JobAnalysisScopeMissing(
                                "criterion_blueprint is missing or not bound to the job"
                            )

                    cursor.execute(
                        _INSERT_SNAPSHOT_SQL,
                        (
                            snapshot.tenant_record_id,
                            snapshot.analysis_record_id,
                            snapshot.job_record_id,
                            position_record_id,
                            criterion_blueprint_id,
                            snapshot.analysis_version_code,
                            snapshot.status_code,
                            snapshot.effective_from,
                            _utc(snapshot.recorded_at),
                            snapshot.reviewed_by_reference,
                            None if snapshot.reviewed_at is None else _utc(snapshot.reviewed_at),
                            snapshot.content_digest(),
                            snapshot.fja_profile.data_function_code,
                            snapshot.fja_profile.people_function_code,
                            snapshot.fja_profile.things_function_code,
                            *_source_params(snapshot.fja_profile.source),
                        ),
                    )
                except Exception as error:  # noqa: BLE001 - DB-API errors are normalized below.
                    if not _is_unique_violation(error):
                        raise
                    constraint_name = _constraint_name(error)
                    raise JobAnalysisIntegrityError(
                        f"job-analysis snapshot identity or version already exists ({constraint_name!r})"
                    ) from error

                for task in snapshot.tasks:
                    cursor.execute(
                        _INSERT_TASK_SQL,
                        (
                            snapshot.tenant_record_id,
                            snapshot.analysis_record_id,
                            task.task_record_id,
                            task.task_statement,
                            task.importance_level,
                            task.difficulty_level,
                            *_source_params(task.source),
                        ),
                    )
                for item in snapshot.ksao_requirements:
                    cursor.execute(
                        _INSERT_KSAO_SQL,
                        (
                            snapshot.tenant_record_id,
                            snapshot.analysis_record_id,
                            item.ksao_record_id,
                            item.category_code,
                            item.requirement_statement,
                            item.importance_level,
                            item.proficiency_level,
                            *_source_params(item.source),
                        ),
                    )
                for link in snapshot.task_ksao_links:
                    cursor.execute(
                        _INSERT_LINK_SQL,
                        (
                            snapshot.tenant_record_id,
                            snapshot.analysis_record_id,
                            link.task_record_id,
                            link.ksao_record_id,
                            link.relationship_strength,
                            link.essential_for_task,
                        ),
                    )
                try:
                    cursor.execute(
                        _INSERT_COMMAND_SQL,
                        (
                            snapshot.tenant_record_id,
                            write_command_id,
                            snapshot.analysis_record_id,
                            idempotency_key,
                            request_digest,
                            actor_reference,
                            purpose_code,
                        ),
                    )
                except Exception as error:  # noqa: BLE001 - DB-API errors are normalized below.
                    if not _is_unique_violation(error):
                        raise
                    constraint_name = _constraint_name(error)
                    raise JobAnalysisIdempotencyConflict(
                        f"idempotency or command identity was recorded concurrently ({constraint_name!r})"
                    ) from error
                cursor.execute(
                    _AUDIT_OUTBOX_SQL,
                    (
                        snapshot.tenant_record_id,
                        audit_evidence.event_id,
                        outbox_delivery_record_id,
                        audit_evidence.canonical_json,
                        audit_evidence.content_digest,
                        "integration_hub",
                    ),
                )
        return snapshot

    def read_snapshot(
        self,
        *,
        tenant_record_id: UUID,
        analysis_record_id: UUID,
    ) -> JobAnalysisSnapshot | None:
        """Read one snapshot under forced tenant RLS and reconstruct the kernel document."""
        tenant_record_id = validate_operational_uuid("tenant_record_id", tenant_record_id)
        analysis_record_id = validate_operational_uuid("analysis_record_id", analysis_record_id)
        with self.connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(_READ_ONLY_SQL)
                cursor.execute(_TENANT_CONTEXT_SQL, (str(tenant_record_id),))
                return self._load_snapshot(
                    cursor,
                    tenant_record_id=tenant_record_id,
                    analysis_record_id=analysis_record_id,
                )

    def _load_snapshot(
        self,
        cursor: Any,
        *,
        tenant_record_id: UUID,
        analysis_record_id: UUID,
    ) -> JobAnalysisSnapshot | None:
        """Assemble one kernel snapshot from normalized rows or return None."""
        cursor.execute(_READ_SNAPSHOT_SQL, (tenant_record_id, analysis_record_id))
        headers = cursor.fetchmany(2)
        if not headers:
            return None
        if len(headers) != 1:
            raise JobAnalysisIntegrityError("multiple snapshot headers match the requested target")
        header = headers[0]
        if header[0] != tenant_record_id or header[1] != analysis_record_id:
            raise JobAnalysisIntegrityError("database row escaped requested target")
        cursor.execute(_READ_TASKS_SQL, (tenant_record_id, analysis_record_id))
        task_rows = cursor.fetchall()
        cursor.execute(_READ_KSAOS_SQL, (tenant_record_id, analysis_record_id))
        ksao_rows = cursor.fetchall()
        cursor.execute(_READ_LINKS_SQL, (tenant_record_id, analysis_record_id))
        link_rows = cursor.fetchall()
        snapshot = JobAnalysisSnapshot(
            analysis_record_id=header[1],
            tenant_record_id=header[0],
            job_record_id=header[2],
            analysis_version_code=header[3],
            status_code=header[4],
            effective_from=header[5],
            recorded_at=header[6],
            tasks=tuple(_task_from_row(tenant_record_id, header[2], row) for row in task_rows),
            ksao_requirements=tuple(_ksao_from_row(tenant_record_id, header[2], row) for row in ksao_rows),
            task_ksao_links=tuple(
                TaskKSAOLink(
                    task_record_id=row[0],
                    ksao_record_id=row[1],
                    relationship_strength=row[2],
                    essential_for_task=row[3],
                )
                for row in link_rows
            ),
            fja_profile=FunctionalJobAnalysisProfile(
                tenant_record_id=tenant_record_id,
                job_record_id=header[2],
                data_function_code=header[10],
                people_function_code=header[11],
                things_function_code=header[12],
                source=_source_from_row(header[13:19]),
            ),
            reviewed_by_reference=header[7],
            reviewed_at=header[8],
        )
        if snapshot.content_digest() != header[9]:
            raise JobAnalysisIntegrityError("stored snapshot digest does not match reconstructed evidence")
        return snapshot


def _source_from_row(values: tuple[object, ...]) -> EvidenceSource:
    """Rebuild one evidence source from six persisted provenance columns."""
    return EvidenceSource(
        source_uri=values[0],
        source_title=values[1],
        source_version_code=values[2],
        retrieved_at=values[3],
        content_digest_sha256=values[4],
        origin_code=values[5],
    )


def _task_from_row(tenant_record_id: UUID, job_record_id: UUID, row: tuple[object, ...]) -> TaskEvidence:
    """Rebuild one task item from its persisted 3NF row."""
    return TaskEvidence(
        tenant_record_id=tenant_record_id,
        job_record_id=job_record_id,
        task_record_id=row[0],
        task_statement=row[1],
        importance_level=row[2],
        difficulty_level=row[3],
        source=_source_from_row(row[4:10]),
    )


def _ksao_from_row(tenant_record_id: UUID, job_record_id: UUID, row: tuple[object, ...]) -> KSAORequirement:
    """Rebuild one KSAO item from its persisted 3NF row."""
    return KSAORequirement(
        tenant_record_id=tenant_record_id,
        job_record_id=job_record_id,
        ksao_record_id=row[0],
        category_code=row[1],
        requirement_statement=row[2],
        importance_level=row[3],
        proficiency_level=row[4],
        source=_source_from_row(row[5:11]),
    )