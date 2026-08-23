"""Repository-level quality contract for the Position reporting-change review lane."""

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
QUALITY_WORKFLOW = (
    REPOSITORY_ROOT / ".github/workflows/position-reporting-change-review-quality.yml"
)
GOVERNED_PATHS = (
    "docs/adr/0095-governed-position-reporting-change-review.md",
    "docs/doctoring/position-reporting-change-review-references.md",
    "docs/traceability/position-reporting-change-review.md",
)


def test_quality_workflow_covers_all_governed_docs() -> None:
    """Require governance-only edits to trigger the dedicated exact-head quality gate."""
    workflow_text = QUALITY_WORKFLOW.read_text(encoding="utf-8")
    for governed_path in GOVERNED_PATHS:
        assert f'- "{governed_path}"' in workflow_text
