"""Keep People API package metadata aligned with canonical owned package versions."""

from pathlib import Path
import tomllib


_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _project_metadata(relative_path: str) -> dict[str, object]:
    """Read project metadata without importing or executing package code."""
    pyproject_path = _REPOSITORY_ROOT / relative_path / "pyproject.toml"
    with pyproject_path.open("rb") as pyproject_file:
        return tomllib.load(pyproject_file)["project"]


def test_people_api_internal_dependencies_match_owned_package_versions() -> None:
    """Reject stale internal distribution pins hidden by source-tree PYTHONPATH tests."""
    people_project = _project_metadata("services/people-api")
    declared_dependencies = set(people_project["dependencies"])

    expected_dependencies = set()
    for package_path in ("packages/hris-kernel", "packages/keyverse-adapter"):
        package_project = _project_metadata(package_path)
        expected_dependencies.add(
            f"{package_project['name']}=={package_project['version']}"
        )

    assert expected_dependencies <= declared_dependencies
