"""Repository-level quality contract for the Organization hierarchy-change review lane."""

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FOUNDATION_WORKFLOW = REPOSITORY_ROOT / ".github/workflows/foundation-ci.yml"
ROOT_CHANGELOG = REPOSITORY_ROOT / "CHANGELOG.md"
RETIRED_LEAF_WORKFLOW = (
    REPOSITORY_ROOT / ".github/workflows/organization-hierarchy-change-review-quality.yml"
)
_VENV_PATH = "/tmp/orgmetra-organization-hierarchy-change-review-venv"


def test_canonical_foundation_executes_installed_artifact_contract() -> None:
    """Keep the feature contract inside canonical Foundation CI after consolidation."""
    workflow = FOUNDATION_WORKFLOW.read_text(encoding="utf-8")

    assert not RETIRED_LEAF_WORKFLOW.exists()
    assert "Run Organization hierarchy change review installed-artifact contract" in workflow
    assert 'python-version: "3.14.7"' in workflow
    assert f"python -m venv {_VENV_PATH}" in workflow
    assert "wheel_sha=" in workflow
    assert 'sha256sum "$wheel_path"' in workflow
    assert f"{_VENV_PATH}/bin/python -m pytest" in workflow
    assert "packages/organization-hierarchy-change-review/pyproject.toml" in workflow


def test_root_changelog_records_active_package() -> None:
    """Keep repository release notes aligned with the active Organization review package."""
    changelog = ROOT_CHANGELOG.read_text(encoding="utf-8")

    assert "orgmetra_organization_hierarchy_change_review" in changelog
