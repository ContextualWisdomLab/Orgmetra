"""Regression coverage for one canonical compensation-review test input fixture."""

from pathlib import Path


def test_valid_packet_input_fixture_has_one_canonical_definition() -> None:
    """Keep the 24-field valid packet seed in conftest instead of copy-pasted tests."""
    tests_dir = Path(__file__).parent
    marker = (
        '"compensation_review_reference": '
        '"compensation_change_review:22222222-2222-4222-8222-222222222222"'
    )
    owners = sorted(
        path.name
        for path in tests_dir.glob("*.py")
        if marker in path.read_text(encoding="utf-8")
    )

    assert owners == ["conftest.py"]
