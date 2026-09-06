"""Regression contracts for Orgmetra quality-gate dispatch boundaries."""

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _workflow(path: str) -> str:
    """Read one reviewed repository-local workflow as UTF-8 text."""
    return (REPOSITORY_ROOT / path).read_text(encoding="utf-8")


def test_foundation_ci_runs_people_api_on_default_branch_pull_requests() -> None:
    """Keep People API coverage in the single repository quality workflow."""
    workflow = _workflow(".github/workflows/foundation-ci.yml")
    assert "      - develop\n" in workflow
    assert "services/people-api/pyproject.toml services/people-api/tests" in workflow
