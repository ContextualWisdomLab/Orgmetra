"""Regression for validity-analysis execution in consolidated Foundation CI."""

from pathlib import Path


def test_foundation_ci_runs_validity_analysis_and_adr_changes() -> None:
    """Require the consolidated gate to execute this package for every develop PR."""
    repository_root = Path(__file__).resolve().parents[3]
    workflow = (repository_root / ".github" / "workflows" / "foundation-ci.yml").read_text(
        encoding="utf-8"
    )

    assert "pull_request:" in workflow
    assert "      - develop" in workflow
    assert "\n    paths:" not in workflow
    assert "\n    paths-ignore:" not in workflow
    assert "PYTHONPATH=packages/validity-analysis/src" in workflow
    assert "packages/validity-analysis/tests" in workflow
