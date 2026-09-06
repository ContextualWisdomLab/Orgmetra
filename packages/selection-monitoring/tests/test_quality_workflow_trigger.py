"""Regression tests for canonical selection-monitoring Foundation ownership."""

from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_FOUNDATION_WORKFLOW = _REPOSITORY_ROOT / ".github/workflows/foundation-ci.yml"
_DEPENDENCY_HYGIENE = _REPOSITORY_ROOT / "tests/test_foundation_ci_dependency_hygiene.sh"
_ARTIFACT_CONTRACT = _REPOSITORY_ROOT / "tests/test_foundation_ci_selection_monitoring_artifact.sh"
_RETIRED_WORKFLOW = _REPOSITORY_ROOT / ".github/workflows/selection-monitoring-quality.yml"
_PYPROJECT = _REPOSITORY_ROOT / "packages/selection-monitoring/pyproject.toml"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_retired_selection_monitoring_workflow_stays_deleted() -> None:
    """Prevent protected workflow consolidation from being reversed by old ancestry."""
    assert not _RETIRED_WORKFLOW.exists()


def test_foundation_owns_selection_monitoring_quality_contract() -> None:
    """Require canonical Foundation CI to discover and execute the package contract."""
    foundation = _read(_FOUNDATION_WORKFLOW)
    hygiene = _read(_DEPENDENCY_HYGIENE)
    artifact = _read(_ARTIFACT_CONTRACT)
    pyproject = _read(_PYPROJECT)

    assert "bash tests/test_foundation_ci_dependency_hygiene.sh" in foundation
    assert '"${repository_root}"/tests/test_foundation_ci_*_artifact.sh' in hygiene
    assert 'bash "${artifact_contract}"' in hygiene
    assert 'retired_workflow="${repository_root}/.github/workflows/selection-monitoring-quality.yml"' in artifact
    assert 'PYTHONPATH="${package_root}/src"' in artifact
    assert '-c "${package_root}/pyproject.toml"' in artifact
    assert '"${package_root}/tests"' in artifact
    assert '"--cov-branch"' in pyproject
    assert '"--cov-fail-under=100"' in pyproject
