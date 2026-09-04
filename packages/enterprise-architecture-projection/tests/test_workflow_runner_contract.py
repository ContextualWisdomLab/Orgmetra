"""Protect the EA projection workflow from floating hosted-runner aliases."""

from pathlib import Path


WORKFLOW_PATH = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "workflows"
    / "enterprise-architecture-projection-quality.yml"
)


def test_projection_quality_uses_explicit_supported_runner_image() -> None:
    """Keep this PR's new workflow off the floating hosted-runner alias."""
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "runs-on: ubuntu-latest" not in workflow
    assert "runs-on: ubuntu-24.04" in workflow
