"""Executable contracts for the PostgreSQL job-analysis persistence adapter."""

from __future__ import annotations

from datetime import date
import unittest
from uuid import UUID

from orgmetra_hris_kernel import AuditOutboxEvent

from orgmetra_job_analysis_api.postgres import PostgresJobAnalysisPort
from orgmetra_job_analysis_api.snapshot import (
    JobAnalysisIdempotencyConflict,
    JobAnalysisIntegrityError,
    JobAnalysisScopeMissing,
    command_digest,
)
from fixtures import (
    ANALYSIS,
    CRITERION,
    IDEMPOTENCY_KEY,
    JOB,
    OTHER_TENANT,
    POSITION,
    RECORDED_AT,
    REVIEWED_AT,
    TENANT,
    clinical_psychologist_snapshot,
)


class FakeCursor:
    """Serve deterministic rows while recording parameterized SQL."""

    def __init__(self, script: list[object]) -> None:
        self.script = list(script)
        self.executions: list[tuple[str, tuple[object, ...] | None]] = []
        self._last: object = None

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def execute(self, sql: str, parameters: tuple[object, ...] | None = None) -> None:
        """Record each SQL statement and advance the scripted response."""
        self.executions.append((sql, parameters))
        self._last = self.script.pop(0) if self.script else None
        if self._last is None and "FROM idempotency_lock" in sql:
            self._last = (None, None, None, None)

    def fetchone(self) -> object:
        """Return the row prepared by the previous execute."""
        return self._last

    def fetchmany(self, size: int) -> list[object]:
        """Return at most ``size`` scripted rows, like a DB-API cursor."""
        return list(self._last or [])[:size]

    def fetchall(self) -> list[object]:
        """Return scripted child rows for tasks, KSAOs, or links."""
        return list(self._last or [])


class FakeConnection:
    """Provide one transaction-scoped cursor context for the adapter."""

    def __init__(self, cursor: FakeCursor) -> None:
        self.cursor_instance = cursor

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def cursor(self) -> FakeCursor:
        """Return the deterministic cursor used by this transaction."""
        return self.cursor_instance


def _audit_event() -> AuditOutboxEvent:
    """Build one non-high-impact audit envelope for write-port tests."""
    snapshot = clinical_psychologist_snapshot()
    return AuditOutboxEvent(
        event_id=UUID("0198a412-6000-7000-8000-000000000301"),
        tenant_record_id=TENANT,
        source_service="job_analysis_api",
        event_type="orgmetra.job_architecture.snapshot_recorded",
        resource_reference=f"job_analysis_snapshot:{ANALYSIS.hex}",
        actor_reference="keyverse:actor-ja-1",
        purpose_code="job_analysis_write",
        reason_code="snapshot_persisted",
        evidence_version_code=snapshot.analysis_version_code,
        result_code="recorded",
        occurred_at=RECORDED_AT,
        high_impact=False,
    )


def _header_row(*, tenant_record_id: UUID = TENANT, analysis_record_id: UUID = ANALYSIS, digest: str | None = None) -> tuple[object, ...]:
    """Return one persisted snapshot header in SELECT column order."""
    snapshot = clinical_psychologist_snapshot()
    source = snapshot.fja_profile.source
    return (
        tenant_record_id,
        analysis_record_id,
        JOB,
        snapshot.analysis_version_code,
        snapshot.status_code,
        date(2026, 8, 1),
        RECORDED_AT,
        snapshot.reviewed_by_reference,
        REVIEWED_AT,
        digest if digest is not None else snapshot.content_digest(),
        snapshot.fja_profile.data_function_code,
        snapshot.fja_profile.people_function_code,
        snapshot.fja_profile.things_function_code,
        source.source_uri,
        source.source_title,
        source.source_version_code,
        source.retrieved_at,
        source.content_digest_sha256,
        source.origin_code,
    )


def _task_rows() -> list[tuple[object, ...]]:
    """Return persisted task rows in SELECT column order."""
    rows = []
    for task in clinical_psychologist_snapshot().tasks:
        source = task.source
        rows.append(
            (
                task.task_record_id,
                task.task_statement,
                task.importance_level,
                task.difficulty_level,
                source.source_uri,
                source.source_title,
                source.source_version_code,
                source.retrieved_at,
                source.content_digest_sha256,
                source.origin_code,
            )
        )
    return rows


def _ksao_rows() -> list[tuple[object, ...]]:
    """Return persisted KSAO rows in SELECT column order."""
    rows = []
    for item in clinical_psychologist_snapshot().ksao_requirements:
        source = item.source
        rows.append(
            (
                item.ksao_record_id,
                item.category_code,
                item.requirement_statement,
                item.importance_level,
                item.proficiency_level,
                source.source_uri,
                source.source_title,
                source.source_version_code,
                source.retrieved_at,
                source.content_digest_sha256,
                source.origin_code,
            )
        )
    return rows


def _link_rows() -> list[tuple[object, ...]]:
    """Return persisted task-KSAO link rows in SELECT column order."""
    return [
        (link.task_record_id, link.ksao_record_id, link.relationship_strength, link.essential_for_task)
        for link in clinical_psychologist_snapshot().task_ksao_links
    ]


class PostgresJobAnalysisPortTests(unittest.TestCase):
    """Prove tenant RLS, fail-closed parents, idempotency, and outbox writes."""

    def _port(self, script: list[object]) -> tuple[PostgresJobAnalysisPort, FakeCursor]:
        cursor = FakeCursor(script)
        return PostgresJobAnalysisPort(lambda: FakeConnection(cursor)), cursor

    def _persist(self, port: PostgresJobAnalysisPort, **overrides: object) -> object:
        snapshot = clinical_psychologist_snapshot()
        values = {
            "snapshot": snapshot,
            "idempotency_key": IDEMPOTENCY_KEY,
            "request_digest": command_digest(
                snapshot=snapshot,
                position_record_id=None,
                criterion_blueprint_id=None,
            ),
            "actor_reference": "keyverse:actor-ja-1",
            "purpose_code": "job_analysis_write",
            "position_record_id": None,
            "criterion_blueprint_id": None,
            "audit_event": _audit_event(),
            "outbox_delivery_record_id": UUID("0198a412-6000-7000-8000-000000000302"),
            "write_command_id": UUID("0198a412-6000-7000-8000-000000000303"),
        }
        values.update(overrides)
        return port.persist_snapshot(**values)

    def test_persists_snapshot_with_idempotency_key_and_audit_outbox(self) -> None:
        snapshot = clinical_psychologist_snapshot()
        write_statement_count = (
            1
            + len(snapshot.tasks)
            + len(snapshot.ksao_requirements)
            + len(snapshot.task_ksao_links)
            + 2
        )
        port, cursor = self._port([None, None, (JOB,)] + [None] * write_statement_count)

        persisted = self._persist(port)

        self.assertEqual(persisted.to_snapshot(), snapshot.to_snapshot())
        sql = [statement for statement, _ in cursor.executions]
        self.assertTrue(any("job_analysis_write_command" in item and "INSERT" in item for item in sql))
        self.assertTrue(any("record_audit_outbox_event" in item for item in sql))
        self.assertTrue(any("job_analysis_task_item" in item for item in sql))
        self.assertTrue(any("job_analysis_ksao_item" in item for item in sql))
        idempotency_insert = next(
            parameters
            for statement, parameters in cursor.executions
            if statement.startswith("INSERT INTO public.job_analysis_write_command")
        )
        self.assertIn(IDEMPOTENCY_KEY, idempotency_insert)
        job_lookup = next(parameters for statement, parameters in cursor.executions if "FROM public.job_profile" in statement)
        self.assertEqual(job_lookup, (TENANT, JOB))

    def test_persists_when_optional_parents_exist(self) -> None:
        snapshot = clinical_psychologist_snapshot()
        script = [
            None,
            None,
            (JOB,),
            (POSITION, JOB),
            (CRITERION, JOB),
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ]
        port, cursor = self._port(script)
        persisted = self._persist(
            port,
            position_record_id=POSITION,
            criterion_blueprint_id=CRITERION,
            request_digest=command_digest(
                snapshot=snapshot,
                position_record_id=POSITION,
                criterion_blueprint_id=CRITERION,
            ),
        )
        self.assertEqual(persisted.to_snapshot(), snapshot.to_snapshot())
        self.assertTrue(any("record_audit_outbox_event" in sql for sql, _ in cursor.executions))

    def test_missing_or_mismatched_scope_fails_closed(self) -> None:
        cases = (
            ([None, None, None], None, None, "job_profile"),
            ([None, None, (JOB,), None], POSITION, None, "position_record"),
            ([None, None, (JOB,), (POSITION, OTHER_TENANT)], POSITION, None, "position_record"),
            ([None, None, (JOB,), (CRITERION, OTHER_TENANT)], None, CRITERION, "criterion_blueprint"),
            ([None, None, (JOB,), None], None, CRITERION, "criterion_blueprint"),
        )
        for script, position_id, criterion_id, expected in cases:
            with self.subTest(expected=expected, position_id=position_id):
                port, _ = self._port(script)
                with self.assertRaisesRegex(JobAnalysisScopeMissing, expected):
                    self._persist(
                        port,
                        position_record_id=position_id,
                        criterion_blueprint_id=criterion_id,
                        request_digest=command_digest(
                            snapshot=clinical_psychologist_snapshot(),
                            position_record_id=position_id,
                            criterion_blueprint_id=criterion_id,
                        ),
                    )

    def test_idempotent_replay_returns_stored_snapshot_without_new_write(self) -> None:
        snapshot = clinical_psychologist_snapshot()
        digest = command_digest(snapshot=snapshot, position_record_id=None, criterion_blueprint_id=None)
        script = [
            None,
            (digest, ANALYSIS, "keyverse:actor-ja-1", "job_analysis_write"),
            [_header_row()],
            _task_rows(),
            _ksao_rows(),
            _link_rows(),
        ]
        port, cursor = self._port(script)
        persisted = self._persist(port, request_digest=digest)
        self.assertEqual(persisted.to_snapshot(), snapshot.to_snapshot())
        self.assertFalse(any("record_audit_outbox_event" in sql for sql, _ in cursor.executions))

    def test_idempotency_conflict_and_lost_snapshot_fail_closed(self) -> None:
        snapshot = clinical_psychologist_snapshot()
        digest = command_digest(snapshot=snapshot, position_record_id=None, criterion_blueprint_id=None)
        port, _ = self._port(
            [None, ("f" * 64, ANALYSIS, "keyverse:actor-ja-1", "job_analysis_write")]
        )
        with self.assertRaises(JobAnalysisIdempotencyConflict):
            self._persist(port, request_digest=digest)
        port, _ = self._port(
            [None, (digest, ANALYSIS, "keyverse:actor-ja-1", "job_analysis_write"), []]
        )
        with self.assertRaisesRegex(JobAnalysisIntegrityError, "lost its snapshot"):
            self._persist(port, request_digest=digest)

    def test_read_reconstructs_exact_clinical_psychologist_snapshot(self) -> None:
        port, cursor = self._port(
            [
                None,
                None,
                [_header_row()],
                _task_rows(),
                _ksao_rows(),
                _link_rows(),
            ]
        )
        snapshot = port.read_snapshot(tenant_record_id=TENANT, analysis_record_id=ANALYSIS)
        self.assertEqual(snapshot.to_snapshot(), clinical_psychologist_snapshot().to_snapshot())
        self.assertEqual(cursor.executions[0], ("SET TRANSACTION READ ONLY", None))

    def test_read_fail_closed_paths(self) -> None:
        port, _ = self._port([None, None, []])
        self.assertIsNone(port.read_snapshot(tenant_record_id=TENANT, analysis_record_id=ANALYSIS))
        port, _ = self._port([None, None, [_header_row(), _header_row()]])
        with self.assertRaisesRegex(JobAnalysisIntegrityError, "multiple snapshot headers"):
            port.read_snapshot(tenant_record_id=TENANT, analysis_record_id=ANALYSIS)
        port, _ = self._port([None, None, [_header_row(tenant_record_id=OTHER_TENANT)]])
        with self.assertRaisesRegex(JobAnalysisIntegrityError, "escaped requested target"):
            port.read_snapshot(tenant_record_id=TENANT, analysis_record_id=ANALYSIS)
        port, _ = self._port(
            [
                None,
                None,
                [_header_row(digest="a" * 64)],
                _task_rows(),
                _ksao_rows(),
                _link_rows(),
            ]
        )
        with self.assertRaisesRegex(JobAnalysisIntegrityError, "digest"):
            port.read_snapshot(tenant_record_id=TENANT, analysis_record_id=ANALYSIS)

    def test_constructor_and_direct_argument_guards(self) -> None:
        with self.assertRaisesRegex(TypeError, "connection_factory"):
            PostgresJobAnalysisPort(None)  # type: ignore[arg-type]
        port, _ = self._port([])
        with self.assertRaises(TypeError):
            port.persist_snapshot(
                snapshot=object(),  # type: ignore[arg-type]
                idempotency_key=IDEMPOTENCY_KEY,
                request_digest="a" * 64,
                actor_reference="keyverse:actor-ja-1",
                purpose_code="job_analysis_write",
                position_record_id=None,
                criterion_blueprint_id=None,
                audit_event=_audit_event(),
                outbox_delivery_record_id=UUID("0198a412-6000-7000-8000-000000000302"),
                write_command_id=UUID("0198a412-6000-7000-8000-000000000303"),
            )
        with self.assertRaises(TypeError):
            self._persist(port, audit_event=object())
        with self.assertRaises(ValueError):
            self._persist(port, idempotency_key=12)
        with self.assertRaises(ValueError):
            port.read_snapshot(tenant_record_id=UUID(int=0), analysis_record_id=ANALYSIS)
        with self.assertRaises(ValueError):
            self._persist(port, position_record_id=UUID(int=0))
        with self.assertRaises(ValueError):
            self._persist(port, criterion_blueprint_id=UUID(int=(1 << 128) - 1))


if __name__ == "__main__":
    unittest.main()
