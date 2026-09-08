"""Regression coverage for detached operational UUIDs at the PostgreSQL port."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_job_analysis_api.postgres import PostgresJobAnalysisPort
from orgmetra_job_analysis_api.snapshot import command_digest
from fixtures import (
    ANALYSIS,
    IDEMPOTENCY_KEY,
    JOB,
    OTHER_TENANT,
    TENANT,
    clinical_psychologist_snapshot,
)
from test_postgres import (
    FakeConnection,
    FakeCursor,
    _audit_event,
    _header_row,
    _ksao_rows,
    _link_rows,
    _task_rows,
)


class PostgresOperationalUUIDDetachmentTests(unittest.TestCase):
    """Require validated UUID values to be snapshotted before DB acquisition hooks run."""

    def test_read_port_uses_detached_uuid_values_after_connection_factory_mutates_aliases(self) -> None:
        """A caller alias cannot retarget tenant or analysis identity after validation."""
        tenant_record_id = UUID(str(TENANT))
        analysis_record_id = UUID(str(ANALYSIS))
        cursor = FakeCursor(
            [None, None, [_header_row()], _task_rows(), _ksao_rows(), _link_rows()]
        )

        def connection_factory() -> FakeConnection:
            object.__setattr__(tenant_record_id, "int", OTHER_TENANT.int)
            object.__setattr__(analysis_record_id, "int", JOB.int)
            return FakeConnection(cursor)

        resolved = PostgresJobAnalysisPort(connection_factory).read_snapshot(
            tenant_record_id=tenant_record_id,
            analysis_record_id=analysis_record_id,
        )

        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.analysis_record_id, ANALYSIS)
        self.assertEqual(cursor.executions[1][1], (str(TENANT),))
        self.assertEqual(cursor.executions[2][1], (TENANT, ANALYSIS))

    def test_write_port_uses_detached_command_ids_after_connection_factory_mutates_aliases(self) -> None:
        """Validated write/outbox identities cannot be rewritten before SQL insertion."""
        snapshot = clinical_psychologist_snapshot()
        write_command_id = UUID("0198a412-6000-7000-8000-000000000413")
        outbox_delivery_record_id = UUID("0198a412-6000-7000-8000-000000000412")
        expected_write_command_id = UUID(str(write_command_id))
        expected_outbox_delivery_record_id = UUID(str(outbox_delivery_record_id))
        mutated_write_command_id = UUID("0198a412-6000-7000-8000-000000000499")
        mutated_outbox_delivery_record_id = UUID("0198a412-6000-7000-8000-000000000498")
        write_statement_count = (
            1
            + len(snapshot.tasks)
            + len(snapshot.ksao_requirements)
            + len(snapshot.task_ksao_links)
            + 2
        )
        cursor = FakeCursor([None, None, (JOB,)] + [None] * write_statement_count)

        def connection_factory() -> FakeConnection:
            object.__setattr__(write_command_id, "int", mutated_write_command_id.int)
            object.__setattr__(
                outbox_delivery_record_id,
                "int",
                mutated_outbox_delivery_record_id.int,
            )
            return FakeConnection(cursor)

        PostgresJobAnalysisPort(connection_factory).persist_snapshot(
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
            outbox_delivery_record_id=outbox_delivery_record_id,
            write_command_id=write_command_id,
        )

        parameter_sets = [parameters for _, parameters in cursor.executions if parameters]
        self.assertTrue(
            any(expected_write_command_id in parameters for parameters in parameter_sets)
        )
        self.assertTrue(
            any(
                expected_outbox_delivery_record_id in parameters
                for parameters in parameter_sets
            )
        )
        self.assertFalse(
            any(mutated_write_command_id in parameters for parameters in parameter_sets)
        )
        self.assertFalse(
            any(
                mutated_outbox_delivery_record_id in parameters
                for parameters in parameter_sets
            )
        )


if __name__ == "__main__":
    unittest.main()
