"""Fail-closed regression for the idempotency lookup projection contract."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_job_analysis_api.postgres import PostgresJobAnalysisPort
from orgmetra_job_analysis_api.snapshot import JobAnalysisIntegrityError, command_digest

from fixtures import IDEMPOTENCY_KEY, clinical_psychologist_snapshot
from test_postgres import FakeConnection, FakeCursor, _audit_event


class _MissingProjectionCursor(FakeCursor):
    """Model a DB-API cursor violating the one-row LEFT JOIN projection contract."""

    def fetchone(self) -> object:
        """Return no row only for the idempotency projection under test."""
        if self.executions and "FROM idempotency_lock" in self.executions[-1][0]:
            return None
        return super().fetchone()


class _GeneratorProjectionCursor(FakeCursor):
    """Model an executable iterable where a fixed DB-API projection row is required."""

    def fetchone(self) -> object:
        """Return a four-value generator only for the idempotency projection."""
        if self.executions and "FROM idempotency_lock" in self.executions[-1][0]:
            return (value for value in (None, None, None, None))
        return super().fetchone()


class _ExecutableTupleProjection(tuple[object, ...]):
    """Expose whether fixed-row validation dispatches caller-controlled iteration."""

    iterated = False

    def __iter__(self):  # type: ignore[override]
        """Fail if validation executes this untrusted sequence hook."""
        type(self).iterated = True
        raise RuntimeError("projection iterator executed")


class _ExecutableTupleProjectionCursor(FakeCursor):
    """Return a tuple subclass whose iterator is executable boundary behavior."""

    def fetchone(self) -> object:
        """Return executable tuple storage only for the idempotency projection."""
        if self.executions and "FROM idempotency_lock" in self.executions[-1][0]:
            return _ExecutableTupleProjection((None, None, None, None))
        return super().fetchone()


class PostgresIdempotencyLookupProjectionTests(unittest.TestCase):
    """Require the advisory-lock LEFT JOIN to return its one-row projection."""

    def _persist(self, cursor: FakeCursor) -> None:
        """Execute one write attempt against the supplied projection cursor."""
        snapshot = clinical_psychologist_snapshot()
        port = PostgresJobAnalysisPort(lambda: FakeConnection(cursor))
        port.persist_snapshot(
            snapshot=snapshot,
            idempotency_key=IDEMPOTENCY_KEY,
            request_digest=command_digest(
                snapshot=snapshot,
                position_record_id=None,
                criterion_blueprint_id=None,
            ),
            actor_reference="keyverse:actor-ja-1",
            purpose_code="job_analysis_write",
            position_record_id=None,
            criterion_blueprint_id=None,
            audit_event=_audit_event(),
            outbox_delivery_record_id=UUID("0198a412-6000-7000-8000-000000000302"),
            write_command_id=UUID("0198a412-6000-7000-8000-000000000303"),
        )

    def test_missing_lookup_projection_fails_before_scope_reads(self) -> None:
        """Treat DB-API ``None`` as impossible evidence, not as command absence."""
        cursor = _MissingProjectionCursor([None, None])

        with self.assertRaisesRegex(JobAnalysisIntegrityError, "lookup.*projection"):
            self._persist(cursor)

        self.assertFalse(
            any("FROM public.job_profile" in statement for statement, _ in cursor.executions)
        )

    def test_generator_lookup_projection_fails_before_scope_reads(self) -> None:
        """Reject arbitrary iterables even when they yield the four selected values."""
        cursor = _GeneratorProjectionCursor([None, None])

        with self.assertRaisesRegex(JobAnalysisIntegrityError, "durable command.*shape"):
            self._persist(cursor)

        self.assertFalse(
            any("FROM public.job_profile" in statement for statement, _ in cursor.executions)
        )

    def test_executable_tuple_projection_is_rejected_without_iteration(self) -> None:
        """Reject tuple subclasses before their caller-controlled iterator can run."""
        _ExecutableTupleProjection.iterated = False
        cursor = _ExecutableTupleProjectionCursor([None, None])

        with self.assertRaisesRegex(JobAnalysisIntegrityError, "durable command.*shape"):
            self._persist(cursor)

        self.assertFalse(_ExecutableTupleProjection.iterated)
        self.assertFalse(
            any("FROM public.job_profile" in statement for statement, _ in cursor.executions)
        )


if __name__ == "__main__":
    unittest.main()
