"""Regression contracts for Orgmetra quality-gate dispatch boundaries."""

from pathlib import Path


def _workflow(path: str) -> str:
    """Read one reviewed repository-local workflow as UTF-8 text."""
    return Path(path).read_text(encoding="utf-8")


def test_people_api_quality_runs_on_current_default_branch_pull_requests() -> None:
    """Keep service coverage evidence alive when Orgmetra's default branch changes."""
    assert "      - develop\n" in _workflow(".github/workflows/people-api-quality.yml")


def test_foundation_ci_runs_on_current_default_branch_pull_requests() -> None:
    """Keep repository integrity evidence alive on the current integration branch."""
    assert "      - develop\n" in _workflow(".github/workflows/foundation-ci.yml")
