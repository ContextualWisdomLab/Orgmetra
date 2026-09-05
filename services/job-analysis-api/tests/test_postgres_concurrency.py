"""Concurrency regressions for PostgreSQL job-analysis persistence."""

from __future__ import annotations

from contextlib import AbstractContextManager
import unittest
from typing import Any
from uuid import UUID

from orgmetra_job_analysis_api.postgres import (
    PostgresJobAnalysisPort,
    _IDEMPOTENCY_LOOKUP_SQL,
    _is_unique_violation,
)
from orgmetra_job_analysis_api.snapshot import (
    JobAnalysisIdempotencyConflict,
    JobAnalysisIntegrityError,
    command_digest,
)
from test_postgres import _audit_event
from fixtures import IDEMPOTENCY_KEY, JOB, clinical_psychologist_snapshot


class _UniqueViolation(Exception):
    """Mimic a DB-API unique violation from psycopg-style drivers."""

    sqlstate = "23505"


class _ConstraintCursor:
    """Return valid parent lookups and fail at one selected insert constraint."""

    def __init__(self, failing_constraint: str) -> None:
        self.failing_constraint = failing_constraint
        self.executions: list[tuple[str, tuple[object, ...] | None]] = []
        self._last: object = None

    def __enter__(self) -> _ConstraintCursor:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def execute(self, sql: str, parameters: tuple[object, ...] | None = None) -> None:
        """Record SQL, return required parents, and inject one unique violation."""
        self.executions.append((sql, parameters))
        if sql.startswith("INSERT INTO public.job_analysis_snapshot"):
            if self.failing_constraint.startswith("job_analysis_snapshot_"):
                raise _UniqueViolation(self.failing_constraint)
            self._last = None
            return
        if sql.startswith("INSERT INTO public.job_analysis_write_command"):
            if self.failing_constraint.startswith("job_analysis_write_command_"):
                raise _UniqueViolation(self.failing_constraint)
            self._last = None
            return
        if "FROM public.job_analysis_write_command" in sql:
            self._last = (None, None, None, None)
        elif "FROM public.job_profile" in sql:
            self._last = (JOB,)
        else:
            self._last = None

    def fetchone(self) -> object:
        """Return the row prepared by the previous statement."""
        return self._last


class _DriverFailureCursor(_ConstraintCursor):
    """Raise a non-unique driver failure at one selected insert."""

    def __init__(self, target_prefix: str) -> None:
        super().__init__("no_unique_constraint")
        self.target_prefix = target_prefix

    def execute(self, sql: str, parameters: tuple[object, ...] | None = None) -> None:
        """Preserve unrelated driver failures instead of reclassifying them."""
        if sql.startswith(self.target_prefix):
            self.executions.append((sql, parameters))
            raise RuntimeError("unrelated driver failure")
        super().execute(sql, parameters)


class _Connection(AbstractContextManager[Any]):
    """Provide one deterministic transaction cursor."""

    def __init__(self, cursor: _ConstraintCursor) -> None:
        self.cursor_instance = cursor

    def __enter__(self) -> _Connection:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def cursor(self) -> _ConstraintCursor:
        """Return the configured cursor."""
        return self.cursor_instance


def _persist_with_cursor(cursor: _ConstraintCursor) -> None:
    """Run one realistic write until the configured cursor succeeds or fails."""
    snapshot = clinical_psychologist_snapshot()
    port = PostgresJobAnalysisPort(lambda: _Connection(cursor))
    port.persist_snapshot(
        snapshot=snapshot,
        idempotency_key=IDEMPOTENCY_KEY,
        request_digest=command_digest(
            snapshot=snapshot,
            position_record_id=None,
            criterion_blueprint_id=None,
        ),
        actor_reference="keyverse:actor-ja-1",
        purpose_code="job_analysis_write",
        position_record_id=None,
        criterion_blueprint_id=None,
        audit_event=_audit_event(),
        outbox_delivery_record_id=UUID("0198a412-6000-7000-8000-000000000302"),
        write_command_id=UUID("0198a412-6000-7000-8000-000000000303"),
    )


def _persist_with_constraint(constraint_name: str) -> None:
    """Run one realistic write until the selected unique constraint fires."""
    _persist_with_cursor(_ConstraintCursor(constraint_name))


class PostgresJobAnalysisConcurrencyTests(unittest.TestCase):
    """Prove exact-key serialization and stable constraint-domain mapping."""

    def test_idempotency_lookup_serializes_the_tenant_and_key_before_reading(self) -> None:
        """Prevent two transactions from both observing an absent command key."""
        normalized = " ".join(_IDEMPOTENCY_LOOKUP_SQL.lower().split())
        self.assertIn("pg_advisory_xact_lock", normalized)
        self.assertIn("hashtextextended", normalized)
        self.assertIn("tenant_record_id", normalized)
        self.assertIn("idempotency_key", normalized)

    def test_unique_violation_metadata_is_read_without_driver_lock_in(self) -> None:
        """Support modern and legacy PostgreSQL DB-API SQLSTATE attributes."""
        error = _UniqueViolation("job_analysis_snapshot_job_version_unique")
        self.assertTrue(_is_unique_violation(error))
        legacy = Exception("legacy")
        legacy.pgcode = "23505"  # type: ignore[attr-defined]
        self.assertTrue(_is_unique_violation(legacy))
        self.assertFalse(_is_unique_violation(RuntimeError("other")))

    def test_snapshot_version_race_maps_to_integrity_error(self) -> None:
        """Normalize a unique race without depending on optional driver diagnostics."""
        with self.assertRaisesRegex(
            JobAnalysisIntegrityError,
            r"^job-analysis snapshot identity or version already exists$",
        ):
            _persist_with_constraint("job_analysis_snapshot_job_version_unique")

    def test_command_key_race_maps_to_idempotency_conflict(self) -> None:
        """Normalize a command race without depending on optional driver diagnostics."""
        with self.assertRaisesRegex(
            JobAnalysisIdempotencyConflict,
            r"^idempotency or command identity was recorded concurrently$",
        ):
            _persist_with_constraint("job_analysis_write_command_idempotency_unique")

    def test_non_unique_snapshot_failure_is_not_reclassified(self) -> None:
        """Preserve an unrelated database failure for the outer fail-closed boundary."""
        with self.assertRaisesRegex(RuntimeError, "unrelated driver failure"):
            _persist_with_cursor(
                _DriverFailureCursor("INSERT INTO public.job_analysis_snapshot")
            )

    def test_non_unique_command_failure_is_not_reclassified(self) -> None:
        """Preserve an unrelated command-insert failure for operator diagnosis."""
        with self.assertRaisesRegex(RuntimeError, "unrelated driver failure"):
            _persist_with_cursor(
                _DriverFailureCursor("INSERT INTO public.job_analysis_write_command")
            )


if __name__ == "__main__":
    unittest.main()
