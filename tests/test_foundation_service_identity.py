"""Identity-collision regressions for Foundation service discovery."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import foundation_service_compatibility as MODULE


def _write_service(root: Path, relative_dir: str, *, name: str) -> None:
    """Create one minimal executable service distribution fixture."""
    service_dir = root / relative_dir
    (service_dir / "src").mkdir(parents=True)
    (service_dir / "tests").mkdir()
    (service_dir / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                f'name = "{name}"',
                'version = "1.0.0"',
                'requires-python = ">=3.11"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_service_discovery_rejects_duplicate_normalized_distribution_identity(
    tmp_path: Path,
) -> None:
    """Two service roots cannot claim one PyPA-normalized distribution identity."""
    _write_service(
        tmp_path,
        "services/first-api",
        name="orgmetra-sample-api",
    )
    _write_service(
        tmp_path,
        "services/second-api",
        name="Orgmetra_Sample.Api",
    )

    with pytest.raises(
        MODULE.ServiceCompatibilityError,
        match="duplicate owned service name after normalization",
    ):
        MODULE.discover_services(tmp_path)
