"""Regression tests for canonical Foundation service execution wiring."""

from pathlib import Path


def test_foundation_service_execution_is_discovery_driven_across_supported_runtimes() -> None:
    """Foundation must bind each discovered-service run to its matching interpreter."""
    workflow = Path(".github/workflows/foundation-ci.yml").read_text(encoding="utf-8")
    assert "PYTHONPATH=services/job-analysis-api" not in workflow
    assert "PYTHONPATH=services/people-api" not in workflow

    runtime_versions = ("3.11", "3.12", "3.13", "3.14")
    invocation = "run: python scripts/foundation_service_compatibility.py"
    assert workflow.count("python scripts/foundation_service_compatibility.py") == len(
        runtime_versions
    )

    for python_minor in runtime_versions:
        setup_token = f'python-version: "{python_minor}"'
        env_token = f'ORGMETRA_PYTHON_MINOR: "{python_minor}"'
        setup_index = workflow.index(setup_token)
        env_index = workflow.index(env_token, setup_index)
        run_index = workflow.index(invocation, env_index)
        next_setup_index = workflow.find('python-version: "', setup_index + len(setup_token))
        assert next_setup_index == -1 or run_index < next_setup_index

    primary_setup = workflow.index('python-version: "3.14"')
    primary_env = workflow.index('ORGMETRA_PYTHON_MINOR: "3.14"', primary_setup)
    primary_run = workflow.index(invocation, primary_env)
    primary_line_end = workflow.index("\n", primary_run)
    assert "--require-execution" in workflow[primary_run:primary_line_end]
