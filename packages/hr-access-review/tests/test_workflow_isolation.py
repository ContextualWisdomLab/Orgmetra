"""Regression contract for hermetic installed-artifact quality execution."""

from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOW_PATH = _REPOSITORY_ROOT / ".github/workflows/hr-access-review-quality.yml"
_VENV_PATH = "/tmp/orgmetra-hr-access-review-venv"


def test_installed_artifact_tests_use_a_fully_isolated_venv() -> None:
    """Require reviewed test dependencies to live inside the tested wheel environment."""
    workflow = _WORKFLOW_PATH.read_text(encoding="utf-8")

    assert f"python -m venv --system-site-packages {_VENV_PATH}" not in workflow
    assert f"python -m venv {_VENV_PATH}" in workflow
    assert (
        f'{_VENV_PATH}/bin/python -m pip install --require-hashes --no-deps '
        f'--only-binary=:all: -r "$GITHUB_WORKSPACE/.github/requirements/foundation-test.txt"'
        in workflow
    )
    assert "for module in (coverage, pytest, pytest_cov):" in workflow
