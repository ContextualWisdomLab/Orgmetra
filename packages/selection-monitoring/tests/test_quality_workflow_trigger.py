"""Regression tests for the selection-monitoring quality-gate trigger surface."""

from pathlib import Path


_WORKFLOW_PATH = Path(".github/workflows/selection-monitoring-quality.yml")
_SHARED_TEST_CONFIGURATION = (
    ".gitignore",
    ".python-version",
    "conftest.py",
    "packages/conftest.py",
    "pyproject.toml",
    "pytest.ini",
    "setup.cfg",
    "tox.ini",
)


def test_quality_workflow_retriggers_on_shared_test_configuration() -> None:
    """Require every shared test/runtime configuration input to retrigger this gate."""
    workflow = _WORKFLOW_PATH.read_text(encoding="utf-8")

    for path in _SHARED_TEST_CONFIGURATION:
        assert f'- "{path}"' in workflow, (
            f"{path} can change package test or clean-checkout behavior and must retrigger "
            "Selection Monitoring Quality"
        )
