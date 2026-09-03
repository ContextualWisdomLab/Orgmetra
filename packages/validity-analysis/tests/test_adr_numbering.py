"""Regression tests for repository-wide ADR number ownership."""

from pathlib import Path


def test_adr_numbers_are_unique_across_the_integrated_repository() -> None:
    """Every four-digit ADR number must identify exactly one decision record."""
    adr_directory = Path(__file__).resolve().parents[3] / "docs" / "adr"
    owners: dict[str, str] = {}

    for adr_path in sorted(adr_directory.glob("[0-9][0-9][0-9][0-9]-*.md")):
        adr_number = adr_path.name[:4]
        previous_owner = owners.get(adr_number)
        assert previous_owner is None, (
            f"ADR {adr_number} is reused by {previous_owner} and {adr_path.name}"
        )
        owners[adr_number] = adr_path.name
