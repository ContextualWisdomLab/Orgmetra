"""Executable contracts for snapshot parse, persist, and read use cases."""

from __future__ import annotations

from datetime import date, datetime, timezone
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDeniedError
from orgmetra_hris_kernel import AuditOutboxEvent, JobAnalysisSnapshot

from orgmetra_job_analysis_api.snapshot import (
    JobAnalysisIntegrityError,
    JobAnalysisSnapshotNotFound,
    command_digest,
    persist_job_analysis_snapshot,
    read_job_analysis_snapshot,
    snapshot_from_document,
)
from fixtures import (
    ANALYSIS,
    CRITERION,
    IDEMPOTENCY_KEY,
    JOB,
    OTHER_TENANT,
    POSITION,
    TENANT,
    clinical_psychologist_document,
    clinical_psychologist_snapshot,
    read_policy,
    read_principal,
    write_policy,
    write_principal,
)


class _ExecutableIdempotencyKey(str):
    """Model caller text that tries to execute through sequence validation hooks."""

    def __len__(self) -> int:
        """Raise if validation executes caller-controlled length behavior."""
        raise RuntimeError("idempotency key length hook executed")

    def __iter__(self):
        """Raise if validation executes caller-controlled iteration behavior."""
        raise RuntimeError("idempotency key iteration hook executed")


class RecordingWritePort:
    """Capture the exact write-port arguments, including Idempotency-Key."""

    def __init__(self, result: JobAnalysisSnapshot | None = None, *, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[dict[str, object]] = []

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
        """Record every keyword the use case forwarded to persistence."""
        self.calls.append(
            {
                "snapshot": snapshot,
                "idempotency_key": idempotency_key,
                "request_digest": request_digest,
                "actor_reference": actor_reference,
                "purpose_code": purpose_code,
                "position_record_id": position_record_id,
                "criterion_blueprint_id": criterion_blueprint_id,
                "audit_event": audit_event,
                "outbox_delivery_record_id": outbox_delivery_record_id,
                "write_command_id": write_command_id,
            }
        )
        if self.error is not None:
            raise self.error
        return self.result if self.result is not None else snapshot


class RecordingReadPort:
    """Return a configured snapshot and capture protected-read attempts."""

    def __init__(self, result: JobAnalysisSnapshot | None) -> None:
        self.result = result
        self.calls: list[tuple[UUID, UUID]] = []

    def read_snapshot(self, *, tenant_record_id: UUID, analysis_record_id: UUID) -> JobAnalysisSnapshot | None:
        """Return deterministic snapshot truth for use-case tests."""
        self.calls.append((tenant_record_id, analysis_record_id))
        return self.result


class SnapshotDocumentTests(unittest.TestCase):
    """Prove posted 임상심리사 documents rebuild the kernel snapshot exactly."""

    def test_clinical_psychologist_document_round_trips_through_kernel(self) -> None:
        posted = clinical_psychologist_document()
        rebuilt = snapshot_from_document(posted, tenant_record_id=TENANT)
        self.assertEqual(rebuilt.to_snapshot(), posted)
        self.assertIn("표준화된 심리검사를 실시하고", posted["tasks"][0]["task_statement"])

    def test_rejects_malformed_documents_before_persistence(self) -> None:
        posted = clinical_psychologist_document()
        cases = (
            ("not-an-object", TENANT),
            ({**posted, "tenant_record_id": str(OTHER_TENANT)}, TENANT),
            ({**posted, "tenant_record_id": "not-a-uuid"}, TENANT),
            ({**posted, "tenant_record_id": 12}, TENANT),
            ({**posted, "job_record_id": str(UUID(int=0))}, TENANT),
            ({**posted, "tasks": []}, TENANT),
            ({**posted, "tasks": "nope"}, TENANT),
            ({**posted, "tasks": ["bad"]}, TENANT),
            ({**posted, "ksao_requirements": []}, TENANT),
            ({**posted, "ksao_requirements": "nope"}, TENANT),
            ({**posted, "ksao_requirements": ["bad"]}, TENANT),
            ({**posted, "task_ksao_links": []}, TENANT),
            ({**posted, "task_ksao_links": "nope"}, TENANT),
            ({**posted, "task_ksao_links": ["bad"]}, TENANT),
            ({**posted, "fja_profile": "nope"}, TENANT),
            ({**posted, "effective_from": "not-a-date"}, TENANT),
            ({**posted, "effective_from": 12}, TENANT),
            ({**posted, "effective_from": datetime(2026, 8, 1, tzinfo=timezone.utc)}, TENANT),
            ({**posted, "recorded_at": "not-a-time"}, TENANT),
            ({**posted, "recorded_at": 12}, TENANT),
            ({**posted, "recorded_at": "2026-08-18T05:00:00"}, TENANT),
            ({**posted, "tasks": [{**posted["tasks"][0], "source": "nope"}]}, TENANT),
            ({**posted, "analysis_record_id": "zzzz"}, TENANT),
            ({**posted, "recorded_at": datetime(2026, 8, 18, 5, 0)}, TENANT),
        )
        rebuilt = snapshot_from_document(
            {
                **posted,
                "analysis_record_id": ANALYSIS,
                "tenant_record_id": TENANT,
                "job_record_id": JOB,
                "effective_from": date(2026, 8, 1),
                "recorded_at": datetime(2026, 8, 18, 5, 0, tzinfo=timezone.utc),
            },
            tenant_record_id=TENANT,
        )
        self.assertEqual(rebuilt.job_record_id, JOB)
        for document, tenant in cases:
            with self.subTest(document=document), self.assertRaises(ValueError):
                snapshot_from_document(document, tenant_record_id=tenant)


class PersistUseCaseTests(unittest.TestCase):
    """Prove authorization, Idempotency-Key forwarding, and payload equality."""

    def test_persisted_clinical_psychologist_snapshot_equals_posted_payload(self) -> None:
        posted = clinical_psychologist_document()
        port = RecordingWritePort()

        view = persist_job_analysis_snapshot(
            principal=write_principal(),
            tenant_record_id=TENANT,
            document=posted,
            idempotency_key=IDEMPOTENCY_KEY,
            purpose_code="job_analysis_write",
            position_record_id=str(POSITION),
            criterion_blueprint_id=str(CRITERION),
            policy=write_policy(),
            write_port=port,
        )

        self.assertEqual(view.snapshot, posted)
        self.assertEqual(len(port.calls), 1)
        call = port.calls[0]
        self.assertEqual(call["idempotency_key"], IDEMPOTENCY_KEY)
        self.assertEqual(call["position_record_id"], POSITION)
        self.assertEqual(call["criterion_blueprint_id"], CRITERION)

        uuid_port = RecordingWritePort()
        persist_job_analysis_snapshot(
            principal=write_principal(),
            tenant_record_id=TENANT,
            document=posted,
            idempotency_key=IDEMPOTENCY_KEY,
            purpose_code="job_analysis_write",
            position_record_id=POSITION,
            criterion_blueprint_id=CRITERION,
            policy=write_policy(),
            write_port=uuid_port,
        )
        self.assertEqual(uuid_port.calls[0]["position_record_id"], POSITION)
        self.assertEqual(
            call["request_digest"],
            command_digest(
                snapshot=clinical_psychologist_snapshot(),
                position_record_id=POSITION,
                criterion_blueprint_id=CRITERION,
            ),
        )
        audit_event = call["audit_event"]
        self.assertIsInstance(audit_event, AuditOutboxEvent)
        self.assertEqual(audit_event.event_type, "orgmetra.job_architecture.snapshot_recorded")
        self.assertFalse(audit_event.high_impact)

    def test_authorization_denial_never_reaches_write_port(self) -> None:
        port = RecordingWritePort()
        with self.assertRaises(AuthorizationDeniedError):
            persist_job_analysis_snapshot(
                principal=write_principal(),
                tenant_record_id=TENANT,
                document=clinical_psychologist_document(),
                idempotency_key=IDEMPOTENCY_KEY,
                purpose_code="wrong_purpose",
                policy=write_policy(),
                write_port=port,
            )
        self.assertEqual(port.calls, [])

    def test_integrity_mismatch_from_write_port_fails_closed(self) -> None:
        other = clinical_psychologist_snapshot()
        drifted = JobAnalysisSnapshot(
            analysis_record_id=other.analysis_record_id,
            tenant_record_id=other.tenant_record_id,
            job_record_id=other.job_record_id,
            analysis_version_code="clinical-psychologist:v2",
            status_code=other.status_code,
            effective_from=other.effective_from,
            recorded_at=other.recorded_at,
            tasks=other.tasks,
            ksao_requirements=other.ksao_requirements,
            task_ksao_links=other.task_ksao_links,
            fja_profile=other.fja_profile,
            reviewed_by_reference=other.reviewed_by_reference,
            reviewed_at=other.reviewed_at,
        )
        port = RecordingWritePort(result=drifted)
        with self.assertRaisesRegex(JobAnalysisIntegrityError, "escaped posted payload"):
            persist_job_analysis_snapshot(
                principal=write_principal(),
                tenant_record_id=TENANT,
                document=clinical_psychologist_document(),
                idempotency_key=IDEMPOTENCY_KEY,
                purpose_code="job_analysis_write",
                policy=write_policy(),
                write_port=port,
            )

    def test_rejects_executable_idempotency_text_before_sequence_hooks(self) -> None:
        """Reject a str subtype before caller-defined length or iteration can execute."""
        port = RecordingWritePort()

        with self.assertRaisesRegex(ValueError, "idempotency_key"):
            persist_job_analysis_snapshot(
                principal=write_principal(),
                tenant_record_id=TENANT,
                document=clinical_psychologist_document(),
                idempotency_key=_ExecutableIdempotencyKey(IDEMPOTENCY_KEY),
                purpose_code="job_analysis_write",
                policy=write_policy(),
                write_port=port,
            )

        self.assertEqual(port.calls, [])

    def test_rejects_reserved_tenant_and_short_idempotency_key(self) -> None:
        port = RecordingWritePort()
        with self.assertRaises(ValueError):
            persist_job_analysis_snapshot(
                principal=write_principal(),
                tenant_record_id=UUID(int=0),
                document=clinical_psychologist_document(),
                idempotency_key=IDEMPOTENCY_KEY,
                purpose_code="job_analysis_write",
                policy=write_policy(),
                write_port=port,
            )
        with self.assertRaises(ValueError):
            persist_job_analysis_snapshot(
                principal=write_principal(),
                tenant_record_id=TENANT,
                document=clinical_psychologist_document(),
                idempotency_key="short-key",
                purpose_code="job_analysis_write",
                policy=write_policy(),
                write_port=port,
            )
        with self.assertRaises(ValueError):
            persist_job_analysis_snapshot(
                principal=write_principal(),
                tenant_record_id=TENANT,
                document=clinical_psychologist_document(),
                idempotency_key="bad\x1fidempotency-key01",
                purpose_code="job_analysis_write",
                policy=write_policy(),
                write_port=port,
            )
        self.assertEqual(port.calls, [])


class ReadUseCaseTests(unittest.TestCase):
    """Prove authorized reads return the exact persisted snapshot document."""

    def test_read_returns_posted_clinical_psychologist_snapshot(self) -> None:
        port = RecordingReadPort(clinical_psychologist_snapshot())
        view = read_job_analysis_snapshot(
            principal=read_principal(),
            tenant_record_id=TENANT,
            analysis_record_id=ANALYSIS,
            purpose_code="job_analysis_read",
            policy=read_policy(),
            read_port=port,
        )
        self.assertEqual(view.snapshot, clinical_psychologist_document())
        self.assertEqual(port.calls, [(TENANT, ANALYSIS)])

    def test_missing_snapshot_is_reported_without_persistence_details(self) -> None:
        port = RecordingReadPort(None)
        with self.assertRaisesRegex(JobAnalysisSnapshotNotFound, "unavailable"):
            read_job_analysis_snapshot(
                principal=read_principal(),
                tenant_record_id=TENANT,
                analysis_record_id=ANALYSIS,
                purpose_code="job_analysis_read",
                policy=read_policy(),
                read_port=port,
            )

    def test_repository_target_mismatch_fails_closed(self) -> None:
        drifted = clinical_psychologist_snapshot()
        object.__setattr__(drifted, "tenant_record_id", OTHER_TENANT)
        port = RecordingReadPort(drifted)
        with self.assertRaisesRegex(JobAnalysisIntegrityError, "does not match authorized target"):
            read_job_analysis_snapshot(
                principal=read_principal(),
                tenant_record_id=TENANT,
                analysis_record_id=ANALYSIS,
                purpose_code="job_analysis_read",
                policy=read_policy(),
                read_port=port,
            )
        wrong_id = clinical_psychologist_snapshot()
        object.__setattr__(wrong_id, "analysis_record_id", JOB)
        port = RecordingReadPort(wrong_id)
        with self.assertRaisesRegex(JobAnalysisIntegrityError, "does not match authorized target"):
            read_job_analysis_snapshot(
                principal=read_principal(),
                tenant_record_id=TENANT,
                analysis_record_id=ANALYSIS,
                purpose_code="job_analysis_read",
                policy=read_policy(),
                read_port=port,
            )

    def test_invalid_read_identity_fails_before_repository_access(self) -> None:
        port = RecordingReadPort(clinical_psychologist_snapshot())
        with self.assertRaises(ValueError):
            read_job_analysis_snapshot(
                principal=read_principal(),
                tenant_record_id=UUID(int=0),
                analysis_record_id=ANALYSIS,
                purpose_code="job_analysis_read",
                policy=read_policy(),
                read_port=port,
            )
        self.assertEqual(port.calls, [])


if __name__ == "__main__":
    unittest.main()
