"""Reject built wheels whose metadata detaches declared owned dependencies."""

from __future__ import annotations

import importlib.util
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


def _write_wheel(
    wheelhouse: Path,
    *,
    filename: str,
    package_root: str,
    dist_info_root: str,
    metadata: str,
    include_py_typed: bool,
) -> None:
    """Create the smallest synthetic wheel needed to exercise artifact metadata checks."""
    wheel_path = wheelhouse / filename
    with zipfile.ZipFile(wheel_path, "w") as archive:
        archive.writestr(f"{package_root}/__init__.py", "")
        if include_py_typed:
            archive.writestr(f"{package_root}/py.typed", "")
        archive.writestr(f"{dist_info_root}/METADATA", metadata)


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
