"""Regression contracts for job-analysis quality-gate dispatch boundaries."""

from pathlib import Path


def _workflow(path: str) -> str:
    """Read one reviewed repository-local workflow as UTF-8 text."""
    return Path(path).read_text(encoding="utf-8")


def test_job_analysis_api_quality_runs_on_current_default_branch_pull_requests() -> None:
    """Keep service coverage evidence alive when Orgmetra's default branch changes."""
    assert "      - develop\n" in _workflow(".github/workflows/job-analysis-api-quality.yml")


def test_job_analysis_quality_reruns_when_foundation_contract_changes() -> None:
    """Revalidate the service when its asserted foundation workflow changes."""
    workflow = _workflow(".github/workflows/job-analysis-api-quality.yml")
    assert '      - ".github/workflows/foundation-ci.yml"\n' in workflow


def test_foundation_ci_includes_job_analysis_postgres_contract() -> None:
    """Keep the snapshot persistence contract in the PostgreSQL integrity matrix."""
    workflow = _workflow(".github/workflows/foundation-ci.yml")
    assert "test_job_analysis_snapshot_postgres.sh" in workflow
    assert "      - develop\n" in workflow
