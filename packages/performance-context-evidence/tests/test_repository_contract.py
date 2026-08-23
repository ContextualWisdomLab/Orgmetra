"""Repository-level quality contract for performance-context evidence."""

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "performance-context-evidence-quality.yml"


def test_quality_workflow_covers_governance_and_package_paths() -> None:
    """Material package, ADR, doctoring, and traceability edits must trigger the focused gate."""
    workflow = WORKFLOW.read_text(encoding="utf-8")
    required_paths = (
        '"packages/performance-context-evidence/**"',
        '"docs/adr/0093-governed-performance-context-evidence.md"',
        '"docs/doctoring/performance-context-evidence-references.md"',
        '"docs/traceability/performance-context-evidence.md"',
        '".github/workflows/performance-context-evidence-quality.yml"',
    )
    for required_path in required_paths:
        assert required_path in workflow


def test_package_has_beginner_readable_buyer_documentation() -> None:
    """The installed contract is accompanied by a concrete next-action explanation."""
    readme = (PACKAGE_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## Next action" in readme
    assert "do not automatically change an individual rating" in readme
    assert "multiple-membership" in readme
