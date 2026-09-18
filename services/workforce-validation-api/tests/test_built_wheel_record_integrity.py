"""Verify that shipped owned wheels carry internally truthful installation RECORDs."""

from __future__ import annotations

import importlib.util
from importlib.metadata import version as installed_version
from pathlib import Path
import subprocess
import sys

from packaging.version import Version


_TEST_ROOT = Path(__file__).resolve().parent
_METADATA_PATH = _TEST_ROOT / "test_package_metadata_compatibility.py"
_RECORD_PATH = _TEST_ROOT / "test_built_wheel_metadata_contract.py"

_METADATA_SPEC = importlib.util.spec_from_file_location(
    "_workforce_package_metadata_contract_for_record",
    _METADATA_PATH,
)
assert _METADATA_SPEC is not None and _METADATA_SPEC.loader is not None
_METADATA_CONTRACT = importlib.util.module_from_spec(_METADATA_SPEC)
_METADATA_SPEC.loader.exec_module(_METADATA_CONTRACT)

_RECORD_SPEC = importlib.util.spec_from_file_location(
    "_workforce_built_wheel_record_contract",
    _RECORD_PATH,
)
assert _RECORD_SPEC is not None and _RECORD_SPEC.loader is not None
_RECORD_CONTRACT = importlib.util.module_from_spec(_RECORD_SPEC)
_RECORD_SPEC.loader.exec_module(_RECORD_CONTRACT)


def test_built_owned_wheels_have_complete_verified_records(tmp_path: Path) -> None:
    """Build the exact owned distributions and verify every installed member against RECORD."""
    backend_requirement = _METADATA_CONTRACT._service_build_backend_requirement()
    assert Version(installed_version("setuptools")) in backend_requirement.specifier, (
        "canonical test/build toolchain must install the exact reviewed setuptools backend"
    )

    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    environment = _METADATA_CONTRACT._subprocess_environment()
    for source_root in (
        _METADATA_CONTRACT._KEYVERSE_ROOT,
        _METADATA_CONTRACT._SERVICE_ROOT,
    ):
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
            cwd=_METADATA_CONTRACT._REPOSITORY_ROOT,
            env=environment,
            check=True,
        )

    wheel_paths = tuple(sorted(wheelhouse.iterdir()))
    assert len(wheel_paths) == 2, "RECORD acceptance must inspect both owned built wheels"
    for wheel_path in wheel_paths:
        _RECORD_CONTRACT._validate_wheel_record(wheel_path)
