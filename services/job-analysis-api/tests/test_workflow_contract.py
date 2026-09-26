"""Regression contracts for job-analysis quality-gate dispatch boundaries."""

from pathlib import Path


def _workflow(path: str) -> str:
    """Read one reviewed repository-local workflow as UTF-8 text."""
    return Path(path).read_text(encoding="utf-8")


def test_foundation_ci_delegates_job_analysis_to_discovered_service_runner() -> None:
    """Keep Job Analysis in the fail-closed discovered-service quality lane."""
    workflow = _workflow(".github/workflows/foundation-ci.yml")
    assert "      - develop\n" in workflow
    assert "Run discovered service contracts on primary runtime" in workflow
    assert "python scripts/foundation_service_compatibility.py --require-execution" in workflow


def test_foundation_ci_includes_job_analysis_postgres_contract() -> None:
    """Keep snapshot persistence in the isolated PostgreSQL contract sequence."""
    workflow = _workflow(".github/workflows/foundation-ci.yml")
    assert "test_job_analysis_snapshot_postgres.sh" in workflow
    assert "test_job_analysis_snapshot_schema_hardening.sh" in workflow
    assert workflow.index('DATABASE_URL="$database_url" bash "tests/$contract"') < workflow.index(
        'DATABASE_URL="$database_url" bash tests/test_job_analysis_snapshot_schema_hardening.sh'
    )
    assert "      - develop\n" in workflow
