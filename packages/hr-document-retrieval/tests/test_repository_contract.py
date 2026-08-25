"""Repository-level guardrails for the dedicated document retrieval quality gate."""

from pathlib import Path


def test_quality_workflow_watches_every_governance_surface() -> None:
    """ADR/doctoring/traceability-only changes must still run the dedicated gate."""
    root = Path(__file__).resolve().parents[3]
    workflow = (root / ".github/workflows/hr-document-retrieval-quality.yml").read_text()
    for expected_path in (
        '"packages/hr-document-retrieval/**"',
        '"docs/adr/0116-purpose-bound-hr-document-retrieval.md"',
        '"docs/doctoring/hr-document-retrieval-references.md"',
        '"docs/traceability/hr-document-retrieval.md"',
    ):
        assert expected_path in workflow


def test_docs_keep_active_pr_truth_distinct_from_protected_main() -> None:
    """The active PR must never be described as already shipped on develop."""
    root = Path(__file__).resolve().parents[3]
    traceability = (root / "docs/traceability/hr-document-retrieval.md").read_text()
    assert "does not contain this executable retrieval boundary" in traceability
    assert "checks, reviews, source code, and PR state do not transfer" in traceability
