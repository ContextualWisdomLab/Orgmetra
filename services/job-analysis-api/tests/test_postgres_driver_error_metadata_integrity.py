"""Runtime-integrity regressions for PostgreSQL driver SQLSTATE metadata."""

from __future__ import annotations

import unittest

from orgmetra_job_analysis_api.postgres import _is_unique_violation


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


class _LegacyUniqueViolation(Exception):
    """Mimic a legacy PostgreSQL DB-API error exposing only pgcode."""

    pgcode = "23505"


class PostgresDriverErrorMetadataIntegrityTests(unittest.TestCase):
    """Require inert built-in SQLSTATE evidence before unique classification."""

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

    def test_legacy_builtin_pgcode_remains_supported(self) -> None:
        """Retain DB-API compatibility when only inert legacy pgcode is available."""
        self.assertTrue(_is_unique_violation(_LegacyUniqueViolation("unique")))


if __name__ == "__main__":
    unittest.main()
