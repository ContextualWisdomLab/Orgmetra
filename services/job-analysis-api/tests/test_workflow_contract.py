"""Regression contracts for job-analysis quality-gate dispatch boundaries."""

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _workflow(path: str) -> str:
    """Read one reviewed repository-local workflow as UTF-8 text."""
    return (REPOSITORY_ROOT / path).read_text(encoding="utf-8")


def test_foundation_ci_runs_job_analysis_on_default_branch_pull_requests() -> None:
    """Keep Job Analysis coverage in the single repository quality workflow."""
    workflow = _workflow(".github/workflows/foundation-ci.yml")
    assert "      - develop\n" in workflow
    assert "services/job-analysis-api/pyproject.toml services/job-analysis-api/tests" in workflow


def test_foundation_ci_includes_job_analysis_postgres_contract() -> None:
    """Keep snapshot persistence in the isolated PostgreSQL contract sequence."""
    workflow = _workflow(".github/workflows/foundation-ci.yml")
    assert "test_job_analysis_snapshot_postgres.sh" in workflow
    assert "test_job_analysis_snapshot_schema_hardening.sh" in workflow
    assert workflow.index('DATABASE_URL="$database_url" bash "tests/$contract"') < workflow.index(
        'DATABASE_URL="$database_url" bash tests/test_job_analysis_snapshot_schema_hardening.sh'
    )
    assert "      - develop\n" in workflow
