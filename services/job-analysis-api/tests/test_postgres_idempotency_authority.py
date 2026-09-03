"""Authority-binding regressions for job-analysis idempotency replays."""

from __future__ import annotations

from dataclasses import replace
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


_UNSET = object()


class _AlwaysEqualText(str):
    """Model a non-canonical DB-returned text value that lies during comparison."""

    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False


class PostgresIdempotencyAuthorityTests(unittest.TestCase):
    """Prove a durable idempotency key cannot cross command or authority identity."""

    def _persist_replay(
        self,
        *,
        stored_actor_reference: object,
        stored_purpose_code: object,
        stored_analysis_record_id: object = ANALYSIS,
        stored_request_digest: object = _UNSET,
        include_stored_authority: bool = True,
        actor_reference: str = "keyverse:actor-ja-1",
        purpose_code: str = "job_analysis_write",
        include_snapshot: bool = False,
        stored_snapshot_header: tuple[object, ...] | None = None,
    ) -> object:
        snapshot = clinical_psychologist_snapshot()
        digest = command_digest(
            snapshot=snapshot,
            position_record_id=None,
            criterion_blueprint_id=None,
        )
        durable_digest = digest if stored_request_digest is _UNSET else stored_request_digest
        durable_row: tuple[object, ...]
        if include_stored_authority:
            durable_row = (
                durable_digest,
                stored_analysis_record_id,
                stored_actor_reference,
                stored_purpose_code,
            )
        else:
            durable_row = (durable_digest, stored_analysis_record_id)
        script: list[object] = [None, durable_row]
        if include_snapshot:
            script.extend(
                [
                    [stored_snapshot_header if stored_snapshot_header is not None else _header_row()],
                    _task_rows(),
                    _ksao_rows(),
                    _link_rows(),
                ]
            )
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

    def test_authorityless_durable_row_fails_closed(self) -> None:
        """Reject a replay row that does not have the four columns selected by the SQL contract."""
        with self.assertRaisesRegex(JobAnalysisIntegrityError, "durable command row"):
            self._persist_replay(
                stored_actor_reference="keyverse:actor-ja-1",
                stored_purpose_code="job_analysis_write",
                include_stored_authority=False,
                include_snapshot=True,
            )

    def test_partial_null_durable_row_fails_closed(self) -> None:
        """Only the all-NULL LEFT JOIN projection can mean that no durable command exists."""
        with self.assertRaisesRegex(JobAnalysisIntegrityError, "partial-null"):
            self._persist_replay(
                stored_actor_reference="keyverse:actor-ja-1",
                stored_purpose_code="job_analysis_write",
                stored_request_digest=None,
            )

    def test_noncanonical_stored_digest_cannot_bypass_digest_binding(self) -> None:
        """Revalidate database-returned digest text before using equality for authority."""
        with self.assertRaisesRegex(JobAnalysisIntegrityError, "durable command"):
            self._persist_replay(
                stored_actor_reference="keyverse:actor-ja-1",
                stored_purpose_code="job_analysis_write",
                stored_request_digest=_AlwaysEqualText("f" * 64),
                include_snapshot=True,
            )

    def test_noncanonical_stored_actor_cannot_bypass_actor_binding(self) -> None:
        """Reject a driver-returned actor text subtype before comparing authority identity."""
        with self.assertRaisesRegex(JobAnalysisIntegrityError, "durable command"):
            self._persist_replay(
                stored_actor_reference=_AlwaysEqualText("keyverse:actor-ja-other"),
                stored_purpose_code="job_analysis_write",
                include_snapshot=True,
            )

    def test_noncanonical_stored_purpose_cannot_bypass_purpose_binding(self) -> None:
        """Reject a driver-returned purpose text subtype before comparing purpose authority."""
        with self.assertRaisesRegex(JobAnalysisIntegrityError, "durable command"):
            self._persist_replay(
                stored_actor_reference="keyverse:actor-ja-1",
                stored_purpose_code=_AlwaysEqualText("job_analysis_read"),
                include_snapshot=True,
            )

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

    def test_same_command_row_cannot_replay_different_snapshot_content(self) -> None:
        """Bind returned durable snapshot semantics back to the idempotency command digest."""
        requested_snapshot = clinical_psychologist_snapshot()
        altered_snapshot = replace(
            requested_snapshot,
            analysis_version_code="clinical-psychologist:v2",
        )
        altered_header = list(_header_row(digest=altered_snapshot.content_digest()))
        altered_header[3] = altered_snapshot.analysis_version_code

        with self.assertRaisesRegex(JobAnalysisIntegrityError, "recorded command digest"):
            self._persist_replay(
                stored_actor_reference="keyverse:actor-ja-1",
                stored_purpose_code="job_analysis_write",
                include_snapshot=True,
                stored_snapshot_header=tuple(altered_header),
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
