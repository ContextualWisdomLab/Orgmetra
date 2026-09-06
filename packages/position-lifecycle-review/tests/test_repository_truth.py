"""Repository-state truth contract for Position lifecycle review documentation."""

from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_DOCUMENTS = (
    _REPOSITORY_ROOT / "docs/traceability/position-lifecycle-review.md",
    _REPOSITORY_ROOT / "docs/adr/0111-governed-position-lifecycle-review.md",
    _REPOSITORY_ROOT / "packages/position-lifecycle-review/README.md",
)


def test_lifecycle_review_docs_describe_effective_repository_controls() -> None:
    """Buyer-facing docs must not mistake classic protection for effective rules."""
    for document_path in _DOCUMENTS:
        document = document_path.read_text(encoding="utf-8")
        assert "issue #89" in document.lower()
        assert "effective organization ruleset" in document
        assert "branch protection is currently absent" not in document
        assert "Protected `develop`" not in document
        assert "Protected Orgmetra" not in document
