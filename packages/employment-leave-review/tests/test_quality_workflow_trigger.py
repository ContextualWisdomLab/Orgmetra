"""Regression contract for consolidated Employment Leave Review quality execution."""

from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_FOUNDATION_WORKFLOW = _REPOSITORY_ROOT / ".github/workflows/foundation-ci.yml"
_FOUNDATION_HYGIENE = _REPOSITORY_ROOT / "tests/test_foundation_ci_dependency_hygiene.sh"
_ARTIFACT_CONTRACT = _REPOSITORY_ROOT / "tests/test_employment_leave_review_artifact.sh"
_RETIRED_LEAF_WORKFLOW = (
    _REPOSITORY_ROOT / ".github/workflows/employment-leave-review-quality.yml"
)
_VENV_PATH = "/tmp/orgmetra-employment-leave-review-venv"


def test_quality_contract_is_owned_by_canonical_foundation() -> None:
    """Keep Employment Leave Review artifact parity in the canonical Foundation lane."""
    workflow = _FOUNDATION_WORKFLOW.read_text(encoding="utf-8")
    hygiene = _FOUNDATION_HYGIENE.read_text(encoding="utf-8")
    artifact = _ARTIFACT_CONTRACT.read_text(encoding="utf-8")

    assert not _RETIRED_LEAF_WORKFLOW.exists()
    assert "Prove Foundation CI dependency hygiene" in workflow
    assert "test_employment_leave_review_artifact.sh" in hygiene
    assert "PYTHONPATH=packages/employment-leave-review/src" not in artifact
    assert "sys.version_info[:3] != (3, 14, 7)" in artifact
    assert f'python -m venv "${{venv_dir}}"' in artifact
    assert "--require-hashes --no-deps --only-binary=:all:" in artifact
    assert 'wheel_sha="$(sha256sum "${wheel_path}" | awk \'{print $1}\')"' in artifact
    assert "for module in (coverage, pytest, pytest_cov):" in artifact
    assert (
        '"${venv_dir}/bin/python" -m pytest' in artifact
        and '-c "${package_root}/pyproject.toml"' in artifact
    )
    assert _VENV_PATH in artifact


def test_quality_contract_is_independent_of_process_cwd(monkeypatch) -> None:
    """Resolve repository-owned quality scripts independently of the process cwd."""
    package_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(package_root)

    assert _FOUNDATION_WORKFLOW.is_file()
    assert _FOUNDATION_HYGIENE.is_file()
    assert _ARTIFACT_CONTRACT.is_file()
    assert not _RETIRED_LEAF_WORKFLOW.exists()
