"""Reject wheels whose dist-info directory does not match the built distribution identity."""

from __future__ import annotations

import csv
import importlib.util
import io
from pathlib import Path
import zipfile

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


def test_hash_locked_acceptance_rejects_mismatched_dist_info_identity(tmp_path: Path) -> None:
    """The shared hash-lock helper must reject a foreign dist-info directory before hashing."""
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
        _CONTRACT._locked_wheel_requirements(
            wheelhouse,
            service_version="0.1.0",
            keyverse_version="0.1.0",
        )
