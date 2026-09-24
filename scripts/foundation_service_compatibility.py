#!/usr/bin/env python3
"""Discover and execute Orgmetra service contracts against the active Python runtime."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version


_NORMALIZE_PROJECT_NAME_RE = re.compile(r"[-_.]+")


class ServiceCompatibilityError(RuntimeError):
    """Report a fail-closed service/distribution compatibility defect."""


@dataclass(frozen=True)
class ProjectMetadata:
    """Represent validated distribution metadata needed by Foundation compatibility."""

    path: Path
    name: str
    normalized_name: str
    version: str
    requires_python: SpecifierSet
    dependencies: tuple[Requirement, ...]
    source_dir: Path | None = None
    tests_dir: Path | None = None


@dataclass(frozen=True)
class ServiceExecution:
    """Describe one service execution and its complete owned source closure."""

    service: ProjectMetadata
    source_paths: tuple[Path, ...]


Runner = Callable[[ProjectMetadata, tuple[Path, ...]], None]


def normalize_project_name(name: str) -> str:
    """Normalize a Python distribution name according to PyPA name normalization."""
    return _NORMALIZE_PROJECT_NAME_RE.sub("-", name).lower()


def _require_text(project: dict[str, object], key: str, path: Path) -> str:
    """Read one required non-empty project metadata string."""
    value = project.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ServiceCompatibilityError(f"{path}: project.{key} is required")
    return value.strip()


def _read_requirements(project: dict[str, object], path: Path) -> tuple[Requirement, ...]:
    """Parse mandatory project dependencies with the canonical packaging parser."""
    raw_dependencies = project.get("dependencies", [])
    if not isinstance(raw_dependencies, list) or not all(
        isinstance(item, str) for item in raw_dependencies
    ):
        raise ServiceCompatibilityError(f"{path}: project.dependencies must be a string array")
    parsed: list[Requirement] = []
    for raw in raw_dependencies:
        try:
            parsed.append(Requirement(raw))
        except InvalidRequirement as exc:
            raise ServiceCompatibilityError(
                f"{path}: invalid project dependency {raw!r}"
            ) from exc
    return tuple(parsed)


def read_project(path: Path, *, require_layout: bool) -> ProjectMetadata:
    """Read one package or service pyproject without importing project code."""
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ServiceCompatibilityError(f"{path}: unreadable pyproject metadata") from exc
    project = document.get("project")
    if not isinstance(project, dict):
        raise ServiceCompatibilityError(f"{path}: [project] metadata is required")

    name = _require_text(project, "name", path)
    version = _require_text(project, "version", path)
    requires_python_text = _require_text(project, "requires-python", path)
    try:
        requires_python = SpecifierSet(requires_python_text)
    except InvalidSpecifier as exc:
        raise ServiceCompatibilityError(
            f"{path}: invalid project.requires-python {requires_python_text!r}"
        ) from exc

    root = path.parent
    source_dir = root / "src" if require_layout else None
    tests_dir = root / "tests" if require_layout else None
    if require_layout and (not source_dir.is_dir() or not tests_dir.is_dir()):
        raise ServiceCompatibilityError(
            f"{path}: owned service requires both src/ and tests/ directories"
        )

    return ProjectMetadata(
        path=path,
        name=name,
        normalized_name=normalize_project_name(name),
        version=version,
        requires_python=requires_python,
        dependencies=_read_requirements(project, path),
        source_dir=source_dir,
        tests_dir=tests_dir,
    )


def discover_packages(root: Path) -> dict[str, ProjectMetadata]:
    """Discover canonical owned package metadata keyed by normalized distribution name."""
    packages: dict[str, ProjectMetadata] = {}
    for pyproject in sorted((root / "packages").glob("*/pyproject.toml")):
        metadata = read_project(pyproject, require_layout=False)
        if metadata.normalized_name in packages:
            raise ServiceCompatibilityError(
                f"duplicate owned package name after normalization: {metadata.name}"
            )
        packages[metadata.normalized_name] = metadata
    return packages


def discover_services(root: Path) -> tuple[ProjectMetadata, ...]:
    """Discover every owned service distribution without a service-name switchboard."""
    services = tuple(
        read_project(pyproject, require_layout=True)
        for pyproject in sorted((root / "services").glob("*/pyproject.toml"))
    )
    if not services:
        raise ServiceCompatibilityError("no owned service pyproject.toml files were discovered")
    return services


def _owned_requirement(
    requirement: Requirement,
    packages: dict[str, ProjectMetadata],
    owner_path: Path,
) -> ProjectMetadata | None:
    """Resolve one mandatory Orgmetra dependency to its canonical owned package metadata."""
    normalized = normalize_project_name(requirement.name)
    if not normalized.startswith("orgmetra-"):
        return None
    package = packages.get(normalized)
    if package is None:
        raise ServiceCompatibilityError(
            f"{owner_path}: unknown owned dependency {requirement.name!r}"
        )
    expected_pin = f"=={package.version}"
    if (
        requirement.name != package.name
        or requirement.extras
        or requirement.marker is not None
        or requirement.url is not None
        or str(requirement.specifier) != expected_pin
    ):
        raise ServiceCompatibilityError(
            f"{owner_path}: owned dependency must be exact canonical pin "
            f"{package.name}{expected_pin}; got {str(requirement)!r}"
        )
    return package


def _owned_closure(
    project: ProjectMetadata,
    packages: dict[str, ProjectMetadata],
) -> tuple[ProjectMetadata, ...]:
    """Resolve the transitive mandatory owned dependency closure in stable order."""
    resolved: dict[str, ProjectMetadata] = {}
    visiting: set[str] = set()

    def visit(owner: ProjectMetadata) -> None:
        for requirement in owner.dependencies:
            package = _owned_requirement(requirement, packages, owner.path)
            if package is None or package.normalized_name in resolved:
                continue
            if package.normalized_name in visiting:
                raise ServiceCompatibilityError(
                    f"{owner.path}: cyclic owned dependency at {package.name}"
                )
            visiting.add(package.normalized_name)
            visit(package)
            visiting.remove(package.normalized_name)
            resolved[package.normalized_name] = package

    visit(project)
    return tuple(resolved[name] for name in sorted(resolved))


def plan_service_executions(
    root: Path,
    runtime: Version,
) -> tuple[ServiceExecution, ...]:
    """Validate service metadata and plan every service supported by the exact runtime."""
    packages = discover_packages(root)
    services = discover_services(root)
    executions: list[ServiceExecution] = []
    for service in services:
        closure = _owned_closure(service, packages)
        if runtime not in service.requires_python:
            continue
        incompatible = [
            package.name for package in closure if runtime not in package.requires_python
        ]
        if incompatible:
            raise ServiceCompatibilityError(
                f"{service.path}: runtime {runtime} is advertised by the service but "
                f"rejected by owned dependency closure: {', '.join(incompatible)}"
            )
        package_source_paths = tuple(package.path.parent / "src" for package in closure)
        missing_sources = tuple(path for path in package_source_paths if not path.is_dir())
        if missing_sources:
            raise ServiceCompatibilityError(
                f"{service.path}: owned dependency source directory is missing: "
                + ", ".join(str(path) for path in missing_sources)
            )
        source_paths = [service.source_dir]
        source_paths.extend(package_source_paths)
        if any(path is None for path in source_paths):
            raise AssertionError("service layout validation must provide source_dir")
        executions.append(
            ServiceExecution(
                service=service,
                source_paths=tuple(path for path in source_paths if path is not None),
            )
        )
    return tuple(executions)


def _run_pytest(service: ProjectMetadata, source_paths: tuple[Path, ...]) -> None:
    """Execute one service's own pytest configuration under an isolated coverage file."""
    if service.tests_dir is None:
        raise AssertionError("service layout validation must provide tests_dir")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(str(path) for path in source_paths)
    env["COVERAGE_FILE"] = (
        f"/tmp/orgmetra-{service.path.parent.name}-"
        f"{sys.version_info.major}.{sys.version_info.minor}.coverage"
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            str(service.path),
            str(service.tests_dir),
        ],
        check=True,
        env=env,
    )


def execute_services(
    root: Path,
    runtime: Version,
    *,
    runner: Runner = _run_pytest,
) -> tuple[str, ...]:
    """Execute every service that truthfully supports the exact active interpreter."""
    executions = plan_service_executions(root, runtime)
    for execution in executions:
        runner(execution.service, execution.source_paths)
    return tuple(execution.service.name for execution in executions)


def main(argv: Sequence[str] | None = None) -> int:
    """Run Foundation service discovery and compatibility acceptance."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args(argv)
    runtime = Version(
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    executed = execute_services(args.root.resolve(), runtime)
    print(
        f"Foundation service compatibility runtime={runtime}: "
        f"executed={len(executed)} [{', '.join(executed)}]"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
