"""Regression contract for current and business-effective Position parent anchors."""

from orgmetra_people_api.postgres_mutations import _POSITION_PARENTS_SQL


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
