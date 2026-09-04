"""Fail-closed regression for the idempotency lookup projection contract."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_job_analysis_api.postgres import PostgresJobAnalysisPort
from orgmetra_job_analysis_api.snapshot import JobAnalysisIntegrityError, command_digest

from fixtures import IDEMPOTENCY_KEY, clinical_psychologist_snapshot
from test_postgres import FakeConnection, FakeCursor, _audit_event


class PostgresIdempotencyLookupProjectionTests(unittest.TestCase):
    """Require the advisory-lock LEFT JOIN to return its one-row projection."""

    def test_missing_lookup_projection_fails_before_scope_reads(self) -> None:
        """Treat DB-API ``None`` as impossible evidence, not as command absence."""
        snapshot = clinical_psychologist_snapshot()
        cursor = FakeCursor([None, None])
        port = PostgresJobAnalysisPort(lambda: FakeConnection(cursor))

        with self.assertRaisesRegex(JobAnalysisIntegrityError, "lookup.*projection"):
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

        self.assertFalse(
            any("FROM public.job_profile" in statement for statement, _ in cursor.executions)
        )


if __name__ == "__main__":
    unittest.main()
