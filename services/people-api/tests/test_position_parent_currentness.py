"""Regression contract for current-recorded Position parent anchors."""

from orgmetra_people_api.postgres_mutations import _POSITION_PARENTS_SQL


def test_position_parent_lookup_requires_current_recorded_parents_and_shared_lock() -> None:
    """A new Position must not attach to a closed Organization Unit or Job Profile."""
    assert "organization.recorded_to IS NULL" in _POSITION_PARENTS_SQL
    assert "job.recorded_to IS NULL" in _POSITION_PARENTS_SQL
    assert "FOR SHARE OF organization, job" in _POSITION_PARENTS_SQL
