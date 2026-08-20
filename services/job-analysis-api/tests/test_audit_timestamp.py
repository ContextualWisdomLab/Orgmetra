"""Regression contract for trustworthy job-analysis mutation audit chronology."""

from __future__ import annotations

from datetime import datetime, timezone
import unittest

from orgmetra_hris_kernel import AuditOutboxEvent, JobAnalysisSnapshot

from orgmetra_job_analysis_api.snapshot import persist_job_analysis_snapshot
from fixtures import (
    IDEMPOTENCY_KEY,
    TENANT,
    clinical_psychologist_document,
    write_policy,
    write_principal,
)


class _RecordingWritePort:
    """Capture the audit event crossing the persistence boundary."""

    def __init__(self) -> None:
        self.audit_event: AuditOutboxEvent | None = None

    def persist_snapshot(
        self,
        *,
        snapshot: JobAnalysisSnapshot,
        idempotency_key: str,
        request_digest: str,
        actor_reference: str,
        purpose_code: str,
        position_record_id: object,
        criterion_blueprint_id: object,
        audit_event: AuditOutboxEvent,
        outbox_delivery_record_id: object,
        write_command_id: object,
    ) -> JobAnalysisSnapshot:
        """Record immutable audit evidence and return the accepted snapshot."""
        del (
            idempotency_key,
            request_digest,
            actor_reference,
            purpose_code,
            position_record_id,
            criterion_blueprint_id,
            outbox_delivery_record_id,
            write_command_id,
        )
        self.audit_event = audit_event
        return snapshot


class JobAnalysisAuditTimestampTests(unittest.TestCase):
    """Separate caller evidence time from system-recorded mutation audit time."""

    def test_audit_occurrence_uses_command_time_not_caller_snapshot_time(self) -> None:
        """A caller must not be able to backdate or future-date the immutable audit event."""
        posted = clinical_psychologist_document()
        posted_recorded_at = datetime.fromisoformat(
            str(posted["recorded_at"]).replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        port = _RecordingWritePort()

        before_command = datetime.now(timezone.utc)
        persist_job_analysis_snapshot(
            principal=write_principal(),
            tenant_record_id=TENANT,
            document=posted,
            idempotency_key=IDEMPOTENCY_KEY,
            purpose_code="job_analysis_write",
            policy=write_policy(),
            write_port=port,
        )
        after_command = datetime.now(timezone.utc)

        self.assertIsNotNone(port.audit_event)
        assert port.audit_event is not None
        self.assertGreaterEqual(port.audit_event.occurred_at, before_command)
        self.assertLessEqual(port.audit_event.occurred_at, after_command)
        self.assertNotEqual(port.audit_event.occurred_at, posted_recorded_at)


if __name__ == "__main__":
    unittest.main()
