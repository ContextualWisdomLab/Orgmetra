"""Fail closed when Workforce Validation cannot ship as its declared Python distribution."""

from __future__ import annotations

from importlib.metadata import version as installed_version
import os
from pathlib import Path
import subprocess
import sys
import tomllib

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import Version
import pytest


_SERVICE_ROOT = Path(__file__).resolve().parents[1]
_REPOSITORY_ROOT = _SERVICE_ROOT.parents[1]
_KEYVERSE_ROOT = _REPOSITORY_ROOT / "packages" / "keyverse-adapter"
_KEYVERSE_PROJECT = _KEYVERSE_ROOT / "pyproject.toml"
_KEYVERSE_NAME = "orgmetra-keyverse-adapter"
_SERVICE_NAME = "orgmetra-workforce-validation-api"


def _toml_document(path: Path) -> dict[str, object]:
    """Read static TOML metadata without importing executable package code."""
    with path.open("rb") as stream:
        return tomllib.load(stream)


def _project_metadata(path: Path) -> dict[str, object]:
    """Read one project table and reject malformed package metadata."""
    project = _toml_document(path).get("project")
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


def _service_build_backend_requirement() -> Requirement:
    """Return the service's single exact setuptools build-backend requirement."""
    build_system = _toml_document(_SERVICE_ROOT / "pyproject.toml").get("build-system")
    assert isinstance(build_system, dict), "service pyproject must define [build-system]"
    raw_requirements = build_system.get("requires")
    assert isinstance(raw_requirements, list), "build-system requires must be a list"
    requirements = [Requirement(value) for value in raw_requirements]
    setuptools_requirements = [
        requirement
        for requirement in requirements
        if canonicalize_name(requirement.name) == canonicalize_name("setuptools")
    ]
    assert len(setuptools_requirements) == 1, "service must declare one setuptools backend"
    requirement = setuptools_requirements[0]
    specifiers = tuple(requirement.specifier)
    assert len(specifiers) == 1 and specifiers[0].operator == "==", (
        "service setuptools build backend must remain exactly pinned"
    )
    return requirement


def _subprocess_environment() -> dict[str, str]:
    """Remove checkout import leakage and prohibit package-index fallback."""
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment["PIP_NO_INDEX"] = "1"
    return environment


def _venv_python(venv_root: Path) -> Path:
    """Return the isolated interpreter path for the current operating system."""
    if os.name == "nt":
        return venv_root / "Scripts" / "python.exe"
    return venv_root / "bin" / "python"


def test_subprocess_environment_blocks_ambient_package_discovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject inherited pip sources or configuration that could escape the wheelhouse."""
    poisoned = {
        "PYTHONPATH": "https://example.invalid/pythonpath",
        "PYTHONHOME": "/tmp/example-python-home",
        "PIP_FIND_LINKS": "https://example.invalid/find-links",
        "PIP_INDEX_URL": "https://example.invalid/simple",
        "PIP_EXTRA_INDEX_URL": "https://example.invalid/extra",
        "PIP_CONFIG_FILE": "/tmp/example-pip.conf",
        "PIP_TRUSTED_HOST": "example.invalid",
    }
    for name, value in poisoned.items():
        monkeypatch.setenv(name, value)

    environment = _subprocess_environment()

    for name in (
        "PYTHONPATH",
        "PYTHONHOME",
        "PIP_FIND_LINKS",
        "PIP_INDEX_URL",
        "PIP_EXTRA_INDEX_URL",
        "PIP_TRUSTED_HOST",
    ):
        assert name not in environment, f"ambient package source leaked through {name}"
    assert environment["PIP_NO_INDEX"] == "1"
    assert environment["PIP_CONFIG_FILE"] == os.devnull


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


def test_built_distribution_closure_installs_without_checkout_imports(tmp_path: Path) -> None:
    """Build local wheels and prove the exact service dependency closure installs offline."""
    backend_requirement = _service_build_backend_requirement()
    assert Version(installed_version("setuptools")) in backend_requirement.specifier, (
        "canonical test/build toolchain must install the service's exact setuptools backend "
        f"before distribution acceptance; required {backend_requirement.specifier}, "
        f"observed {installed_version('setuptools')}"
    )

    service_project = _project_metadata(_SERVICE_ROOT / "pyproject.toml")
    service_version = service_project.get("version")
    assert isinstance(service_version, str), "service project version must be text"

    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    environment = _subprocess_environment()
    for source_root in (_KEYVERSE_ROOT, _SERVICE_ROOT):
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                "--no-deps",
                "--no-build-isolation",
                "--wheel-dir",
                str(wheelhouse),
                str(source_root),
            ],
            cwd=_REPOSITORY_ROOT,
            env=environment,
            check=True,
        )

    install_venv = tmp_path / "install-venv"
    subprocess.run(
        [sys.executable, "-m", "venv", str(install_venv)],
        cwd=tmp_path,
        env=environment,
        check=True,
    )
    isolated_python = _venv_python(install_venv)
    subprocess.run(
        [
            str(isolated_python),
            "-m",
            "pip",
            "install",
            "--no-index",
            f"--find-links={wheelhouse}",
            f"{_SERVICE_NAME}=={service_version}",
        ],
        cwd=tmp_path,
        env=environment,
        check=True,
    )
    subprocess.run(
        [str(isolated_python), "-m", "pip", "check"],
        cwd=tmp_path,
        env=environment,
        check=True,
    )

    probe = "\n".join(
        [
            "from importlib.metadata import version",
            "from pathlib import Path",
            "import sys",
            "import orgmetra_keyverse_adapter",
            "import orgmetra_workforce_validation_api",
            f"assert version({_KEYVERSE_NAME!r}) == '0.1.0'",
            f"assert version({_SERVICE_NAME!r}) == {service_version!r}",
            "prefix = Path(sys.prefix).resolve()",
            "for module in (orgmetra_keyverse_adapter, orgmetra_workforce_validation_api):",
            "    module_path = Path(module.__file__).resolve()",
            "    assert prefix in module_path.parents, (prefix, module_path)",
        ]
    )
    subprocess.run(
        [str(isolated_python), "-c", probe],
        cwd=tmp_path,
        env=environment,
        check=True,
    )
