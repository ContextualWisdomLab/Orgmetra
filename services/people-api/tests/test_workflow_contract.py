"""Regression contracts for the People API quality gate dispatch boundary."""

from pathlib import Path


def test_people_api_quality_runs_on_current_default_branch_pull_requests() -> None:
    """Keep service coverage evidence alive when Orgmetra's default branch changes."""
    workflow = Path(".github/workflows/people-api-quality.yml").read_text(encoding="utf-8")

    assert "      - develop\n" in workflow
