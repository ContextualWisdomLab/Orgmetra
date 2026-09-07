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
    """A failed assertion after a real lock wait must close both client and server sessions."""
    acceptance = _load_acceptance_namespace()
    exercise = acceptance["_exercise_conflict"]
    original_lock_assertion = exercise.__globals__["_assert_database_lock_wait"]
    original_connection_factory = exercise.__globals__["_ConnectionFactory"]
    original_threading = exercise.__globals__["threading"]
    created_factories: list[object] = []
    join_timeouts: list[float | None] = []

    class _CapturingConnectionFactory(original_connection_factory):
        """Retain factories so the failure path can prove client handles were closed."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            created_factories.append(self)

    class _CapturingThread(original_threading.Thread):
        """Record whether cleanup joins can hang without an explicit deadline."""

        def join(self, timeout: float | None = None) -> None:
            join_timeouts.append(timeout)
            super().join(timeout=timeout)

    class _ThreadingProbe:
        Event = original_threading.Event
        Thread = _CapturingThread

    def fail_after_real_lock_observation(
        database_url: str, *, blocked_pid: int, blocker_pid: int
    ) -> None:
        original_lock_assertion(
            database_url,
            blocked_pid=blocked_pid,
            blocker_pid=blocker_pid,
        )
        raise AssertionError("forced failure after PostgreSQL lock observation")

    exercise.__globals__["_ConnectionFactory"] = _CapturingConnectionFactory
    exercise.__globals__["_assert_database_lock_wait"] = fail_after_real_lock_observation
    exercise.__globals__["threading"] = _ThreadingProbe
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

            assert join_timeouts == [30, 30], "concurrency writer cleanup joins must be deadline-bounded"
            assert len(created_factories) == 2
            assert all(
                connection.closed
                for factory in created_factories
                for connection in factory.connections
            )
            active_writers = acceptance["_psql"](
                database_url,
                "SELECT count(*) FROM pg_stat_activity "
                "WHERE application_name LIKE 'orgmetra-assignment-concurrency-writer-%';",
            )
            assert active_writers == "0"
    finally:
        exercise.__globals__["_ConnectionFactory"] = original_connection_factory
        exercise.__globals__["_assert_database_lock_wait"] = original_lock_assertion
        exercise.__globals__["threading"] = original_threading


def test_expired_cleanup_join_terminates_live_backend_before_returning() -> None:
    """A bounded join deadline must not return while an owned PostgreSQL backend is still live."""
    acceptance = _load_acceptance_namespace()
    exercise = acceptance["_exercise_conflict"]
    original_lock_assertion = exercise.__globals__["_assert_database_lock_wait"]
    original_connection_factory = exercise.__globals__["_ConnectionFactory"]
    original_connection_type = exercise.__globals__["_LibpqConnection"]
    original_connection_exit = original_connection_type.__exit__
    original_psql = exercise.__globals__["_psql"]
    original_threading = exercise.__globals__["threading"]
    created_factories: list[object] = []
    created_threads: list[object] = []
    termination_sql: list[str] = []
    hold_second_exit = original_threading.Event()
    second_waiting_to_close = original_threading.Event()

    class _CapturingConnectionFactory(original_connection_factory):
        """Retain writer factories so the timeout path can inspect owned backend identities."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            created_factories.append(self)

    class _ExpireFirstJoinThread(original_threading.Thread):
        """Make the first bounded join expire immediately, then allow a real cleanup join."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            self._join_calls = 0
            created_threads.append(self)

        def join(self, timeout: float | None = None) -> None:
            self._join_calls += 1
            if self._join_calls == 1:
                super().join(timeout=0)
                return
            super().join(timeout=timeout)

    class _ThreadingProbe:
        Event = original_threading.Event
        Thread = _ExpireFirstJoinThread

    def hold_second_connection_open(
        connection: object, exc_type: object, exc: object, traceback: object
    ) -> None:
        if connection._barrier is None:
            second_waiting_to_close.set()
            if not hold_second_exit.wait(timeout=30):
                raise AssertionError("timed out waiting for cleanup to terminate the blocked writer")
        original_connection_exit(connection, exc_type, exc, traceback)

    def observing_psql(database_url: str, sql: str) -> str:
        if "pg_terminate_backend" in sql:
            termination_sql.append(sql)
            hold_second_exit.set()
        return original_psql(database_url, sql)

    def fail_after_real_lock_observation(
        database_url: str, *, blocked_pid: int, blocker_pid: int
    ) -> None:
        original_lock_assertion(
            database_url,
            blocked_pid=blocked_pid,
            blocker_pid=blocker_pid,
        )
        raise AssertionError("forced failure after PostgreSQL lock observation")

    exercise.__globals__["_ConnectionFactory"] = _CapturingConnectionFactory
    exercise.__globals__["_assert_database_lock_wait"] = fail_after_real_lock_observation
    exercise.__globals__["_psql"] = observing_psql
    exercise.__globals__["threading"] = _ThreadingProbe
    original_connection_type.__exit__ = hold_second_connection_open
    try:
        isolated_postgres = acceptance["_isolated_postgres"]
        with isolated_postgres() as database_url:
            acceptance["_seed_fixture"](database_url, people=1, positions=2)
            first_command = acceptance["_assignment_command"](
                assignment_id=UUID("10000000-0000-7000-8003-000000000003"),
                employment_id=acceptance["_EMPLOYMENT_ONE"],
                person_id=acceptance["_PERSON_ONE"],
                position_id=acceptance["_POSITION_ONE"],
                allocation=Decimal("0.7500"),
                suffix=13,
            )
            second_command = acceptance["_assignment_command"](
                assignment_id=UUID("10000000-0000-7000-8003-000000000004"),
                employment_id=acceptance["_EMPLOYMENT_ONE"],
                person_id=acceptance["_PERSON_ONE"],
                position_id=acceptance["_POSITION_TWO"],
                allocation=Decimal("0.5000"),
                suffix=14,
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

            assert second_waiting_to_close.wait(timeout=5), "second writer never reached connection cleanup"
            assert termination_sql, "expired cleanup join did not terminate the live PostgreSQL backend"
            assert len(created_factories) == 2
            assert all(
                connection.closed
                for factory in created_factories
                for connection in factory.connections
            )
            active_writers = original_psql(
                database_url,
                "SELECT count(*) FROM pg_stat_activity "
                "WHERE application_name LIKE 'orgmetra-assignment-concurrency-writer-%';",
            )
            assert active_writers == "0"
    finally:
        hold_second_exit.set()
        for thread in created_threads:
            original_threading.Thread.join(thread, timeout=5)
        original_connection_type.__exit__ = original_connection_exit
        exercise.__globals__["_ConnectionFactory"] = original_connection_factory
        exercise.__globals__["_assert_database_lock_wait"] = original_lock_assertion
        exercise.__globals__["_psql"] = original_psql
        exercise.__globals__["threading"] = original_threading
