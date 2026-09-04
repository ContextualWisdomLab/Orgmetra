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


class _AttributeTrapStateError(Exception):
    """Expose inert class metadata behind executable dynamic attribute access."""

    sqlstate = "23505"

    def __getattribute__(self, name: str) -> object:
        if name in {"sqlstate", "pgcode"}:
            raise AssertionError("driver metadata lookup must not execute __getattribute__")
        return super().__getattribute__(name)


class _ExecutableStatePropertyError(Exception):
    """Expose SQLSTATE only through a descriptor that must not execute."""

    @property
    def sqlstate(self) -> str:
        raise AssertionError("driver SQLSTATE descriptor must not execute")


class _Diagnostic:
    """Carry one driver-provided constraint diagnostic."""

    def __init__(self, constraint_name: str) -> None:
        self.constraint_name = constraint_name


class _ExecutableConstraintError(Exception):
    """Carry a constraint-name subtype that must not escape normalization."""

    sqlstate = "23505"

    def __init__(self) -> None:
        super().__init__("unique violation")
        self.diag = _Diagnostic(_ExecutableText("job_analysis_snapshot_job_version_unique"))


class _AttributeTrapDiagnostic:
    """Store inert diagnostic text behind executable dynamic attribute access."""

    def __init__(self) -> None:
        self.constraint_name = "job_analysis_snapshot_job_version_unique"

    def __getattribute__(self, name: str) -> object:
        if name == "constraint_name":
            raise AssertionError("constraint metadata lookup must not execute __getattribute__")
        return super().__getattribute__(name)


class _AttributeTrapConstraintError(Exception):
    """Store an inert diagnostic object behind executable dynamic access."""

    sqlstate = "23505"

    def __init__(self) -> None:
        super().__init__("unique violation")
        self.diag = _AttributeTrapDiagnostic()

    def __getattribute__(self, name: str) -> object:
        if name == "diag":
            raise AssertionError("driver diagnostic lookup must not execute __getattribute__")
        return super().__getattribute__(name)


class _ExecutableDiagPropertyError(Exception):
    """Expose diagnostics only through a descriptor that must not execute."""

    sqlstate = "23505"

    @property
    def diag(self) -> object:
        raise AssertionError("driver diagnostic descriptor must not execute")


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

    def test_sqlstate_lookup_does_not_execute_dynamic_attribute_access(self) -> None:
        """Read inert stored SQLSTATE without invoking a driver override."""
        self.assertTrue(_is_unique_violation(_AttributeTrapStateError("unique")))

    def test_sqlstate_descriptor_is_not_executed_for_classification(self) -> None:
        """Treat executable SQLSTATE descriptors as unavailable evidence."""
        self.assertFalse(_is_unique_violation(_ExecutableStatePropertyError("unique")))

    def test_constraint_name_requires_exact_builtin_text(self) -> None:
        """Keep executable diagnostic text out of normalized conflict messages."""
        self.assertIsNone(_constraint_name(_ExecutableConstraintError()))

    def test_constraint_lookup_does_not_execute_dynamic_attribute_access(self) -> None:
        """Recover inert stored diagnostics without invoking driver overrides."""
        self.assertEqual(
            _constraint_name(_AttributeTrapConstraintError()),
            "job_analysis_snapshot_job_version_unique",
        )

    def test_constraint_descriptor_is_not_executed(self) -> None:
        """Omit a diagnostic that exists only behind an executable descriptor."""
        self.assertIsNone(_constraint_name(_ExecutableDiagPropertyError("unique")))

    def test_legacy_builtin_pgcode_remains_supported(self) -> None:
        """Retain DB-API compatibility when only inert legacy pgcode is available."""
        self.assertTrue(_is_unique_violation(_LegacyUniqueViolation("unique")))


if __name__ == "__main__":
    unittest.main()
