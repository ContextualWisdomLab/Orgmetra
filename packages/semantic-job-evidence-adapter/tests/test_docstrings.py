"""Executable documentation-completeness contract for semantic source evidence."""

from __future__ import annotations

import ast
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PACKAGE_ROOT / "src" / "orgmetra_semantic_job_evidence_adapter"
TEST_ROOT = PACKAGE_ROOT / "tests"


def _python_files() -> tuple[Path, ...]:
    """Return every owned Python source/test file recursively in deterministic order."""
    return tuple(sorted({*SOURCE_ROOT.rglob("*.py"), *TEST_ROOT.rglob("*.py")}))


def test_owned_python_modules_and_callables_are_documented() -> None:
    """Require beginner-readable docstrings on every owned module, class, and callable."""
    paths = _python_files()
    assert paths, f"No owned Python files discovered under {SOURCE_ROOT} or {TEST_ROOT}"
    missing: list[str] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if ast.get_docstring(tree, clean=False) is None:
            missing.append(f"{path.relative_to(PACKAGE_ROOT)}:<module>")
        for node in ast.walk(tree):
            if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if ast.get_docstring(node, clean=False) is None:
                missing.append(f"{path.relative_to(PACKAGE_ROOT)}:{node.lineno}:{node.name}")
    assert not missing, "Missing owned Python docstrings: " + ", ".join(missing)
