"""Executable compatibility contract for the semantic evidence package support range."""

from pathlib import Path
import tomllib


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "semantic-job-evidence-adapter-quality.yml"


def test_declared_python_range_matches_the_hosted_compatibility_matrix() -> None:
    """Bound public Python support to the minor versions exercised by hosted CI."""
    pyproject = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["requires-python"] == ">=3.12,<3.15"

    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "matrix:" in workflow
    assert 'python-version: ["3.12", "3.13", "3.14"]' in workflow
    assert "python-version: ${{ matrix.python-version }}" in workflow
