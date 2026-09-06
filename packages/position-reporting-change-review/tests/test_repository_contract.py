"""Repository-level quality contract for the Position reporting-change review lane."""

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FOUNDATION_WORKFLOW = REPOSITORY_ROOT / ".github/workflows/foundation-ci.yml"
RETIRED_LEAF_WORKFLOW = (
    REPOSITORY_ROOT / ".github/workflows/position-reporting-change-review-quality.yml"
)
_VENV_PATH = "/tmp/orgmetra-position-reporting-change-review-venv"


def test_canonical_foundation_executes_installed_artifact_contract() -> None:
    """Keep exact installed-wheel quality in Foundation without recreating a leaf workflow."""
    workflow = FOUNDATION_WORKFLOW.read_text(encoding="utf-8")

    assert not RETIRED_LEAF_WORKFLOW.exists()
    assert "Run Position reporting change review installed-artifact contract" in workflow
    assert 'python-version: "3.14.7"' in workflow
    assert f"python -m venv {_VENV_PATH}" in workflow
    assert 'wheel_sha="$(sha256sum "$wheel_path" | awk \'{print $1}\')"' in workflow
    assert (
        f"{_VENV_PATH}/bin/python -m pytest "
        '-c "$GITHUB_WORKSPACE/packages/position-reporting-change-review/pyproject.toml"'
        in workflow
    )
