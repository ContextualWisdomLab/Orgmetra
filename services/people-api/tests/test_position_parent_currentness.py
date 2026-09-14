"""Regression contracts for current and business-effective Position parent anchors."""

from orgmetra_people_api.postgres_mutations import PostgresPeopleMutationPort, _POSITION_PARENTS_SQL
from test_people_mutations import JOB, ORGANIZATION, position_command
from test_postgres_people_mutations import FakeConnection, RECORDED_AT, ScriptedCursor, position_authorization


def test_position_parent_lookup_requires_current_effective_parents_and_shared_lock() -> None:
    """A new Position must attach only to current parent versions covering its effective date."""
    assert "JOIN public.organization_unit_version AS organization_version" in _POSITION_PARENTS_SQL
    assert "JOIN public.job_profile_version AS job_version" in _POSITION_PARENTS_SQL
    assert "organization.recorded_to IS NULL" in _POSITION_PARENTS_SQL
    assert "job.recorded_to IS NULL" in _POSITION_PARENTS_SQL
    assert "organization_version.recorded_to IS NULL" in _POSITION_PARENTS_SQL
    assert "job_version.recorded_to IS NULL" in _POSITION_PARENTS_SQL
    assert "organization_version.effective_from <= %s" in _POSITION_PARENTS_SQL
    assert "organization_version.effective_to IS NULL OR organization_version.effective_to > %s" in _POSITION_PARENTS_SQL
    assert "job_version.effective_from <= %s" in _POSITION_PARENTS_SQL
    assert "job_version.effective_to IS NULL OR job_version.effective_to > %s" in _POSITION_PARENTS_SQL
    assert "FOR SHARE OF organization, job, organization_version, job_version" in _POSITION_PARENTS_SQL


def test_position_parent_lookup_uses_requested_effective_date_for_both_parent_versions() -> None:
    """The parent-version lookup must evaluate both half-open intervals at the Position business date."""
    command = position_command()
    cursor = ScriptedCursor([[], [(ORGANIZATION, JOB, RECORDED_AT)]], [])
    connection = FakeConnection(cursor)
    port = PostgresPeopleMutationPort(lambda: connection)

    port.create_position(command=command, authorization=position_authorization())

    _sql, parameters = next(
        execution
        for execution in cursor.executions
        if "FROM public.organization_unit AS organization" in execution[0]
    )
    assert parameters == (
        command.job_profile_id,
        command.tenant_record_id,
        command.organization_unit_id,
        command.effective_from,
        command.effective_from,
        command.effective_from,
        command.effective_from,
    )
