"""Regression contracts for Orgmetra quality-gate dispatch boundaries."""

from pathlib import Path


def _workflow(path: str) -> str:
    """Read one reviewed repository-local workflow as UTF-8 text."""
    return Path(path).read_text(encoding="utf-8")


def test_foundation_ci_delegates_people_api_to_discovered_service_runner() -> None:
    """Keep People API in the fail-closed discovered-service quality lane."""
    workflow = _workflow(".github/workflows/foundation-ci.yml")
    assert "      - develop\n" in workflow
    assert "Run discovered service contracts on primary runtime" in workflow
    assert "python scripts/foundation_service_compatibility.py --require-execution" in workflow
