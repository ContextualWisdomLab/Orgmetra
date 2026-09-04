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
      <<continuation omitted for display>>
