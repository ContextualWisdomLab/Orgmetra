"""Regression tests for stacked HR data-export workflow coverage.

GitHub evaluates ``pull_request`` workflow branch filters from the pull request's
base branch. A child PR stacked on ``feat/governed-hr-data-export-control``
therefore receives no HR Data Export Quality run unless the workflow already on
that parent branch accepts the parent branch as a pull-request target.
"""

from pathlib import Path
import re


_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOW_PATH = _REPOSITORY_ROOT / ".github" / "workflows" / "hr-data-export-quality.yml"


def test_export_quality_runs_for_stacked_execution_child() -> None:
    """Require the parent branch to materialize the child PR's focused gate."""

    workflow = _WORKFLOW_PATH.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^\s{4}branches:\s*\n(?P<body>(?:\s{6}- .+\n)+)", workflow)
    assert match is not None, "HR Data Export Quality must declare pull_request branches"
    branch_lines = {
        line.strip().removeprefix("- ")
        for line in match.group("body").splitlines()
        if line.strip().startswith("- ")
    }
    assert "develop" in branch_lines
    assert "feat/governed-hr-data-export-control" in branch_lines, (
        "stacked export-execution PRs target feat/governed-hr-data-export-control; "
        "the parent-owned workflow must accept that base branch before child-head "
        "evidence can materialize"
    )
