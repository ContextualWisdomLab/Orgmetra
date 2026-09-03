"""Regression coverage for detached Job Analysis snapshots at the PostgreSQL boundary."""

from __future__ import annotations

from uuid import UUID

import pytest

from orgmetra_job_analysis_api.postgres import PostgresJobAnalysisPort
from orgmetra_job_analysis_api.snapshot import JobAnalysisIntegrityError, command_digest
from fixtures import IDEMPOTENCY_KEY, JOB, clinical_psychologist_snapshot
from test_postgres import FakeConnection, FakeCursor, _audit_event

_MUTATED_ANALYSIS = UUID("0198a412-6000-7000-8000-000000000499")


def test_write_port_detaches_snapshot_before_executable_database_acquisition() -> None:
    """Database hooks cannot retarget or rewrite already-authorized snapshot evidence."""
    snapshot = clinical_psychologist_snapshot()
    expected_snapshot = snapshot.to_snapshot()
    expected_analysis_id = snapshot.analysis_record_id
    expected_version = snapshot.analysis_version_code
    expected_task_statement = snapshot.tasks[0].task_statement
    write_statement_count = (
        1
        + len(snapshot.tasks)
        + len(snapshot.ksao_requirements)
        + len(snapshot.task_ksao_links)
        + 2
    )
    cursor = FakeCursor([None, None, (JOB,)] + [None] * write_statement_count)

    def connection_factory() -> FakeConnection:
        object.__setattr__(snapshot, "analysis_record_id", _MUTATED_ANALYSIS)
        object.__setattr__(snapshot, "analysis_version_code", "clinical-psychologist:mutated")
        object.__setattr__(snapshot.tasks[0], "task_statement", "Mutated task statement after authorization")
        return FakeConnection(cursor)

    persisted = PostgresJobAnalysisPort(connection_factory).persist_snapshot(
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
        outbox_delivery_record_id=UUID("0198a412-6000-7000-8000-000000000412"),
        write_command_id=UUID("0198a412-6000-7000-8000-000000000413"),
    )

    snapshot_insert = next(
        parameters
        for statement, parameters in cursor.executions
        if statement.startswith("INSERT INTO public.job_analysis_snapshot")
    )
    task_insert = next(
        parameters
        for statement, parameters in cursor.executions
        if statement.startswith("INSERT INTO public.job_analysis_task_item")
    )
    command_insert = next(
        parameters
        for statement, parameters in cursor.executions
        if statement.startswith("INSERT INTO public.job_analysis_write_command")
    )

    assert snapshot_insert[1] == expected_analysis_id
    assert snapshot_insert[5] == expected_version
    assert task_insert[1] == expected_analysis_id
    assert task_insert[3] == expected_task_statement
    assert command_insert[2] == expected_analysis_id
    assert persisted.to_snapshot() == expected_snapshot


def test_write_port_rejects_noncanonical_snapshot_before_database_acquisition() -> None:
    """A low-level-normalizable mutation must not silently change durable evidence."""
    snapshot = clinical_psychologist_snapshot()
    original_statement = snapshot.tasks[0].task_statement
    object.__setattr__(snapshot.tasks[0], "task_statement", f"  {original_statement}   ")

    def never_connect() -> object:
        raise AssertionError("database acquired before noncanonical snapshot rejection")

    with pytest.raises(
        JobAnalysisIntegrityError,
        match="detached snapshot does not match canonical evidence",
    ):
        PostgresJobAnalysisPort(never_connect).persist_snapshot(
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
            outbox_delivery_record_id=UUID("0198a412-6000-7000-8000-000000000412"),
            write_command_id=UUID("0198a412-6000-7000-8000-000000000413"),
        )
