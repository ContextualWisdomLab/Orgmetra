"""Tests for package-neutral Foundation service runtime discovery."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from packaging.version import Version


sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import foundation_service_compatibility as MODULE


def _write_project(
    root: Path,
    relative_dir: str,
    *,
    name: str,
    version: str,
    requires_python: str,
    dependencies: tuple[str, ...] = (),
    service: bool = False,
) -> Path:
    """Create minimal package metadata and, for services, executable layout."""
    project_dir = root / relative_dir
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "src").mkdir()
    if service:
        (project_dir / "tests").mkdir()
    deps = ",\n".join(f"  {json.dumps(dependency)}" for dependency in dependencies)
    dependencies_text = f"dependencies = [\n{deps}\n]\n" if dependencies else ""
    pyproject = project_dir / "pyproject.toml"
    pyproject.write_text(
        "\n".join(
            [
                "[project]",
                f'name = "{name}"',
                f'version = "{version}"',
                f'requires-python = "{requires_python}"',
                dependencies_text.rstrip(),
                "",
            ]
        ),
        encoding="utf-8",
    )
    return pyproject


def test_normalize_project_name_matches_pypa_equivalence() -> None:
    """Hyphen, underscore, dot, and case variants normalize to one lookup key."""
    expected = "orgmetra-hris-kernel"
    for candidate in (
        "orgmetra-hris-kernel",
        "Orgmetra_HRIS.Kernel",
        "ORGMETRA...HRIS___KERNEL",
    ):
        assert MODULE.normalize_project_name(candidate) == expected


def test_service_discovery_fails_closed_when_layout_is_incomplete(tmp_path: Path) -> None:
    """A pyproject cannot escape execution by omitting its owned tests directory."""
    _write_project(
        tmp_path,
        "services/incomplete-api",
        name="orgmetra-incomplete-api",
        version="0.1.0",
        requires_python=">=3.11",
    )
    with pytest.raises(MODULE.ServiceCompatibilityError, match="requires both src/ and tests/"):
        MODULE.discover_services(tmp_path)


@pytest.mark.parametrize(
    "dependency, match",
    [
        ("orgmetra-missing==1.0.0", "unknown owned dependency"),
        ("Orgmetra_Core==1.0.0", "exact canonical pin"),
        ("orgmetra-core==0.9.0", "exact canonical pin"),
        ("orgmetra-core>=1.0.0", "exact canonical pin"),
        ("orgmetra-core[extra]==1.0.0", "exact canonical pin"),
        ('orgmetra-core==1.0.0; python_version >= "3.12"', "exact canonical pin"),
    ],
)
def test_owned_dependencies_fail_closed(
    tmp_path: Path, dependency: str, match: str
) -> None:
    """Unknown, aliased, conditional, extra, or stale owned requirements are rejected."""
    _write_project(
        tmp_path,
        "packages/core",
        name="orgmetra-core",
        version="1.0.0",
        requires_python=">=3.12",
    )
    _write_project(
        tmp_path,
        "services/sample-api",
        name="orgmetra-sample-api",
        version="1.0.0",
        requires_python=">=3.11",
        dependencies=(dependency,),
        service=True,
    )
    with pytest.raises(MODULE.ServiceCompatibilityError, match=match):
        MODULE.plan_service_executions(tmp_path, Version("3.12.8"))


def test_runtime_contradiction_is_detected_from_exact_interpreter(tmp_path: Path) -> None:
    """A service cannot advertise an exact runtime rejected by its owned closure."""
    _write_project(
        tmp_path,
        "packages/core",
        name="orgmetra-core",
        version="1.0.0",
        requires_python=">=3.12",
    )
    _write_project(
        tmp_path,
        "services/sample-api",
        name="orgmetra-sample-api",
        version="1.0.0",
        requires_python=">=3.11",
        dependencies=("orgmetra-core==1.0.0",),
        service=True,
    )
    with pytest.raises(MODULE.ServiceCompatibilityError, match="runtime 3.11.9"):
        MODULE.plan_service_executions(tmp_path, Version("3.11.9"))


def test_unsupported_service_is_not_executed(tmp_path: Path) -> None:
    """A runtime outside the service specifier produces no false execution evidence."""
    _write_project(
        tmp_path,
        "services/sample-api",
        name="orgmetra-sample-api",
        version="1.0.0",
        requires_python=">=3.12",
        service=True,
    )
    calls: list[str] = []

    def runner(service, source_paths) -> None:
        """Record any unexpected execution."""
        calls.append(service.name)

    assert MODULE.execute_services(tmp_path, Version("3.11.9"), runner=runner) == ()
    assert calls == []


def test_empty_dependency_service_executes_on_declared_runtime(tmp_path: Path) -> None:
    """An independent service is still executed even without owned dependencies."""
    _write_project(
        tmp_path,
        "services/product-composition-api",
        name="orgmetra-product-composition-api",
        version="0.1.0",
        requires_python=">=3.11",
        service=True,
    )
    calls: list[tuple[str, tuple[Path, ...]]] = []

    def runner(service, source_paths) -> None:
        """Capture the planned source boundary."""
        calls.append((service.name, source_paths))

    executed = MODULE.execute_services(tmp_path, Version("3.11.9"), runner=runner)
    assert executed == ("orgmetra-product-composition-api",)
    assert calls == [
        (
            "orgmetra-product-composition-api",
            (tmp_path / "services/product-composition-api/src",),
        )
    ]


def test_owned_dependency_requires_source_layout(tmp_path: Path) -> None:
    """An owned dependency cannot enter service execution without its source directory."""
    package_project = _write_project(
        tmp_path,
        "packages/core",
        name="orgmetra-core",
        version="1.0.0",
        requires_python=">=3.11",
    )
    (package_project.parent / "src").rmdir()
    _write_project(
        tmp_path,
        "services/sample-api",
        name="orgmetra-sample-api",
        version="1.0.0",
        requires_python=">=3.11",
        dependencies=("orgmetra-core==1.0.0",),
        service=True,
    )
    with pytest.raises(MODULE.ServiceCompatibilityError, match="source directory is missing"):
        MODULE.plan_service_executions(tmp_path, Version("3.11.9"))


def test_transitive_owned_closure_is_included_in_pythonpath(tmp_path: Path) -> None:
    """Service execution receives every transitively pinned owned package source."""
    _write_project(
        tmp_path,
        "packages/base",
        name="orgmetra-base",
        version="1.0.0",
        requires_python=">=3.12",
    )
    _write_project(
        tmp_path,
        "packages/core",
        name="orgmetra-core",
        version="2.0.0",
        requires_python=">=3.12",
        dependencies=("orgmetra-base==1.0.0",),
    )
    _write_project(
        tmp_path,
        "services/sample-api",
        name="orgmetra-sample-api",
        version="1.0.0",
        requires_python=">=3.12",
        dependencies=("orgmetra-core==2.0.0",),
        service=True,
    )
    plans = MODULE.plan_service_executions(tmp_path, Version("3.12.8"))
    assert len(plans) == 1
    assert plans[0].source_paths == (
        tmp_path / "services/sample-api/src",
        tmp_path / "packages/base/src",
        tmp_path / "packages/core/src",
    )


def test_duplicate_normalized_owned_package_names_are_rejected(tmp_path: Path) -> None:
    """Two package directories cannot claim the same normalized distribution identity."""
    _write_project(
        tmp_path,
        "packages/a",
        name="orgmetra-core",
        version="1.0.0",
        requires_python=">=3.12",
    )
    _write_project(
        tmp_path,
        "packages/b",
        name="Orgmetra_Core",
        version="1.0.0",
        requires_python=">=3.12",
    )
    with pytest.raises(MODULE.ServiceCompatibilityError, match="duplicate owned package name"):
        MODULE.discover_packages(tmp_path)
