"""Regression contracts for repository-owned database identifier validation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_postgresql_public_schema_is_not_treated_as_an_owned_identifier() -> None:
    """Accept PostgreSQL's external ``public`` schema while validating owned tables."""
    result = subprocess.run(
        [sys.executable, "tests/validate_repository.py"],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
