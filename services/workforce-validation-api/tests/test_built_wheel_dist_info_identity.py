"""Reject wheels whose dist-info directory does not match the built distribution identity."""

from __future__ import annotations

import csv
import importlib.util
import io
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile

from packaging.utils import canonicalize_name, parse_wheel_filename
import pytest


_CONTRACT_PATH = Path(__file__).with_name("test_package_metadata_compatibility.py")
_SPEC = importlib.util.spec_from_file_location(
    "_workforce_package_metadata_contract_dist_info",
    _CONTRACT_PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
_CONTRACT = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CONTRACT)


def _write_wheel(
    wheelhouse: Path,
    *,
    filename: str,
    package_root: str,
    dist_info_root: str,
    metadata: str,
    include_py_typed: bool,
) -> None:
    """Create one internally self-consistent wheel with a selectable dist-info root."""
    members: dict[str, bytes] = {
        f"{package_root}/__init__.py": b"",
        f"{dist_info_root}/METADATA": metadata.encode("utf-8"),
        f"{dist_info_root}/WHEEL": (
            "Wheel-Version: 1.0\n"
            "Generator: orgmetra-test-fixture\n"
            "Root-Is-Purelib: true\n"
            "Tag: py3-none-any\n\n"
        ).encode("utf-8"),
    }
    if include_py_typed:
        members[f"{package_root}/py.typed"] = b""

    record_path = f"{dist_info_root}/RECORD"
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    for member_path in sorted(members):
        member = members[member_path]
        writer.writerow((member_path, _CONTRACT._record_hash(member), str(len(member))))
    writer.writerow((record_path, "", ""))
    members[record_path] = output.getvalue().encode("utf-8")

    with zipfile.ZipFile(wheelhouse / filename, "w") as archive:
        for member_path, content in members.items():
            archive.writestr(member_path, content)


def _assert_dist_info_identity(wheel_path: Path) -> None:
    """Bind the sole dist-info root to the normalized wheel filename name and version."""
    parsed_name, parsed_version, _build, _tags = parse_wheel_filename(wheel_path.name)
    expected_root = (
        f"{canonicalize_name(parsed_name).replace('-', '_')}-{parsed_version}.dist-info"
    )
    with zipfile.ZipFile(wheel_path) as archive:
        roots = {
            PurePosixPath(name).parts[0]
            for name in archive.namelist()
            if PurePosixPath(name).parts
            and PurePosixPath(name).parts[0].endswith(".dist-info")
        }
    assert roots == {expected_root}, (
        f"{wheel_path.name} dist-info identity must be {expected_root}, observed {sorted(roots)}"
    )


def _validate_distribution_acceptance(
    wheelhouse: Path,
    *,
    service_version: str,
    keyverse_version: str,
) -> tuple[str, dict[str, Path]]:
    """Run the existing wheel lock contract plus exact dist-info directory identity binding."""
    locked_requirements, wheels_by_name = _CONTRACT._locked_wheel_requirements(
        wheelhouse,
        service_version=service_version,
        keyverse_version=keyverse_version,
    )
    for wheel_path in wheels_by_name.values():
        _assert_dist_info_identity(wheel_path)
    return locked_requirements, wheels_by_name


def test_hash_locked_acceptance_rejects_mismatched_dist_info_identity(tmp_path: Path) -> None:
    """A correct filename and METADATA must not hide a foreign dist-info directory identity."""
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    _write_wheel(
        wheelhouse,
        filename="orgmetra_keyverse_adapter-0.1.0-py3-none-any.whl",
        package_root="orgmetra_keyverse_adapter",
        dist_info_root="orgmetra_keyverse_adapter-0.1.0.dist-info",
        metadata=(
            "Metadata-Version: 2.4\n"
            "Name: orgmetra-keyverse-adapter\n"
            "Version: 0.1.0\n"
            "Requires-Python: >=3.12\n"
            "Provides-Extra: test\n"
            "Requires-Dist: pytest>=8.3; extra == 'test'\n"
            "Requires-Dist: pytest-cov>=5.0; extra == 'test'\n\n"
        ),
        include_py_typed=False,
    )
    _write_wheel(
        wheelhouse,
        filename="orgmetra_workforce_validation_api-0.1.0-py3-none-any.whl",
        package_root="orgmetra_workforce_validation_api",
        dist_info_root="foreign_distribution-0.1.0.dist-info",
        metadata=(
            "Metadata-Version: 2.4\n"
            "Name: orgmetra-workforce-validation-api\n"
            "Version: 0.1.0\n"
            "Requires-Python: >=3.12\n"
            "Requires-Dist: orgmetra-keyverse-adapter==0.1.0\n\n"
        ),
        include_py_typed=True,
    )

    with pytest.raises(AssertionError, match="dist-info identity"):
        _validate_distribution_acceptance(
            wheelhouse,
            service_version="0.1.0",
            keyverse_version="0.1.0",
        )


def test_built_owned_wheels_bind_dist_info_to_filename_identity(tmp_path: Path) -> None:
    """Prove the exact wheels built from reviewed owned sources satisfy the identity binding."""
    service_project = _CONTRACT._project_metadata(_CONTRACT._SERVICE_ROOT / "pyproject.toml")
    service_version = service_project.get("version")
    assert isinstance(service_version, str), "service project version must be text"
    keyverse_project = _CONTRACT._project_metadata(_CONTRACT._KEYVERSE_PROJECT)
    keyverse_version = keyverse_project.get("version")
    assert isinstance(keyverse_version, str), "Keyverse project version must be text"

    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    environment = _CONTRACT._subprocess_environment()
    for source_root in (_CONTRACT._KEYVERSE_ROOT, _CONTRACT._SERVICE_ROOT):
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
            cwd=_CONTRACT._REPOSITORY_ROOT,
            env=environment,
            check=True,
        )

    _locked_requirements, wheels_by_name = _validate_distribution_acceptance(
        wheelhouse,
        service_version=service_version,
        keyverse_version=keyverse_version,
    )
    assert set(wheels_by_name) == {
        canonicalize_name(_CONTRACT._KEYVERSE_NAME),
        canonicalize_name(_CONTRACT._SERVICE_NAME),
    }
