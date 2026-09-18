"""Regression tests for validity-analysis coverage by consolidated Foundation CI."""

from pathlib import Path


_WORKFLOW_PATH = Path(".github/workflows/foundation-ci.yml")


def test_foundation_ci_retriggers_without_path_filter() -> None:
    """Keep shared repository changes inside the consolidated validity gate surface."""
    workflow = _WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "pull_request:" in workflow
    assert "      - develop" in workflow
    assert "\n    paths:" not in workflow
    assert "\n    paths-ignore:" not in workflow
