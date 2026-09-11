"""Keep Job Analysis API package metadata aligned with canonical owned packages."""

from pathlib import Path
import re
import tomllib

import pytest


_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_OWNED_PACKAGE_PATHS = ("packages/hris-kernel", "packages/keyverse-adapter")


def _project_metadata(relative_path: str) -> dict[str, object]:
    """Read project metadata without importing or executing package code."""
    pyproject_path = _REPOSITORY_ROOT / relative_path / "pyproject.toml"
    with pyproject_path.open("rb") as pyproject_file:
        return tomllib.load(pyproject_file)["project"]


def _minimum_python_version(project: dict[str, object]) -> tuple[int, int]:
    """Return the exact declared lower Python minor for the current simple contract."""
    requires_python = project.get("requires-python")
    assert isinstance(requires_python, str)
    match = re.fullmatch(r">=(\d+)\.(\d+)", requires_python)
    assert match is not None, "requires-python must remain an explicit >=major.minor floor"
    return int(match.group(1)), int(match.group(2))


def _expected_owned_dependencies() -> set[str]:
    """Return canonical exact pins for every owned Job Analysis dependency."""
    expected_dependencies = set()
    for package_path in _OWNED_PACKAGE_PATHS:
        package_project = _project_metadata(package_path)
        expected_dependencies.add(
            f"{package_project['name']}=={package_project['version']}"
        )
    return expected_dependencies


def _assert_owned_dependency_pins(
    declared_dependencies: list[str], expected_dependencies: set[str]
) -> None:
    """Require declared internal dependencies to equal the canonical owned pins."""
    declared_owned_dependencies = {
        dependency
        for dependency in declared_dependencies
        if dependency.startswith("orgmetra-")
    }
    assert declared_owned_dependencies == expected_dependencies


def test_owned_dependency_contract_rejects_extra_internal_pin() -> None:
    """Reject an unknown or stale internal package that a subset check would miss."""
    expected_dependencies = {"orgmetra-hris-kernel==0.4.0"}
    with pytest.raises(AssertionError):
        _assert_owned_dependency_pins(
            ["orgmetra-hris-kernel==0.4.0", "orgmetra-stale-package==0.1.0"],
            expected_dependencies,
        )


def test_owned_dependency_contract_rejects_normalized_internal_alias() -> None:
    """Reject internal names whose underscore spelling normalizes into Orgmetra."""
    expected_dependencies = {"orgmetra-hris-kernel==0.4.0"}
    with pytest.raises(AssertionError):
        _assert_owned_dependency_pins(
            ["orgmetra-hris-kernel==0.4.0", "orgmetra_stale_package==0.1.0"],
            expected_dependencies,
        )


def test_job_analysis_api_internal_dependencies_match_owned_package_versions() -> None:
    """Reject stale internal distribution pins hidden by source-tree PYTHONPATH tests."""
    service_project = _project_metadata("services/job-analysis-api")
    declared_dependencies = service_project["dependencies"]
    assert isinstance(declared_dependencies, list)
    assert all(isinstance(dependency, str) for dependency in declared_dependencies)

    _assert_owned_dependency_pins(
        declared_dependencies,
        _expected_owned_dependencies(),
    )


def test_job_analysis_api_python_floor_covers_owned_runtime_dependencies() -> None:
    """Reject a service Python floor that cannot install its mandatory owned packages."""
    service_project = _project_metadata("services/job-analysis-api")
    service_floor = _minimum_python_version(service_project)

    for package_path in _OWNED_PACKAGE_PATHS:
        package_project = _project_metadata(package_path)
        assert _minimum_python_version(package_project) <= service_floor
