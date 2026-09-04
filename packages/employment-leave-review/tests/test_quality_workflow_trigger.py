"""Regression tests for the employment-leave quality-gate trigger surface."""

from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOW_PATH = _REPOSITORY_ROOT / ".github/workflows/employment-leave-review-quality.yml"
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
            "Employment Leave Review Quality"
        )


def test_quality_workflow_contract_is_independent_of_process_cwd(monkeypatch) -> None:
    """Read the repository workflow even when pytest starts from the package directory."""
    package_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(package_root)

    workflow = _WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "Employment Leave Review Quality" in workflow
