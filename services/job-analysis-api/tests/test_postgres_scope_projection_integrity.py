"""Regression coverage for scope-query target identity at the durable port."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_job_analysis_api.postgres import PostgresJobAnalysisPort
from orgmetra_job_analysis_api.snapshot import JobAnalysisIntegrityError, command_digest
from fixtures import CRITERION, IDEMPOTENCY_KEY, JOB, POSITION, clinical_psychologist_snapshot
from test_postgres import FakeConnection, FakeCursor, _audit_event


_WRONG_JOB = UUID("0198a412-6000-7000-8000-000000000491")
_WRONG_POSITION = UUID("0198a412-6000-7000-8000-000000000492")
_WRONG_CRITERION = UUID("0198a412-6000-7000-8000-000000000493")


class _EqualityForgedUUID(UUID):
    """Model a DB-API UUID subtype that can forge equality at a trust boundary."""

    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False


_FORGED_JOB = _EqualityForgedUUID(str(_WRONG_JOB))
_FORGED_POSITION = _EqualityForgedUUID(str(_WRONG_POSITION))
_FORGED_CRITERION = _EqualityForgedUUID(str(_WRONG_CRITERION))


class PostgresScopeProjectionIntegrityTests(unittest.TestCase):
    """Require scope rows to prove the exact Job, Position, and Criterion queried."""

    def _persist(
        self,
        cursor: FakeCursor,
        *,
        position_record_id: UUID | None = None,
        criterion_blueprint_id: UUID | None = None,
    ) -> None:
        snapshot = clinical_psychologist_snapshot()
        PostgresJobAnalysisPort(lambda: FakeConnection(cursor)).persist_snapshot(
            snapshot=snapshot,
            idempotency_key=IDEMPOTENCY_KEY,
            request_digest=command_digest(
                snapshot=snapshot,
                position_record_id=position_record_id,
                criterion_blueprint_id=criterion_blueprint_id,
            ),
            actor_reference="keyverse:actor-ja-1",
            purpose_code="job_analysis_write",
            position_record_id=position_record_id,
            criterion_blueprint_id=criterion_blueprint_id,
            audit_event=_audit_event(),
            outbox_delivery_record_id=UUID("0198a412-6000-7000-8000-000000000494"),
            write_command_id=UUID("0198a412-6000-7000-8000-000000000495"),
        )

    def _assert_no_write(self, cursor: FakeCursor) -> None:
        self.assertFalse(
            any(
                statement.startswith("INSERT INTO")
                or "record_audit_outbox_event" in statement
                for statement, _ in cursor.executions
            )
        )

    def test_job_scope_projection_must_name_requested_job(self) -> None:
        cursor = FakeCursor([None, None, (_WRONG_JOB,)])

        with self.assertRaisesRegex(JobAnalysisIntegrityError, "job_profile scope row"):
            self._persist(cursor)

        self._assert_no_write(cursor)

    def test_position_scope_projection_must_name_requested_position(self) -> None:
        cursor = FakeCursor([None, None, (JOB,), (_WRONG_POSITION, JOB)])

        with self.assertRaisesRegex(JobAnalysisIntegrityError, "position_record scope row"):
            self._persist(cursor, position_record_id=POSITION)

        self._assert_no_write(cursor)

    def test_criterion_scope_projection_must_name_requested_criterion(self) -> None:
        cursor = FakeCursor([None, None, (JOB,), (_WRONG_CRITERION, JOB)])

        with self.assertRaisesRegex(JobAnalysisIntegrityError, "criterion_blueprint scope row"):
            self._persist(cursor, criterion_blueprint_id=CRITERION)

        self._assert_no_write(cursor)

    def test_job_scope_projection_rejects_equality_forging_uuid_subtype(self) -> None:
        cursor = FakeCursor([None, None, (_FORGED_JOB,)])

        with self.assertRaisesRegex(JobAnalysisIntegrityError, "job_profile scope row"):
            self._persist(cursor)

        self._assert_no_write(cursor)

    def test_position_scope_projection_rejects_equality_forging_uuid_subtype(self) -> None:
        cursor = FakeCursor([None, None, (JOB,), (_FORGED_POSITION, JOB)])

        with self.assertRaisesRegex(JobAnalysisIntegrityError, "position_record scope row"):
            self._persist(cursor, position_record_id=POSITION)

        self._assert_no_write(cursor)

    def test_criterion_scope_projection_rejects_equality_forging_uuid_subtype(self) -> None:
        cursor = FakeCursor([None, None, (JOB,), (_FORGED_CRITERION, JOB)])

        with self.assertRaisesRegex(JobAnalysisIntegrityError, "criterion_blueprint scope row"):
            self._persist(cursor, criterion_blueprint_id=CRITERION)

        self._assert_no_write(cursor)

    def test_job_scope_projection_rejects_invalid_shape(self) -> None:
        for malformed_row in (object(), (), (JOB, JOB)):
            with self.subTest(malformed_row=malformed_row):
                cursor = FakeCursor([None, None, malformed_row])

                with self.assertRaisesRegex(
                    JobAnalysisIntegrityError,
                    "job_profile scope row has invalid shape",
                ):
                    self._persist(cursor)

                self._assert_no_write(cursor)

    def test_position_scope_projection_rejects_invalid_shape(self) -> None:
        for malformed_row in (object(), (POSITION,), (POSITION, JOB, JOB)):
            with self.subTest(malformed_row=malformed_row):
                cursor = FakeCursor([None, None, (JOB,), malformed_row])

                with self.assertRaisesRegex(
                    JobAnalysisIntegrityError,
                    "position_record scope row has invalid shape",
                ):
                    self._persist(cursor, position_record_id=POSITION)

                self._assert_no_write(cursor)

    def test_criterion_scope_projection_rejects_invalid_shape(self) -> None:
        for malformed_row in (object(), (CRITERION,), (CRITERION, JOB, JOB)):
            with self.subTest(malformed_row=malformed_row):
                cursor = FakeCursor([None, None, (JOB,), malformed_row])

                with self.assertRaisesRegex(
                    JobAnalysisIntegrityError,
                    "criterion_blueprint scope row has invalid shape",
                ):
                    self._persist(cursor, criterion_blueprint_id=CRITERION)

                self._assert_no_write(cursor)

    def test_job_scope_projection_rejects_non_sequence_iterable(self) -> None:
        cursor = FakeCursor([None, None, (value for value in (JOB,))])

        with self.assertRaisesRegex(
            JobAnalysisIntegrityError,
            "job_profile scope row has invalid shape",
        ):
            self._persist(cursor)

        self._assert_no_write(cursor)

    def test_position_scope_projection_rejects_non_sequence_iterable(self) -> None:
        cursor = FakeCursor([None, None, (JOB,), (value for value in (POSITION, JOB))])

        with self.assertRaisesRegex(
            JobAnalysisIntegrityError,
            "position_record scope row has invalid shape",
        ):
            self._persist(cursor, position_record_id=POSITION)

        self._assert_no_write(cursor)

    def test_criterion_scope_projection_rejects_non_sequence_iterable(self) -> None:
        cursor = FakeCursor([None, None, (JOB,), (value for value in (CRITERION, JOB))])

        with self.assertRaisesRegex(
            JobAnalysisIntegrityError,
            "criterion_blueprint scope row has invalid shape",
        ):
            self._persist(cursor, criterion_blueprint_id=CRITERION)

        self._assert_no_write(cursor)

    def test_position_scope_projection_rejects_forged_job_relationship_uuid(self) -> None:
        cursor = FakeCursor([None, None, (JOB,), (POSITION, _FORGED_JOB)])

        with self.assertRaisesRegex(
            JobAnalysisIntegrityError,
            "position_record.job_profile_id scope row",
        ):
            self._persist(cursor, position_record_id=POSITION)

        self._assert_no_write(cursor)

    def test_criterion_scope_projection_rejects_forged_job_relationship_uuid(self) -> None:
        cursor = FakeCursor([None, None, (JOB,), (CRITERION, _FORGED_JOB)])

        with self.assertRaisesRegex(
            JobAnalysisIntegrityError,
            "criterion_blueprint.job_profile_id scope row",
        ):
            self._persist(cursor, criterion_blueprint_id=CRITERION)

        self._assert_no_write(cursor)


if __name__ == "__main__":
    unittest.main()