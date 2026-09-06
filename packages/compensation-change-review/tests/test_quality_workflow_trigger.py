"""Regression tests for consolidated compensation-review quality admission."""

from pathlib import Path


_FOUNDATION_WORKFLOW = Path(".github/workflows/foundation-ci.yml")
_RETIRED_LEAF_WORKFLOW = Path(
    ".github/workflows/compensation-change-review-quality.yml"
)
_PACKAGE_TEST_COMMAND = (
    "PYTHONPATH=packages/compensation-change-review/src "
    "COVERAGE_FILE=/tmp/orgmetra-compensation-change-review.coverage "
    "python -m pytest -c packages/compensation-change-review/pyproject.toml "
    "packages/compensation-change-review/tests"
)


def test_foundation_runs_compensation_review_with_exact_package_coverage() -> None:
    """Keep compensation review inside the canonical one-job Foundation lane."""
    workflow = _FOUNDATION_WORKFLOW.read_text(encoding="utf-8")

    assert _PACKAGE_TEST_COMMAND in workflow


def test_leaf_quality_workflow_stays_retired() -> None:
    """Do not recreate a package-specific runner after repository consolidation."""
    assert not _RETIRED_LEAF_WORKFLOW.exists()
