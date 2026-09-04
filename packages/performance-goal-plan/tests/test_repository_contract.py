"""Repository-level quality contract for the performance goal-plan lane."""

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
QUALITY_WORKFLOW = REPOSITORY_ROOT / ".github/workflows/performance-goal-plan-quality.yml"
GOVERNED_ADR_PATH = "docs/adr/0092-governed-performance-goal-plan.md"


def test_quality_workflow_covers_governed_adr() -> None:
    """Require ADR-only edits to trigger the dedicated exact-head quality gate."""
    workflow_text = QUALITY_WORKFLOW.read_text(encoding="utf-8")
    assert f'- "{GOVERNED_ADR_PATH}"' in workflow_text
