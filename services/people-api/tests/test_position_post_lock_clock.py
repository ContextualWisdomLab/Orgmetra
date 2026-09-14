"""Regression contract for Position recorded-time ordering."""

from orgmetra_people_api.mutations import create_position_record
from orgmetra_people_api.postgres_mutations import PostgresPeopleMutationPort
from test_people_mutations import ORGANIZATION, JOB, position_command, position_policy
from test_postgres_people_mutations import (
    PRINCIPAL,
    RECORDED_AT,
    FakeConnection,
    ScriptedCursor,
)

_POST_LOCK_CLOCK_SQL = "SELECT pg_catalog.clock_timestamp()"


def test_position_reads_database_clock_after_parent_lock_before_insert() -> None:
    """Position recorded_at must reflect time after current parent truth is locked."""
    cursor = ScriptedCursor([[], [(ORGANIZATION, JOB, RECORDED_AT)]], [])
    connection = FakeConnection(cursor)
    port = PostgresPeopleMutationPort(lambda: connection)

    create_position_record(
        principal=PRINCIPAL,
        command=position_command(),
        purpose_code="job_architecture_admin",
        policy=position_policy(),
        mutation_port=port,
    )

    sql = [statement for statement, _parameters in cursor.executions]
    parent_index = next(
        index for index, statement in enumerate(sql)
        if "FROM public.organization_unit AS organization" in statement
    )
    clock_index = sql.index(_POST_LOCK_CLOCK_SQL)
    insert_index = next(
        index for index, statement in enumerate(sql)
        if statement.startswith("INSERT INTO public.position_record (")
    )
    assert parent_index < clock_index < insert_index
