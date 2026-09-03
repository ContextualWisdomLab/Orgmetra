"""Authority-binding regressions for job-analysis idempotency replays."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_job_analysis_api.postgres import PostgresJobAnalysisPort, _IDEMPOTENCY_LOOKUP_SQL
from orgmetra_job_analysis_api.snapshot import (
    JobAnalysisIdempotencyConflict,
    JobAnalysisIntegrityError,
    command_digest,
)

from fixtures import ANALYSIS, IDEMPOTENCY_KEY, clinical_psychologist_snapshot
from test_postgres import (
    FakeConnection,
    FakeCursor,
    _audit_event,
    _header_row,
    _ksao_rows,
    _link_rows,
    _task_rows,
)


class PostgresIdempotencyAuthorityTests(unittest.TestCase):
    """Prove a durable idempotency key cannot cross command or authority identity."""

    def _persist_replay(
        self,
        *,
        stored_actor_reference: str,
        stored_purpose_code: str,
        stored_analysis_record_id: object = ANALYSIS,
        actor_reference: str = "keyverse:actor-ja-1",
        purpose_code: str = "job_analysis_write",
        include_snapshot: bool = False,
    ) -> object:
        snapshot = clinical_psychologist_snapshot()
        digest = command_digest(
            snapshot=snapshot,
            position_record_id=None,
            criterion_blueprint_id=None,
        )
        script: list[object] = [
            None,
            (
                digest,
                stored_analysis_record_id,
                stored_actor_reference,
                stored_purpose_code,
            ),
        ]
        if include_snapshot:
            script.extend([[_header_row()], _task_rows(), _ksao_rows(), _link_rows()])
        cursor = FakeCursor(script)
        port = PostgresJobAnalysisPort(lambda: FakeConnection(cursor))
        return port.persist_snapshot(
            snapshot=snapshot,
            idempotency_key=IDEMPOTENCY_KEY,
            request_digest=digest,
            actor_reference=actor_reference,
            purpose_code=purpose_code,
            position_record_id=None,
            criterion_blueprint_id=None,
            audit_event=_audit_event(),
            outbox_delivery_record_id=UUID("0198a412-6000-7000-8000-000000000302"),
            write_command_id=UUID("0198a412-6000-7000-8000-000000000303"),
        )

    def test_lookup_reads_the_immutable_actor_and_purpose_binding(self) -> None:
        """Keep replay authority in the same serialized command lookup."""
        normalized = " ".join(_IDEMPOTENCY_LOOKUP_SQL.lower().split())
        self.assertIn("actor_reference", normalized)
        self.assertIn("purpose_code", normalized)

    def test_same_key_and_digest_cannot_replay_under_a_different_actor(self) -> None:
        """Prevent one authorized principal from inheriting another actor's command."""
        with self.assertRaisesRegex(JobAnalysisIdempotencyConflict, "actor"):
            self._persist_replay(stored_actor_reference="keyverse:actor-ja-other", stored_purpose_code="job_analysis_write")

    def test_same_key_and_digest_cannot_replay_under_a_different_purpose(self) -> None:
        """Prevent an idempotent command from escaping its original purpose boundary."""
        with self.assertRaisesRegex(JobAnalysisIdempotencyConflict, "purpose"):
            self._persist_replay(stored_actor_reference="keyverse:actor-ja-1", stored_purpose_code="job_analysis_read")

    def test_same_digest_cannot_replay_a_different_snapshot_identity(self) -> None:
        """A durable digest cannot authorize replay of another persisted snapshot identity."""
        foreign_analysis_record_id = UUID("0198a412-6000-7000-8000-000000000399")
        with self.assertRaisesRegex(JobAnalysisIntegrityError, "analysis_record_id"):
            self._persist_replay(
                stored_actor_reference="keyverse:actor-ja-1",
                stored_purpose_code="job_analysis_write",
                stored_analysis_record_id=foreign_analysis_record_id,
            )

    def test_malformed_stored_snapshot_identity_fails_closed(self) -> None:
        """Corrupt durable replay identity is an integrity failure, not a load target."""
        with self.assertRaisesRegex(JobAnalysisIntegrityError, "invalid analysis_record_id"):
            self._persist_replay(
                stored_actor_reference="keyverse:actor-ja-1",
                stored_purpose_code="job_analysis_write",
                stored_analysis_record_id="0198a412-6000-7000-8000-000000000399",
            )

    def test_exact_actor_purpose_and_snapshot_replay_returns_the_stored_snapshot(self) -> None:
        """Preserve the successful retry contract for the exact original command authority."""
        replayed = self._persist_replay(
            stored_actor_reference="keyverse:actor-ja-1",
            stored_purpose_code="job_analysis_write",
            include_snapshot=True,
        )
        self.assertEqual(replayed.to_snapshot(), clinical_psychologist_snapshot().to_snapshot())


if __name__ == "__main__":
    unittest.main()
