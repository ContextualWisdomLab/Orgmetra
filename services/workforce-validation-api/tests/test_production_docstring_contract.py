"""Verify substantive docstrings across the owned Workforce Validation production surface.

CodeRabbit's PR-wide percentage also counts test helpers, so it is useful review
signal but not a precise measure of the commercial requirement for owned
production code. This contract scans the package itself and makes missing module,
class, function, method, property, protocol, and resolver documentation a hard CI
failure instead of an advisory review percentage.
"""

from __future__ import annotations

import ast
from pathlib import Path


_PACKAGE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "orgmetra_workforce_validation_api"
)


def _qualified_name(path: Path, parents: tuple[str, ...], name: str) -> str:
    """Return one repository-relative Python symbol name for a docstring failure."""
    module_name = path.relative_to(_PACKAGE_ROOT).with_suffix("").as_posix().replace("/", ".")
    scope = ".".join((*parents, name))
    return f"{module_name}:{scope}" if scope else module_name


def _collect_missing_docstrings(path: Path) -> list[str]:
    """Collect production definitions whose first statement is not a non-empty docstring."""
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    missing: list[str] = []

    if not ast.get_docstring(module, clean=False):
        missing.append(f"{path.relative_to(_PACKAGE_ROOT)}:<module>")

    def visit(body: list[ast.stmt], parents: tuple[str, ...]) -> None:
        """Walk lexical definitions while preserving readable ownership-qualified names."""
        for node in body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if not ast.get_docstring(node, clean=False):
                    missing.append(_qualified_name(path, parents, node.name))
                visit(node.body, (*parents, node.name))

    visit(module.body, ())
    return missing


def test_owned_production_definitions_have_docstrings() -> None:
    """Require 100% docstrings for every owned Python production definition."""
    source_files = sorted(_PACKAGE_ROOT.glob("*.py"))
    assert source_files, "workforce-validation production package must contain Python sources"

    missing = [
        symbol
        for source_file in source_files
        for symbol in _collect_missing_docstrings(source_file)
    ]
    assert not missing, "missing production docstrings:\n" + "\n".join(missing)
