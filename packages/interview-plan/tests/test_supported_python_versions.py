"""Regression coverage for the package's declared Python compatibility contract."""

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_declared_python_floor_has_executable_compatibility_lanes() -> None:
    """Require every declared minor from 3.12 through the primary 3.14 lane in CI."""
    package_config = (REPOSITORY_ROOT / "packages/interview-plan/pyproject.toml").read_text()
    workflow = (REPOSITORY_ROOT / ".github/workflows/interview-plan-quality.yml").read_text()

    assert 'requires-python = ">=3.12"' in package_config
    assert "compatibility:" in workflow
    assert '"3.12"' in workflow
    assert '"3.13"' in workflow
    assert 'python-version: "3.14"' in workflow
    assert "python-version: ${{ matrix.python-version }}" in workflow
