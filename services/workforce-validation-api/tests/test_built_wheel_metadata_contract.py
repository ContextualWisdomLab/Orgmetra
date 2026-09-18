"""Reject built wheels whose metadata or RECORD detaches reviewed artifact truth."""

from __future__ import annotations

import base64
import csv
import hashlib
import importlib.util
import io
from pathlib import Path
import zipfile

import pytest


_CONTRACT_PATH = Path(__file__).with_name("test_package_metadata_compatibility.py")
_SPEC = importlib.util.spec_from_file_location(
    "_workforce_package_metadata_contract",
    _CONTRACT_PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
_CONTRACT = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CONTRACT)


def _record_hash(content: bytes) -> str:
    """Return the wheel RECORD sha256 representation for one synthetic member."""
    digest = hashlib.sha256(content).digest()
    encoded = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return f"sha256={encoded}"


def _write_wheel(
    wheelhouse: Path,
    *,
    filename: str,
    package_root: str,
    dist_info_root: str,
    metadata: str,
    include_py_typed: bool,
    break_record_hash: bool = False,
) -> None:
    """Create a minimal internally recorded wheel for artifact-contract regressions."""
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
        member_hash = _record_hash(member)
        if break_record_hash and member_path == f"{package_root}/__init__.py":
            member_hash = "sha256=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        writer.writerow((member_path, member_hash, str(len(member))))
    writer.writerow((record_path, "", ""))
    members[record_path] = output.getvalue().encode("utf-8")

    wheel_path = wheelhouse / filename
    with zipfile.ZipFile(wheel_path, "w") as archive:
        for member_path, member in members.items():
            archive.writestr(member_path, member)


def test_hash_locked_acceptance_rejects_service_wheel_missing_keyverse_dependency(
    tmp_path: Path,
) -> None:
    """A directly locked Keyverse wheel must not mask missing service dependency metadata."""
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
            "Requires-Python: >=3.12\n\n"
        ),
        include_py_typed=False,
    )
    _write_wheel(
        wheelhouse,
        filename="orgmetra_workforce_validation_api-0.1.0-py3-none-any.whl",
        package_root="orgmetra_workforce_validation_api",
        dist_info_root="orgmetra_workforce_validation_api-0.1.0.dist-info",
        metadata=(
            "Metadata-Version: 2.4\n"
            "Name: orgmetra-workforce-validation-api\n"
            "Version: 0.1.0\n"
            "Requires-Python: >=3.12\n\n"
        ),
        include_py_typed=True,
    )

    with pytest.raises(AssertionError, match="mandatory Keyverse dependency"):
        _CONTRACT._locked_wheel_requirements(
            wheelhouse,
            service_version="0.1.0",
            keyverse_version="0.1.0",
        )


def test_hash_locked_acceptance_rejects_wheel_with_invalid_record_hash(
    tmp_path: Path,
) -> None:
    """A wheel SHA lock must not hide an internally false installation RECORD."""
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
            "Requires-Python: >=3.12\n\n"
        ),
        include_py_typed=False,
    )
    _write_wheel(
        wheelhouse,
        filename="orgmetra_workforce_validation_api-0.1.0-py3-none-any.whl",
        package_root="orgmetra_workforce_validation_api",
        dist_info_root="orgmetra_workforce_validation_api-0.1.0.dist-info",
        metadata=(
            "Metadata-Version: 2.4\n"
            "Name: orgmetra-workforce-validation-api\n"
            "Version: 0.1.0\n"
            "Requires-Python: >=3.12\n"
            "Requires-Dist: orgmetra-keyverse-adapter==0.1.0\n\n"
        ),
        include_py_typed=True,
        break_record_hash=True,
    )

    with pytest.raises(AssertionError, match="RECORD"):
        _CONTRACT._locked_wheel_requirements(
            wheelhouse,
            service_version="0.1.0",
            keyverse_version="0.1.0",
        )
