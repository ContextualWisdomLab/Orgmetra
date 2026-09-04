"""Regression contract for exact installed-wheel quality execution."""

from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOW_PATH = _REPOSITORY_ROOT / ".github/workflows/semantic-job-evidence-adapter-quality.yml"
_VENV_PATH = "/tmp/orgmetra-semantic-job-evidence-adapter-venv"


def test_quality_lane_executes_the_hash_bound_installed_wheel() -> None:
    """Require tests and reviewed test dependencies to execute inside an isolated venv."""
    workflow = _WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "PYTHONPATH: packages/semantic-job-evidence-adapter/src" not in workflow
    assert f"python -m venv {_VENV_PATH}" in workflow
    assert (
        f'{_VENV_PATH}/bin/python -m pip install --require-hashes --no-deps '
        f'--only-binary=:all: -r "$GITHUB_WORKSPACE/.github/requirements/foundation-test.txt"'
        in workflow
    )
    assert "wheel_sha=\"$(sha256sum \"$wheel_path\" | awk '{print $1}')\"" in workflow
    assert "for module in (coverage, pytest, pytest_cov):" in workflow
    assert (
        f"{_VENV_PATH}/bin/python -m pytest "
        '-c "$GITHUB_WORKSPACE/packages/semantic-job-evidence-adapter/pyproject.toml"'
        in workflow
    )
