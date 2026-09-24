"""Edge coverage for Foundation service compatibility ownership."""

from __future__ import annotations

import json
import runpy
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
    """Create a minimal owned project fixture."""
    project_dir = root / relative_dir
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "src").mkdir()
    if service:
        (project_dir / "tests").mkdir()
    deps = ",\n".join(f"  {json.dumps(dependency)}" for dependency in dependencies)
    dependency_text = f"dependencies = [\n{deps}\n]\n" if dependencies else ""
    pyproject = project_dir / "pyproject.toml"
    pyproject.write_text(
        "\n".join(
            [
                "[project]",
                f'name = "{name}"',
                f'version = "{version}"',
                f'requires-python = "{requires_python}"',
                dependency_text.rstrip(),
                "",
            ]
        ),
        encoding="utf-8",
    )
    return pyproject


@pytest.mark.parametrize(
    "project_text, match",
    [
        ("", r"\[project\] metadata is required"),
        (
            "[project]\nname = 3\nversion = \"1.0.0\"\nrequires-python = \">=3.11\"\n",
            "project.name is required",
        ),
        (
            "[project]\nname = \"x\"\nversion = \"\"\nrequires-python = \">=3.11\"\n",
            "project.version is required",
        ),
        (
            "[project]\nname = \"x\"\nversion = \"1\"\nrequires-python = \"not a specifier\"\n",
            "invalid project.requires-python",
        ),
        (
            "[project]\nname = \"x\"\nversion = \"1\"\nrequires-python = \">=3.11\"\ndependencies = 3\n",
            "project.dependencies must be a string array",
        ),
        (
            "[project]\nname = \"x\"\nversion = \"1\"\nrequires-python = \">=3.11\"\ndependencies = [\"not a valid @@@\"]\n",
            "invalid project dependency",
        ),
    ],
)
def test_invalid_project_metadata_fails_closed(
    tmp_path: Path, project_text: str, match: str
) -> None:
    """Malformed metadata never becomes compatibility evidence."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(project_text, encoding="utf-8")
    with pytest.raises(MODULE.ServiceCompatibilityError, match=match):
        MODULE.read_project(pyproject, require_layout=False)


def test_unreadable_or_invalid_toml_fails_closed(tmp_path: Path) -> None:
    """Missing files and invalid TOML are reported as unreadable metadata."""
    with pytest.raises(MODULE.ServiceCompatibilityError, match="unreadable pyproject"):
        MODULE.read_project(tmp_path / "missing.toml", require_layout=False)
    invalid = tmp_path / "invalid.toml"
    invalid.write_text("[project\n", encoding="utf-8")
    with pytest.raises(MODULE.ServiceCompatibilityError, match="unreadable pyproject"):
        MODULE.read_project(invalid, require_layout=False)


def test_service_discovery_requires_at_least_one_service(tmp_path: Path) -> None:
    """An empty service inventory cannot silently pass."""
    (tmp_path / "services").mkdir()
    with pytest.raises(MODULE.ServiceCompatibilityError, match="no owned service"):
        MODULE.discover_services(tmp_path)


def test_external_dependencies_do_not_enter_owned_source_closure(tmp_path: Path) -> None:
    """Third-party requirements remain outside Orgmetra-owned source authority."""
    _write_project(
        tmp_path,
        "services/sample-api",
        name="orgmetra-sample-api",
        version="1.0.0",
        requires_python=">=3.11",
        dependencies=("requests>=2",),
        service=True,
    )
    plans = MODULE.plan_service_executions(tmp_path, Version("3.11.9"))
    assert plans[0].source_paths == (tmp_path / "services/sample-api/src",)


def test_direct_reference_owned_dependency_is_rejected(tmp_path: Path) -> None:
    """An owned direct reference cannot bypass the canonical exact pin."""
    _write_project(
        tmp_path,
        "packages/core",
        name="orgmetra-core",
        version="1.0.0",
        requires_python=">=3.11",
    )
    _write_project(
        tmp_path,
        "services/sample-api",
        name="orgmetra-sample-api",
        version="1.0.0",
        requires_python=">=3.11",
        dependencies=("orgmetra-core @ https://example.com/core.whl",),
        service=True,
    )
    with pytest.raises(MODULE.ServiceCompatibilityError, match="exact canonical pin"):
        MODULE.plan_service_executions(tmp_path, Version("3.11.9"))


def test_transitive_cycle_is_rejected(tmp_path: Path) -> None:
    """Owned dependency cycles fail before service execution."""
    _write_project(
        tmp_path,
        "packages/a",
        name="orgmetra-a",
        version="1.0.0",
        requires_python=">=3.11",
        dependencies=("orgmetra-b==1.0.0",),
    )
    _write_project(
        tmp_path,
        "packages/b",
        name="orgmetra-b",
        version="1.0.0",
        requires_python=">=3.11",
        dependencies=("orgmetra-a==1.0.0",),
    )
    _write_project(
        tmp_path,
        "services/sample-api",
        name="orgmetra-sample-api",
        version="1.0.0",
        requires_python=">=3.11",
        dependencies=("orgmetra-a==1.0.0",),
        service=True,
    )
    with pytest.raises(MODULE.ServiceCompatibilityError, match="cyclic owned dependency"):
        MODULE.plan_service_executions(tmp_path, Version("3.11.9"))


def test_duplicate_transitive_dependency_is_deduplicated(tmp_path: Path) -> None:
    """A package reached directly and transitively is included exactly once."""
    _write_project(
        tmp_path,
        "packages/base",
        name="orgmetra-base",
        version="1.0.0",
        requires_python=">=3.11",
    )
    _write_project(
        tmp_path,
        "packages/core",
        name="orgmetra-core",
        version="1.0.0",
        requires_python=">=3.11",
        dependencies=("orgmetra-base==1.0.0",),
    )
    _write_project(
        tmp_path,
        "services/sample-api",
        name="orgmetra-sample-api",
        version="1.0.0",
        requires_python=">=3.11",
        dependencies=("orgmetra-core==1.0.0", "orgmetra-base==1.0.0"),
        service=True,
    )
    plan = MODULE.plan_service_executions(tmp_path, Version("3.11.9"))[0]
    assert plan.source_paths.count(tmp_path / "packages/base/src") == 1


def test_run_pytest_uses_service_config_and_detached_coverage_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Runtime execution uses the service pytest config and exact source closure."""
    pyproject = _write_project(
        tmp_path,
        "services/sample-api",
        name="orgmetra-sample-api",
        version="1.0.0",
        requires_python=">=3.11",
        service=True,
    )
    service = MODULE.read_project(pyproject, require_layout=True)
    captured: dict[str, object] = {}

    def fake_run(command, *, check, env):
        """Capture subprocess authority without launching pytest."""
        captured["command"] = command
        captured["check"] = check
        captured["env"] = env

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)
    MODULE._run_pytest(service, (pyproject.parent / "src",))
    assert captured["command"] == [
        sys.executable,
        "-m",
        "pytest",
        "-c",
        str(pyproject),
        str(pyproject.parent / "tests"),
    ]
    assert captured["check"] is True
    assert captured["env"]["PYTHONPATH"] == str(pyproject.parent / "src")
    assert "orgmetra-sample-api" in captured["env"]["COVERAGE_FILE"]


def test_main_reports_exact_runtime_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI reporting binds to the active interpreter and execution set."""
    observed: dict[str, object] = {}

    def fake_execute(root_path, runtime, *, runner=MODULE._run_pytest):
        """Capture CLI planning inputs."""
        observed["root"] = root_path
        observed["runtime"] = runtime
        return ("orgmetra-sample-api",)

    monkeypatch.setattr(MODULE, "execute_services", fake_execute)
    assert MODULE.main(["--root", str(tmp_path)]) == 0
    assert observed["root"] == tmp_path.resolve()
    assert observed["runtime"] == Version(
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    assert "executed=1 [orgmetra-sample-api]" in capsys.readouterr().out


def test_cli_guard_executes_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The executable script guard delegates to main rather than becoming dead code."""
    _write_project(
        tmp_path,
        "services/sample-api",
        name="orgmetra-sample-api",
        version="1.0.0",
        requires_python="<2",
        service=True,
    )
    script = Path(__file__).parents[1] / "scripts/foundation_service_compatibility.py"
    monkeypatch.setattr(sys, "argv", [str(script), "--root", str(tmp_path)])
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(str(script), run_name="__main__")
    assert exit_info.value.code == 0
