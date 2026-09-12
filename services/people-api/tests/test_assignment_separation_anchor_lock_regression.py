"""Regression contract for Assignment versus Employment-separation serialization."""

from __future__ import annotations

from orgmetra_people_api.postgres_mutations import PostgresPeopleMutationPort
from test_people_mutations import assignment_command
from test_postgres_people_mutations import (
    CONVERSION,
    RECORDED_AT,
    FakeConnection,
    ScriptedCursor,
    assignment_authorization,
    covering_employment_row,
    covering_position_row,
)


def test_assignment_locks_employment_anchor_before_reading_versions() -> None:
    """Acquire the separation-shared anchor lock in its own READ COMMITTED statement."""
    cursor = ScriptedCursor(
        [[], [(CONVERSION, RECORDED_AT)]],
        [[covering_employment_row()], [covering_position_row()], []],
    )
    connection = FakeConnection(cursor)
    port = PostgresPeopleMutationPort(lambda: connection)

    port.create_assignment(
        command=assignment_command(),
        authorization=assignment_authorization(),
    )

    statements = [sql for sql, _parameters in cursor.executions]
    lock_indexes = [
        index
        for index, sql in enumerate(statements)
        if "FROM public.employment_record AS employment" in sql
        and "FOR UPDATE OF employment" in sql
        and "employment_record_version" not in sql
    ]
    version_index = next(
        index
        for index, sql in enumerate(statements)
        if "JOIN public.employment_record_version AS version" in sql
        and "employment.employment_record_id = %s" in sql
    )

    assert len(lock_indexes) == 1
    assert lock_indexes[0] < version_index
