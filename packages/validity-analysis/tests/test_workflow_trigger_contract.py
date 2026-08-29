"""Regression for the validity package's repository-wide ADR numbering trigger."""

from pathlib import Path


def test_any_adr_change_runs_the_adr_numbering_regression() -> None:
    """Keep ADR uniqueness enforcement reachable when any decision record changes."""
    repository_root = Path(__file__).resolve().parents[3]
    workflow = (repository_root / ".github" / "workflows" / "validity-analysis-quality.yml").read_text(
        encoding="utf-8"
    )

    assert '      - "docs/adr/**"' in workflow
