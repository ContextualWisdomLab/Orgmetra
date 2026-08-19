"""Executable documentation-quality contract for the structured-interview package."""

from __future__ import annotations

import ast
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOTS = (PACKAGE_ROOT / "src", PACKAGE_ROOT / "tests")


def _undocumented_definitions(path: Path) -> list[str]:
    """Return module/class/callable names that lack a beginner-readable docstring."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    missing: list[str] = []
    if ast.get_docstring(tree) is None:
        missing.append(f"{path}:<module>")
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if ast.get_docstring(node) is None:
                missing.append(f"{path}:{node.name}")
    return missing


def test_owned_python_definitions_have_docstrings() -> None:
    """Require readable docstrings across every owned production and regression definition."""
    missing: list[str] = []
    for root in PYTHON_ROOTS:
        for path in sorted(root.rglob("*.py")):
            missing.extend(_undocumented_definitions(path))
    assert not missing, "Missing docstrings:\n" + "\n".join(missing)
