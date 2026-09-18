"""Fail closed when Workforce Validation advertises an uninstallable Python floor."""

from __future__ import annotations

from pathlib import Path
import tomllib

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import Version


_SERVICE_ROOT = Path(__file__).resolve().parents[1]
_REPOSITORY_ROOT = _SERVICE_ROOT.parents[1]
_KEYVERSE_PROJECT = _REPOSITORY_ROOT / "packages" / "keyverse-adapter" / "pyproject.toml"
_KEYVERSE_NAME = "orgmetra-keyverse-adapter"


def _project_metadata(path: Path) -> dict[str, object]:
    """Read static project metadata without importing executable package code."""
    with path.open("rb") as stream:
        document = tomllib.load(stream)
    project = document.get("project")
    assert isinstance(project, dict), f"{path} must define a [project] table"
    return project


def _inclusive_python_floor(raw_specifier: object, *, owner: str) -> Version:
    """Resolve one reviewed inclusive Python floor or fail before comparing ranges."""
    assert isinstance(raw_specifier, str), f"{owner} requires-python must be text"
    specifiers = tuple(SpecifierSet(raw_specifier))
    assert len(specifiers) == 1 and specifiers[0].operator == ">=", (
        f"{owner} requires-python must remain one explicit inclusive floor; "
        "extend this contract before adopting a compound range"
    )
    return Version(specifiers[0].version)


def test_service_python_floor_covers_mandatory_keyverse_dependency() -> None:
    """Reject a service floor below the exact owned Keyverse dependency floor."""
    service_project = _project_metadata(_SERVICE_ROOT / "pyproject.toml")
    keyverse_project = _project_metadata(_KEYVERSE_PROJECT)

    service_dependencies = service_project.get("dependencies")
    assert isinstance(service_dependencies, list), "service dependencies must be a list"
    parsed_dependencies = [Requirement(value) for value in service_dependencies]
    keyverse_requirements = [
        requirement
        for requirement in parsed_dependencies
        if canonicalize_name(requirement.name) == canonicalize_name(_KEYVERSE_NAME)
    ]
    assert len(keyverse_requirements) == 1, "service must declare exactly one Keyverse dependency"

    keyverse_version = keyverse_project.get("version")
    assert isinstance(keyverse_version, str), "Keyverse project version must be text"
    assert keyverse_requirements[0].specifier == SpecifierSet(f"=={keyverse_version}"), (
        "service must consume the exact in-repository Keyverse version"
    )

    service_floor = _inclusive_python_floor(
        service_project.get("requires-python"), owner="workforce-validation-api"
    )
    keyverse_floor = _inclusive_python_floor(
        keyverse_project.get("requires-python"), owner="keyverse-adapter"
    )
    assert service_floor >= keyverse_floor, (
        "workforce-validation-api advertises Python versions where its mandatory "
        f"Keyverse dependency cannot install: service floor {service_floor}, "
        f"Keyverse floor {keyverse_floor}"
    )
