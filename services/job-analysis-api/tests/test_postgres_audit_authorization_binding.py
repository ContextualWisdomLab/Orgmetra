"""Regression coverage for job-analysis authorization/audit binding at persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_hris_kernel import AuditOutboxEvent
from orgmetra_job_analysis_api.postgres import PostgresJobAnalysisPort
from orgmetra_job_analysis_api.snapshot import JobAnalysisIntegrityError, command_digest
from fixtures import ANALYSIS, IDEMPOTENCY_KEY, OTHER_TENANT, TENANT, clinical_psychologist_snapshot

_ACTOR_REFERENCE = "keyverse:actor-ja-1"
_PURPOSE_CODE = "job_analysis_write"
_RESOURCE_REFERENCE = f"job_analysis_snapshot:{ANALYSIS.hex}"


def _never_connect() -> object:
    """Prove invalid durable evidence is rejected before database acquisition."""
    raise AssertionError("database acquired before job-analysis audit binding validation")


def _audit_event(**overrides: object) -> AuditOutboxEvent:
    """Build one shaped audit envelope whose authority fields may be adversarially drifted."""
    snapshot = clinical_psychologist_snapshot()
    values: dict[str, object] = {
        "event_id": UUID("0198a412-6000-7000-8000-000000000401"),
        "tenant_record_id": TENANT,
        "source_service": "job_analysis_api",
        "event_type": "orgmetra.job_architecture.snapshot_recorded",
        "resource_reference": _RESOURCE_REFERENCE,
        "actor_reference": _ACTOR_REFERENCE,
        "purpose_code": _PURPOSE_CODE,
        "reason_code": "snapshot_persisted",
        "evidence_version_code": snapshot.analysis_version_code,
        "result_code": "recorded",
        "occurred_at": datetime(2026, 8, 18, 5, 1, tzinfo=timezone.utc),
        "high_impact": False,
    }
    values.update(overrides)
    return AuditOutboxEvent(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "audit_event",
    [
        _audit_event(actor_reference="keyverse:actor-ja-other"),
        _audit_event(purpose_code="job_analysis_read"),
        _audit_event(tenant_record_id=OTHER_TENANT),
        _audit_event(resource_reference="job_analysis_snapshot:0198a412600070008000000000000999"),
    ],
)
def test_job_analysis_audit_authority_drift_fails_before_database(
    audit_event: AuditOutboxEvent,
) -> None:
    """Command authority and durable audit provenance must describe the same write."""
    snapshot = clinical_psychologist_snapshot()
    port = PostgresJobAnalysisPort(_never_connect)

    with pytest.raises(JobAnalysisIntegrityError, match="audit event does not match the job-analysis write authority"):
        port.persist_snapshot(
            snapshot=snapshot,
            idempotency_key=IDEMPOTENCY_KEY,
            request_digest=command_digest(
                snapshot=snapshot,
                position_record_id=None,
                criterion_blueprint_id=None,
            ),
            actor_reference=_ACTOR_REFERENCE,
            purpose_code=_PURPOSE_CODE,
            position_record_id=None,
            criterion_blueprint_id=None,
            audit_event=audit_event,
            outbox_delivery_record_id=UUID("0198a412-6000-7000-8000-000000000402"),
            write_command_id=UUID("0198a412-6000-7000-8000-000000000403"),
        )
