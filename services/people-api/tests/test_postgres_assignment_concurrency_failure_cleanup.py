"""Failure-path acceptance for Assignment concurrency writer cleanup."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import runpy
from uuid import UUID


def _load_acceptance_namespace() -> dict[str, object]:
    """Load the sibling PostgreSQL concurrency harness without coupling test order."""
    source = Path(__file__).with_name("test_postgres_assignment_concurrency_acceptance.py")
    return runpy.run_path(str(source))


def test_post_lock_assertion_failure_cleans_writer_sessions_before_teardown() -> None:
    """A failed assertion after a real lock wait must not leave PostgreSQL writers alive."""
    acceptance = _load_acceptance_namespace()
    exercise = acceptance["_exercise_conflict"]
    original_lock_assertion = exercise.__globals__["_assert_database_lock_wait"]

    def fail_after_real_lock_observation(
        database_url: str, *, blocked_pid: int, blocker_pid: int
    ) -> None:
        original_lock_assertion(
            database_url,
            blocked_pid=blocked_pid,
            blocker_pid=blocker_pid,
        )
        raise AssertionError("forced failure after PostgreSQL lock observation")

    exercise.__globals__["_assert_database_lock_wait"] = fail_after_real_lock_observation
    try:
        isolated_postgres = acceptance["_isolated_postgres"]
        with isolated_postgres() as database_url:
            acceptance["_seed_fixture"](database_url, people=1, positions=2)
            first_command = acceptance["_assignment_command"](
                assignment_id=UUID("10000000-0000-7000-8003-000000000001"),
                employment_id=acceptance["_EMPLOYMENT_ONE"],
                person_id=acceptance["_PERSON_ONE"],
                position_id=acceptance["_POSITION_ONE"],
                allocation=Decimal("0.7500"),
                suffix=11,
            )
            second_command = acceptance["_assignment_command"](
                assignment_id=UUID("10000000-0000-7000-8003-000000000002"),
                employment_id=acceptance["_EMPLOYMENT_ONE"],
                person_id=acceptance["_PERSON_ONE"],
                position_id=acceptance["_POSITION_TWO"],
                allocation=Decimal("0.5000"),
                suffix=12,
            )

            try:
                exercise(
                    database_url,
                    first_command=first_command,
                    second_command=second_command,
                    expected_error="Visible allocations for one employment exceed 1.0000.",
                    employment_id=acceptance["_EMPLOYMENT_ONE"],
                )
            except AssertionError as error:
                assert str(error) == "forced failure after PostgreSQL lock observation"
            else:
                raise AssertionError("forced concurrency assertion failure was not propagated")

            active_writers = acceptance["_psql"](
                database_url,
                "SELECT count(*) FROM pg_stat_activity "
                "WHERE application_name LIKE 'orgmetra-assignment-concurrency-writer-%';",
            )
            assert active_writers == "0"
    finally:
        exercise.__globals__["_assert_database_lock_wait"] = original_lock_assertion
