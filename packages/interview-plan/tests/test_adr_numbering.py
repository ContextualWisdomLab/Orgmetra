"""Regression coverage for repository-wide ADR numbering collisions."""

from pathlib import Path


def test_adr_numeric_prefixes_are_unique() -> None:
    """Reject duplicate four-digit ADR identifiers after branch integration."""
    repository_root = Path(__file__).resolve().parents[3]
    adr_paths = sorted((repository_root / "docs" / "adr").glob("[0-9][0-9][0-9][0-9]-*.md"))
    adr_numbers = [path.name.split("-", 1)[0] for path in adr_paths]
    duplicate_numbers = sorted(
        number for number in set(adr_numbers) if adr_numbers.count(number) > 1
    )

    assert duplicate_numbers == [], f"duplicate ADR numeric prefixes: {duplicate_numbers}"
