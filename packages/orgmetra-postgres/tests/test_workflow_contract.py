"""Static security contracts for the PostgreSQL quality workflow."""

from __future__ import annotations

import re
from pathlib import Path


WORKFLOW_PATH = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "workflows"
    / "postgres-quality.yml"
)


def _workflow_text() -> str:
    """Return the exact workflow source under test."""

    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_third_party_actions_are_immutably_pinned() -> None:
    action_revisions = re.findall(
        r"^\s*uses:\s*([^\s@]+)@([^\s#]+)",
        _workflow_text(),
        flags=re.MULTILINE,
    )

    assert action_revisions
    for action_name, revision in action_revisions:
        assert action_name.startswith("actions/")
        assert re.fullmatch(r"[0-9a-f]{40}", revision)


def test_workflow_has_minimal_permissions_and_no_model_credentials() -> None:
    workflow_text = _workflow_text()

    assert "permissions:\n  contents: read" in workflow_text
    assert "secrets: inherit" not in workflow_text
    assert "COPILOT_GITHUB_TOKEN" not in workflow_text
    assert "NVIDIA_NIM_API_KEY" not in workflow_text
    assert "persist-credentials: false" in workflow_text


def test_real_postgresql_and_exact_coverage_are_required() -> None:
    workflow_text = _workflow_text()

    assert "postgres:17" in workflow_text
    assert "postgres:18" in workflow_text
    assert "ORGMETRA_TEST_ADMIN_DATABASE_URL" in workflow_text
    assert "--branch" in workflow_text
    assert "--fail-under=100" in workflow_text
    assert "covered_branches" in workflow_text
    assert "validate_docstrings.py" in workflow_text
