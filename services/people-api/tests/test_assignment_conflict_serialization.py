"""Regression contract for serializable Assignment portfolio/capacity validation."""

from __future__ import annotations

from orgmetra_people_api.postgres_mutations import (
    _EXISTING_ASSIGNMENTS_SQL,
    _NAMED_EMPLOYMENT_VERSIONS_SQL,
    _NAMED_POSITION_VERSIONS_SQL,
)


def test_assignment_snapshot_locks_both_conflict_roots_before_reading_allocations() -> None:
    """Serialize writes sharing an employment or position before checking FTE totals."""
    assert "FOR UPDATE OF employment" in _NAMED_EMPLOYMENT_VERSIONS_SQL
    assert "FOR UPDATE OF position" in _NAMED_POSITION_VERSIONS_SQL
    assert "FROM public.assignment_record AS assignment" in _EXISTING_ASSIGNMENTS_SQL
