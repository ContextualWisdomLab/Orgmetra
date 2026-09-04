"""Runtime-integrity regressions for PostgreSQL driver error metadata."""

from __future__ import annotations

import unittest

from orgmetra_job_analysis_api.postgres import _constraint_name, _is_unique_violation


class _ExecutableText(str):
    """Fail if driver-provided text participates in caller-defined equality."""

    def __eq__(self, other: object) -> bool:
        raise AssertionError("driver text equality must not execute")


class _FallbackProbe(Exception):
    """Expose modern SQLSTATE while making legacy fallback access observable."""

    sqlstate = "23505"

    @property
    def pgcode(self) -> str:
        raise AssertionError("legacy pgcode must not be read when sqlstate is present")


class _ExecutableStateError(Exception):
    """Carry a string subtype that must not be trusted as SQLSTATE evidence."""

    sqlstate = _ExecutableText("23505")


class _Diagnostic:
    """Carry one driver-provided constraint diagnostic.""

    def __init__(self, constraint_name: str) -> None:
        self.constraint_name = constraint_name


class _ExecutableConstraintError(Exception):
    """Carry a constraint-name subtype that must not escape normalization."""

    sqlstate = "23505"

    def __init__(self) -> None:
        super().__init__("unique violation")
        self.diag = _Diagnostic(_ExecutableText("job_analysis_snapshot_job_version_unique"))


class _LegacyUniqueViolation(Exception):
    """Mimic a legacy PostgreSQL DB-API error exposing only pgcode."""

    pgcode = "23505"


class PostgresDriverErrorMetadataIntegrityTests(unittest.TestCase):
    """Require inert built-in diagnostics before classification or interpolation."""

    def test_modern_sqlstate_does_not_touch_legacy_fallback(self) -> None:
        """Do not execute a legacy fallback accessor after modern SQLSTATE exists."""
        self.assertTrue(_is_unique_violation(_FallbackProbe("unique")))

    def test_sqlstate_subtype_is_not_compared_as_unique_violation_evidence(self) -> None:
        """Reject executable text before equality-based SQLSTATE classification."""
        self.assertFalse(_is_unique_violation(_ExecutableStateError("unique")))

    def test_constraint_name_requires_exact_builtin_text(self) -> None:
        """Keep executable diagnostic text out of normalized conflict messages."""
        self.assertIsNone(_constraint_name(_ExecutableConstraintError()))

    def test_legacy_builtin_pgcode_remains_supported(self) -> None:
        """Retain DB-API compatibility when only inert legacy pgcode is available."""
        self.assertTrue(_is_unique_violation(_LegacyUniqueViolation("unique")))


if __name__ == "__main__":
    unittest.main()
