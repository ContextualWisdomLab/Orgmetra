from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys


def test_request_routing_imports_on_declared_python_runtime() -> None:
    """Keep the routing error hierarchy importable on every declared Python runtime."""

    service_root = Path(__file__).resolve().parents[1]
    source_root = service_root / "src"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(source_root)

    completed = subprocess.run(
        [sys.executable, "-c", "import orgmetra_product_composition.request_routing"],
        cwd=service_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
