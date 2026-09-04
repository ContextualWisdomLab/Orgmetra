"""Repository-level quality contract for performance-context evidence."""

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "performance-context-evidence-quality.yml"
BUILD_LOCK = REPOSITORY_ROOT / ".github" / "requirements" / "performance-context-evidence-build.txt"


def test_quality_workflow_covers_governance_and_package_paths() -> None:
    """Material package, build-lock, ADR, doctoring, and traceability edits trigger the gate."""
    workflow = WORKFLOW.read_text(encoding="utf-8")
    required_paths = (
        '"packages/performance-context-evidence/**"',
        '".github/requirements/performance-context-evidence-build.txt"',
        '"docs/adr/0093-governed-performance-context-evidence.md"',
        '"docs/doctoring/performance-context-evidence-references.md"',
        '"docs/traceability/performance-context-evidence.md"',
        '".github/workflows/performance-context-evidence-quality.yml"',
    )
    for required_path in required_paths:
        assert required_path in workflow


def test_quality_workflow_uses_reviewed_build_lock_and_exact_artifact_install() -> None:
    """Build tooling is reviewable and the no-deps wheel install makes no unused extras claim."""
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "-r .github/requirements/performance-context-evidence-build.txt" in workflow
    assert "setuptools==84.0.0" not in workflow
    assert "orgmetra-performance-context-evidence[test]" not in workflow
    assert BUILD_LOCK.read_text(encoding="utf-8") == (
        "setuptools==84.0.0 "
        "--hash=sha256:51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670\n"
    )


def test_package_has_beginner_readable_buyer_documentation() -> None:
    """The installed contract is accompanied by a concrete next-action explanation."""
    readme = (PACKAGE_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## Next action" in readme
    assert "do not automatically change an individual rating" in readme
    assert "multiple-membership" in readme
