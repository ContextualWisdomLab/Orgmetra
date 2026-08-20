"""Concurrency contracts for governed PostgreSQL People mutations.

These tests pin the database-locking boundary that prevents two distinct
idempotency keys from validating the same stale employment or position
snapshot and then committing mutually incompatible authoritative facts.
"""

from orgmetra_people_api import postgres_mutations


def test_employment_conflict_snapshot_is_serialized_per_converted_person() -> None:
    """Lock the current conversion before reading person employment history."""
    assert "ISOLATION LEVEL READ COMMITTED" in postgres_mutations._READ_WRITE_SQL
    assert "FOR UPDATE OF conversion" in postgres_mutations._CONVERSION_SQL


def test_assignment_capacity_snapshot_is_serialized_per_position() -> None:
    """Lock the position before reading the assignments used for capacity validation."""
    sql = postgres_mutations._NAMED_POSITION_VERSIONS_SQL
    assert "FROM public.position_record AS position" in sql
    assert "JOIN public.position_record_version AS version" in sql
    assert "FOR UPDATE OF position" in sql
