"""Repository-state truth contract for Position lifecycle review documentation."""

from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_DOCUMENTS = (
    _REPOSITORY_ROOT / "docs/traceability/position-lifecycle-review.md",
    _REPOSITORY_ROOT / "docs/adr/0111-governed-position-lifecycle-review.md",
    _REPOSITORY_ROOT / "packages/position-lifecycle-review/README.md",
)


def test_lifecycle_review_docs_do_not_claim_unenforced_branch_protection() -> None:
    """Buyer-facing docs must distinguish default-branch truth from protection state."""
    for document_path in _DOCUMENTS:
        document = document_path.read_text(encoding="utf-8")
        assert "issue #89" in document
        assert "Protected `develop`" not in document
        assert "Protected Orgmetra" not in document
