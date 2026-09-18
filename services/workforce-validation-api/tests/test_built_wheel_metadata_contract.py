"""Reject built wheels whose metadata or RECORD detaches reviewed artifact truth."""

from __future__ import annotations

import base64
import csv
import hashlib
import importlib.util
import io
from pathlib import Path, PurePosixPath
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
    """Return the wheel RECORD sha256 representation for one member."""
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
    """Require one complete sha256 RECORD that exactly covers installed wheel members."""
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

    for wheel_path in wheelhouse.iterdir():
        _validate_wheel_record(wheel_path)
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

    service_wheel = wheelhouse / "orgmetra_workforce_validation_api-0.1.0-py3-none-any.whl"
    with pytest.raises(AssertionError, match="RECORD sha256 mismatch"):
        _validate_wheel_record(service_wheel)


def test_record_rejects_normalization_alias_member_paths(tmp_path: Path) -> None:
    """Raw-distinct ZIP paths that normalize to one install path must fail closed."""
    wheel_path = tmp_path / "alias-0.1.0-py3-none-any.whl"
    members = {
        "alias/__init__.py": b"canonical",
        "./alias/__init__.py": b"ambiguous",
    }
    record_path = "alias-0.1.0.dist-info/RECORD"
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    for member_path, content in members.items():
        writer.writerow((member_path, _record_hash(content), str(len(content))))
    writer.writerow((record_path, "", ""))

    with zipfile.ZipFile(wheel_path, "w") as archive:
        for member_path, content in members.items():
            archive.writestr(member_path, content)
        archive.writestr(record_path, output.getvalue().encode("utf-8"))

    with pytest.raises(AssertionError, match="non-canonical"):
        _validate_wheel_record(wheel_path)
