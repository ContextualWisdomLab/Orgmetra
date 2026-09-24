"""Regression tests for canonical Foundation service execution wiring."""

from pathlib import Path


def test_foundation_service_execution_is_discovery_driven_across_supported_runtimes() -> None:
    """Foundation must execute discovered services rather than a service-name switchboard."""
    workflow = Path(".github/workflows/foundation-ci.yml").read_text(encoding="utf-8")
    assert "PYTHONPATH=services/job-analysis-api" not in workflow
    assert "PYTHONPATH=services/people-api" not in workflow
    assert workflow.count("python scripts/foundation_service_compatibility.py") == 4
    assert 'python-version: "3.11"' in workflow
    assert 'ORGMETRA_PYTHON_MINOR: "3.11"' in workflow
