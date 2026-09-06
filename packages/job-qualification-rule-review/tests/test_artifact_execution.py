"""Regression contract for consolidated exact installed-wheel quality execution."""

from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_FOUNDATION_WORKFLOW = _REPOSITORY_ROOT / ".github/workflows/foundation-ci.yml"
_RETIRED_LEAF_WORKFLOW = (
    _REPOSITORY_ROOT / ".github/workflows/job-qualification-rule-review-quality.yml"
)
_VENV_PATH = "/tmp/orgmetra-job-qualification-rule-review-venv"


def test_foundation_executes_the_hash_bound_installed_wheel() -> None:
    """Keep artifact parity inside the canonical one-job Foundation lane."""
    workflow = _FOUNDATION_WORKFLOW.read_text(encoding="utf-8")

    assert not _RETIRED_LEAF_WORKFLOW.exists()
    assert "Set up exact Job Qualification Rule Review Python" in workflow
    assert 'python-version: "3.14.7"' in workflow
    assert "Run Job qualification rule review installed-artifact contract" in workflow
    assert "PYTHONPATH=packages/job-qualification-rule-review/src" not in workflow
    assert f"python -m venv {_VENV_PATH}" in workflow
    assert (
        f'{_VENV_PATH}/bin/python -m pip install --require-hashes --no-deps '
        f'--only-binary=:all: -r "$GITHUB_WORKSPACE/.github/requirements/foundation-test.txt"'
        in workflow
    )
    assert 'wheel_sha="$(sha256sum "$wheel_path" | awk \'{print $1}\')"' in workflow
    assert "for module in (coverage, pytest, pytest_cov):" in workflow
    assert (
        f"{_VENV_PATH}/bin/python -m pytest "
        '-c "$GITHUB_WORKSPACE/packages/job-qualification-rule-review/pyproject.toml"'
        in workflow
    )
