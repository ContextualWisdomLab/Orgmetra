"""Regression contracts for current-recorded Assignment parent anchors."""

from orgmetra_people_api.postgres_mutations import (
    _ASSIGNMENT_EMPLOYMENT_ANCHOR_SQL,
    _NAMED_POSITION_VERSIONS_SQL,
)


def test_assignment_parent_roots_require_current_recorded_truth_and_lock() -> None:
    """A new Assignment must bind only current Employment and Position roots."""
    assert "employment.recorded_to IS NULL" in _ASSIGNMENT_EMPLOYMENT_ANCHOR_SQL
    assert "FOR UPDATE OF employment" in _ASSIGNMENT_EMPLOYMENT_ANCHOR_SQL
    assert "position.recorded_to IS NULL" in _NAMED_POSITION_VERSIONS_SQL
    assert "FOR UPDATE OF position" in _NAMED_POSITION_VERSIONS_SQL
