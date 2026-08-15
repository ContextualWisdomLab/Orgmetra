"""Fail when a shipped public Python symbol lacks a useful docstring."""

from __future__ import annotations

import ast
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src" / "orgmetra_postgres"


def _public_name(name: str) -> bool:
    """Return whether a symbol belongs to the public documentation surface."""

    return not name.startswith("_")


def _missing_docstrings(path: Path) -> list[str]:
    """Return public symbols without non-empty docstrings in one source file."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    missing: list[str] = []
    if not ast.get_docstring(tree):
        missing.append(f"{path}: module")
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if _public_name(node.name) and not ast.get_docstring(node):
                missing.append(f"{path}:{node.lineno} {node.name}")
    return missing


def main() -> int:
    """Print missing public docstrings and return a shell-compatible status."""

    missing = [
        item
        for path in sorted(PACKAGE_ROOT.glob("*.py"))
        for item in _missing_docstrings(path)
    ]
    if missing:
        print("Missing public docstrings:")
        print("\n".join(missing))
        return 1
    print("Public docstring coverage: 100%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
