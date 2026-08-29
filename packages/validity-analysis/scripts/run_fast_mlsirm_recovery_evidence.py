#!/usr/bin/env python3
"""Run a bounded pinned fast-mlsirm Rust recovery smoke and emit one receipt."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from orgmetra_validity_analysis.recovery_runner import main


if __name__ == "__main__":  # pragma: no cover
    try:
        sys.exit(main())
    except (RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
