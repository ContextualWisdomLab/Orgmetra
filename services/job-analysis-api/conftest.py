"""Make sibling Orgmetra workspace packages importable for this service's tests.

The service depends on sibling workspace packages (for example
``orgmetra_hris_kernel``). Hosted quality workflows install those dependencies
into isolated environments, but plain ``pytest`` sessions started inside this
service directory (such as the central coverage sandbox) do not perform a
workspace install. This conftest adds every workspace ``src`` tree to the
import path so test collection succeeds without changing production behavior.
"""

from __future__ import annotations

from pathlib import Path
import sys

_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]

for _source_dir in sorted(
    str(path)
    for pattern in ("packages/*/src", "services/*/src")
    for path in _WORKSPACE_ROOT.glob(pattern)
    if path.is_dir()
):
    if _source_dir not in sys.path:
        sys.path.insert(0, _source_dir)
