"""Fail closed when Workforce Validation cannot ship as its declared Python distribution."""

from __future__ import annotations

import base64
import csv
from email.parser import Parser
import hashlib
from importlib.metadata import version as installed_version
import io
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tomllib
import zipfile

from packaging.markers import Marker
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name, parse_wheel_filename
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
    """Remove checkout and ambient pip discovery inputs before offline acceptance."""
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    for name in tuple(environment):
        if name.startswith("PIP_"):
            environment.pop(name)
    environment["PIP_CONFIG_FILE"] = os.devnull
    environment["PIP_NO_INDEX"] = "1"
    environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    return environment


def _venv_python(venv_root: Path) -> Path:
    """Return the isolated interpreter path for the current operating system."""
    if os.name == "nt":
        return venv_root / "Scripts" / "python.exe"
    return venv_root / "bin" / "python"


def _sha256(path: Path) -> str:
    """Hash one built artifact before it becomes an installation candidate."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _record_hash(content: bytes) -> str:
    """Return the URL-safe unpadded sha256 representation required by wheel RECORD."""
    digest = hashlib.sha256(content).digest()
    encoded = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return f"sha256={encoded}"


def _canonical_wheel_member_path(member_path: str, *, wheel_name: str) -> str:
    """Return one canonical relative POSIX wheel member path or fail closed."""
    path = PurePosixPath(member_path)
    assert path.parts and not path.is_absolute(), (
        f"{wheel_name} contains an absolute or empty wheel member path"
    )
    assert ".." not in path.parts and "\\" not in member_path, (
        f"{wheel_name} contains a non-canonical wheel member path"
    )
    canonical = path.as_posix()
    assert member_path == canonical, (
        f"{wheel_name} contains a non-canonical wheel member path"
    )
    return canonical


def _validate_wheel_record(wheel_path: Path) -> None:
    """Verify canonical member identity and the complete wheel installation RECORD."""
    with zipfile.ZipFile(wheel_path) as archive:
        infos = tuple(info for info in archive.infolist() if not info.is_dir())
        archive_paths = [info.filename for info in infos]
        assert len(archive_paths) == len(set(archive_paths)), (
            f"{wheel_path.name} contains duplicate archive member paths"
        )
        canonical_archive_paths = [
            _canonical_wheel_member_path(path, wheel_name=wheel_path.name)
            for path in archive_paths
        ]
        assert len(canonical_archive_paths) == len(set(canonical_archive_paths)), (
            f"{wheel_path.name} contains normalization-colliding archive member paths"
        )
        record_paths = [
            path
            for path in canonical_archive_paths
            if len(PurePosixPath(path).parts) == 2
            and PurePosixPath(path).parts[0].endswith(".dist-info")
            and PurePosixPath(path).name == "RECORD"
        ]
        assert len(record_paths) == 1, (
            f"{wheel_path.name} must contain exactly one dist-info RECORD"
        )
        record_path = record_paths[0]
        record_text = archive.read(record_path).decode("utf-8")
        rows = tuple(csv.reader(io.StringIO(record_text)))
        assert rows, f"{wheel_path.name} RECORD must not be empty"

        recorded: dict[str, tuple[str, str]] = {}
        for row in rows:
            assert len(row) == 3, f"{wheel_path.name} RECORD rows must have three columns"
            member_path, member_hash, member_size = row
            canonical_member_path = _canonical_wheel_member_path(
                member_path,
                wheel_name=wheel_path.name,
            )
            assert canonical_member_path not in recorded, (
                f"{wheel_path.name} RECORD contains duplicate path {member_path}"
            )
            recorded[canonical_member_path] = (member_hash, member_size)

        assert set(recorded) == set(canonical_archive_paths), (
            f"{wheel_path.name} RECORD must cover every wheel member exactly once"
        )
        for info in infos:
            canonical_info_path = _canonical_wheel_member_path(
                info.filename,
                wheel_name=wheel_path.name,
            )
            member_hash, member_size = recorded[canonical_info_path]
            if canonical_info_path == record_path:
                assert member_hash == "" and member_size == "", (
                    f"{wheel_path.name} RECORD self-entry must leave hash and size empty"
                )
                continue
            content = archive.read(info.filename)
            assert member_hash == _record_hash(content), (
                f"{wheel_path.name} RECORD sha256 mismatch for {info.filename}"
            )
            assert member_size == str(len(content)), (
                f"{wheel_path.name} RECORD size mismatch for {info.filename}"
            )


def _validate_wheel_contents(
    wheel_path: Path,
    *,
    package_root: str,
    require_py_typed: bool,
) -> None:
    """Reject repository leakage, sibling source, or missing declared package data."""
    with zipfile.ZipFile(wheel_path) as archive:
        names = tuple(archive.namelist())

    assert names, f"{wheel_path.name} must not be empty"
    top_levels: set[str] = set()
    dist_info_roots: set[str] = set()
    for raw_name in names:
        parts = PurePosixPath(raw_name).parts
        if not parts:
            continue
        top_levels.add(parts[0])
        if parts[0].endswith(".dist-info"):
            dist_info_roots.add(parts[0])
        assert "tests" not in {part.lower() for part in parts}, (
            f"{wheel_path.name} leaked test content: {raw_name}"
        )
        assert not raw_name.endswith(".pyc"), (
            f"{wheel_path.name} must not ship bytecode: {raw_name}"
        )

    assert len(dist_info_roots) == 1, (
        f"{wheel_path.name} must contain exactly one .dist-info root"
    )
    allowed_top_levels = {package_root, *dist_info_roots}
    assert top_levels <= allowed_top_levels, (
        f"{wheel_path.name} contains unexpected top-level content: "
        f"{sorted(top_levels - allowed_top_levels)}"
    )
    assert package_root in top_levels, (
        f"{wheel_path.name} does not contain expected package root {package_root}"
    )
    if require_py_typed:
        assert f"{package_root}/py.typed" in names, (
            f"{wheel_path.name} must include declared py.typed package data"
        )


def _requirement_identity(requirement: Requirement) -> tuple[str, tuple[str, ...], str, str, str]:
    """Normalize one dependency declaration without dropping extras, markers, or direct URLs."""
    return (
        canonicalize_name(requirement.name),
        tuple(sorted(canonicalize_name(extra) for extra in requirement.extras)),
        str(requirement.specifier),
        str(requirement.marker) if requirement.marker is not None else "",
        requirement.url or "",
    )


def _reviewed_dependency_metadata(
    project: dict[str, object],
    *,
    owner: str,
) -> tuple[tuple[Requirement, ...], tuple[str, ...]]:
    """Expand reviewed base and optional dependencies into built METADATA semantics."""
    raw_dependencies = project.get("dependencies", [])
    assert isinstance(raw_dependencies, list) and all(
        isinstance(value, str) for value in raw_dependencies
    ), f"{owner} project dependencies must be a text list"
    requirements = [Requirement(value) for value in raw_dependencies]

    raw_optional = project.get("optional-dependencies", {})
    assert isinstance(raw_optional, dict), f"{owner} optional-dependencies must be a table"
    extras: list[str] = []
    for raw_extra, raw_requirements in raw_optional.items():
        assert isinstance(raw_extra, str), f"{owner} optional dependency names must be text"
        assert isinstance(raw_requirements, list) and all(
            isinstance(value, str) for value in raw_requirements
        ), f"{owner} optional dependency group {raw_extra} must be a text list"
        normalized_extra = canonicalize_name(raw_extra)
        extras.append(normalized_extra)
        for value in raw_requirements:
            requirement = Requirement(value)
            extra_marker = f"extra == {normalized_extra!r}"
            if requirement.marker is None:
                requirement.marker = Marker(extra_marker)
            else:
                requirement.marker = Marker(f"({requirement.marker}) and {extra_marker}")
            requirements.append(requirement)

    assert len(extras) == len(set(extras)), f"{owner} optional dependency extras must be unique"
    return tuple(requirements), tuple(sorted(extras))


def _validate_wheel_metadata(
    wheel_path: Path,
    *,
    expected_name: str,
    expected_version: str,
    expected_requires_python: str,
    expected_dependencies: tuple[Requirement, ...],
    expected_extras: tuple[str, ...],
    required_dependency: tuple[str, str] | None = None,
) -> None:
    """Bind built METADATA to reviewed project identity, runtime, dependencies, and extras."""
    with zipfile.ZipFile(wheel_path) as archive:
        metadata_paths = [
            name
            for name in archive.namelist()
            if PurePosixPath(name).name == "METADATA"
            and len(PurePosixPath(name).parts) == 2
            and PurePosixPath(name).parts[0].endswith(".dist-info")
        ]
        assert len(metadata_paths) == 1, (
            f"{wheel_path.name} must contain exactly one dist-info METADATA file"
        )
        raw_metadata = archive.read(metadata_paths[0]).decode("utf-8")

    metadata = Parser().parsestr(raw_metadata)
    raw_name = metadata.get("Name")
    raw_version = metadata.get("Version")
    raw_requires_python = metadata.get("Requires-Python")
    assert raw_name is not None, f"{wheel_path.name} METADATA must declare Name"
    assert raw_version is not None, f"{wheel_path.name} METADATA must declare Version"
    assert raw_requires_python is not None, (
        f"{wheel_path.name} METADATA must declare Requires-Python"
    )
    assert canonicalize_name(raw_name) == canonicalize_name(expected_name), (
        f"{wheel_path.name} METADATA Name does not match reviewed project identity"
    )
    assert Version(raw_version) == Version(expected_version), (
        f"{wheel_path.name} METADATA Version does not match reviewed project version"
    )
    assert SpecifierSet(raw_requires_python) == SpecifierSet(expected_requires_python), (
        f"{wheel_path.name} METADATA Requires-Python does not match reviewed project runtime"
    )

    parsed_dependencies = [
        Requirement(value) for value in metadata.get_all("Requires-Dist", failobj=[])
    ]
    if required_dependency is not None:
        dependency_name, dependency_version = required_dependency
        matching_dependencies = [
            requirement
            for requirement in parsed_dependencies
            if canonicalize_name(requirement.name) == canonicalize_name(dependency_name)
        ]
        assert len(matching_dependencies) == 1, (
            f"{wheel_path.name} METADATA must preserve the mandatory Keyverse dependency"
        )
        requirement = matching_dependencies[0]
        assert requirement.specifier == SpecifierSet(f"=={dependency_version}"), (
            f"{wheel_path.name} METADATA must preserve the exact owned Keyverse version"
        )
        assert not requirement.extras and requirement.marker is None and requirement.url is None, (
            f"{wheel_path.name} mandatory Keyverse dependency must remain unconditional"
        )

    assert sorted(_requirement_identity(value) for value in parsed_dependencies) == sorted(
        _requirement_identity(value) for value in expected_dependencies
    ), f"{wheel_path.name} METADATA dependencies do not match reviewed project dependencies"

    built_extras = tuple(
        sorted(canonicalize_name(value) for value in metadata.get_all("Provides-Extra", failobj=[]))
    )
    assert built_extras == expected_extras, (
        f"{wheel_path.name} METADATA extras do not match reviewed optional dependencies"
    )


def _locked_wheel_requirements(
    wheelhouse: Path,
    *,
    service_version: str,
    keyverse_version: str,
) -> tuple[str, dict[str, Path]]:
    """Validate exact wheel identities and return a hash-locked install manifest."""
    expected_versions = {
        canonicalize_name(_KEYVERSE_NAME): Version(keyverse_version),
        canonicalize_name(_SERVICE_NAME): Version(service_version),
    }
    package_roots = {
        canonicalize_name(_KEYVERSE_NAME): "orgmetra_keyverse_adapter",
        canonicalize_name(_SERVICE_NAME): "orgmetra_workforce_validation_api",
    }
    source_projects = {
        canonicalize_name(_KEYVERSE_NAME): _project_metadata(_KEYVERSE_PROJECT),
        canonicalize_name(_SERVICE_NAME): _project_metadata(_SERVICE_ROOT / "pyproject.toml"),
    }
    wheels_by_name: dict[str, Path] = {}
    hashes_by_name: dict[str, str] = {}

    wheel_paths = tuple(sorted(wheelhouse.iterdir()))
    assert len(wheel_paths) == len(expected_versions), (
        "distribution acceptance must produce exactly the expected owned wheels"
    )
    assert all(path.is_file() and path.suffix == ".whl" for path in wheel_paths), (
        "isolated wheelhouse must contain wheel artifacts only"
    )
    for wheel_path in wheel_paths:
        parsed_name, parsed_version, build, _tags = parse_wheel_filename(wheel_path.name)
        canonical_name = canonicalize_name(parsed_name)
        assert build == (), f"{wheel_path.name} must not use an unreviewed build tag"
        assert canonical_name in expected_versions, (
            f"unexpected wheel in isolated wheelhouse: {wheel_path.name}"
        )
        assert parsed_version == expected_versions[canonical_name], (
            f"{wheel_path.name} version does not match repository metadata"
        )
        assert canonical_name not in wheels_by_name, (
            f"duplicate wheel identity for {canonical_name}"
        )
        project = source_projects[canonical_name]
        requires_python = project.get("requires-python")
        assert isinstance(requires_python, str), (
            f"{canonical_name} project requires-python must be text"
        )
        reviewed_dependencies, reviewed_extras = _reviewed_dependency_metadata(
            project,
            owner=canonical_name,
        )
        _validate_wheel_record(wheel_path)
        wheels_by_name[canonical_name] = wheel_path
        hashes_by_name[canonical_name] = _sha256(wheel_path)
        _validate_wheel_contents(
            wheel_path,
            package_root=package_roots[canonical_name],
            require_py_typed=canonical_name == canonicalize_name(_SERVICE_NAME),
        )
        _validate_wheel_metadata(
            wheel_path,
            expected_name=(
                _SERVICE_NAME
                if canonical_name == canonicalize_name(_SERVICE_NAME)
                else _KEYVERSE_NAME
            ),
            expected_version=str(expected_versions[canonical_name]),
            expected_requires_python=requires_python,
            expected_dependencies=reviewed_dependencies,
            expected_extras=reviewed_extras,
            required_dependency=(
                (_KEYVERSE_NAME, keyverse_version)
                if canonical_name == canonicalize_name(_SERVICE_NAME)
                else None
            ),
        )

    assert set(wheels_by_name) == set(expected_versions)
    lock_lines = [
        f"{_KEYVERSE_NAME}=={keyverse_version} --hash=sha256:{hashes_by_name[canonicalize_name(_KEYVERSE_NAME)]}",
        f"{_SERVICE_NAME}=={service_version} --hash=sha256:{hashes_by_name[canonicalize_name(_SERVICE_NAME)]}",
    ]
    return "\n".join(lock_lines) + "\n", wheels_by_name


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
    assert environment["PIP_DISABLE_PIP_VERSION_CHECK"] == "1"


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
    """Hash-bind local wheels and prove the exact dependency closure installs offline."""
    backend_requirement = _service_build_backend_requirement()
    assert Version(installed_version("setuptools")) in backend_requirement.specifier, (
        "canonical test/build toolchain must install the service's exact setuptools backend "
        f"before distribution acceptance; required {backend_requirement.specifier}, "
        f"observed {installed_version('setuptools')}"
    )

    service_project = _project_metadata(_SERVICE_ROOT / "pyproject.toml")
    service_version = service_project.get("version")
    assert isinstance(service_version, str), "service project version must be text"
    keyverse_project = _project_metadata(_KEYVERSE_PROJECT)
    keyverse_version = keyverse_project.get("version")
    assert isinstance(keyverse_version, str), "Keyverse project version must be text"

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
                "--no-index",
                "--no-cache-dir",
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

    locked_requirements, wheels_by_name = _locked_wheel_requirements(
        wheelhouse,
        service_version=service_version,
        keyverse_version=keyverse_version,
    )
    requirements_path = tmp_path / "built-wheel-requirements.txt"
    requirements_path.write_text(locked_requirements, encoding="utf-8")

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
            "--require-hashes",
            "--no-index",
            "--no-cache-dir",
            "--only-binary=:all:",
            f"--find-links={wheelhouse}",
            "--requirement",
            str(requirements_path),
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

    assert set(wheels_by_name) == {
        canonicalize_name(_KEYVERSE_NAME),
        canonicalize_name(_SERVICE_NAME),
    }
    probe = "\n".join(
        [
            "from importlib.metadata import version",
            "from pathlib import Path",
            "import sys",
            "import orgmetra_keyverse_adapter",
            "import orgmetra_workforce_validation_api",
            f"assert version({_KEYVERSE_NAME!r}) == {keyverse_version!r}",
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