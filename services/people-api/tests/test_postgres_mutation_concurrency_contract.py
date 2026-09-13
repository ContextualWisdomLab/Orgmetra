"""Concurrency contracts for governed PostgreSQL People mutations.

These tests pin the database-locking boundaries that prevent distinct idempotency
keys from validating stale Employment or Position snapshots and then committing
mutually incompatible authoritative facts.
"""

from orgmetra_people_api import postgres_mutations


def test_employment_conflict_snapshot_is_serialized_per_person() -> None:
    """Lock the current Person before reading its Employment portfolio."""
    assert "ISOLATION LEVEL READ COMMITTED" in postgres_mutations._READ_WRITE_SQL
    assert "FROM public.person_record AS person" in postgres_mutations._PERSON_EMPLOYMENT_ANCHOR_SQL
    assert "FOR UPDATE OF person" in postgres_mutations._PERSON_EMPLOYMENT_ANCHOR_SQL


def test_assignment_employment_snapshot_is_serialized_on_employment_root() -> None:
    """Lock the named Employment before reading eligibility and allocation state."""
    sql = postgres_mutations._ASSIGNMENT_EMPLOYMENT_ANCHOR_SQL
    assert "FROM public.employment_record AS employment" in sql
    assert "FOR UPDATE OF employment" in sql


def test_assignment_capacity_snapshot_is_serialized_per_position() -> None:
    """Lock the Position before reading the assignments used for seat capacity validation."""
    sql = postgres_mutations._NAMED_POSITION_VERSIONS_SQL
    assert "FROM public.position_record AS position" in sql
    assert "JOIN public.position_record_version AS version" in sql
    assert "FOR UPDATE OF position" in sql
