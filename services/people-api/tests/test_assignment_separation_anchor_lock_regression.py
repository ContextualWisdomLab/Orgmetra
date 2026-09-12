"""Regression contract for Assignment versus Employment-separation serialization."""

from __future__ import annotations

from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
_MIGRATION = _REPO_ROOT / "database/migrations/0017_assignment_employment_separation_serialization.sql"


def test_assignment_insert_uses_employment_anchor_as_shared_conflict_boundary() -> None:
    """Keep the Assignment/Employment race guard at the authoritative PostgreSQL boundary."""
    sql = _MIGRATION.read_text(encoding="utf-8")

    assert "CREATE FUNCTION public.guard_assignment_employment_coverage()" in sql
    assert "FOR UPDATE OF employment" in sql
    assert "CREATE TRIGGER assignment_employment_coverage_guard" in sql
    assert "BEFORE INSERT ON public.assignment_record" in sql
    assert "version.recorded_to IS NULL" in sql
    assert "version.employment_status_code IN ('active', 'leave')" in sql
    assert "NEW.effective_to <= version.effective_to" in sql
