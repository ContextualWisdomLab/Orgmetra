"""Regression contracts for Enterprise Architecture projection CI admission."""

from pathlib import Path


def _workflow() -> str:
    """Read the repository-local EA projection workflow as UTF-8 text."""
    return Path(".github/workflows/enterprise-architecture-projection-quality.yml").read_text(
        encoding="utf-8"
    )


def test_ea_projection_quality_uses_explicit_available_runner_image() -> None:
    """Avoid the ubuntu-latest selector that is currently failing runner admission."""
    workflow = _workflow()
    assert "    runs-on: ubuntu-24.04\n" in workflow
    assert "    runs-on: ubuntu-latest\n" not in workflow
