"""Enforce a measurable documentation floor across owned Workforce Validation code.

CodeRabbit's PR-wide percentage is useful review signal but also counts test
helpers. This repository-native contract instead scans the production package
recursively and makes undocumented production definitions a hard CI failure.
The mechanical floor rejects blank and placeholder-sized docstrings; semantic
quality remains subject to code review so the metric cannot reward filler.
"""

from __future__ import annotations

import ast
from pathlib import Path
import re


_PACKAGE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "orgmetra_workforce_validation_api"
)
_MIN_DOCSTRING_CHARACTERS = 12
_MIN_DOCSTRING_WORDS = 2
_WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
_PLACEHOLDER_DOCSTRINGS = frozenset({"todo", "tbd", "fixme", "pass", "placeholder"})


def _is_substantive_docstring(node: ast.AST) -> bool:
    """Reject absent, blank, one-token, and placeholder-sized documentation."""
    docstring = ast.get_docstring(node, clean=False)
    if docstring is None:
        return False
    normalized = " ".join(docstring.split())
    if not normalized or normalized.casefold() in _PLACEHOLDER_DOCSTRINGS:
        return False
    return (
        len(normalized) >= _MIN_DOCSTRING_CHARACTERS
        and len(_WORD_PATTERN.findall(normalized)) >= _MIN_DOCSTRING_WORDS
    )


def _symbol_label(path: Path, node: ast.AST) -> str:
    """Return one stable repository-relative location for a documentation failure."""
    relative = path.relative_to(_PACKAGE_ROOT).as_posix()
    name = getattr(node, "name", "<module>")
    line = getattr(node, "lineno", 1)
    return f"{relative}:{line}:{name}"


def _collect_missing_docstrings(path: Path) -> list[str]:
    """Collect every production definition below the minimum documentation floor."""
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    missing: list[str] = []

    if not _is_substantive_docstring(module):
        missing.append(_symbol_label(path, module))

    for node in ast.walk(module):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and not (
            _is_substantive_docstring(node)
        ):
            missing.append(_symbol_label(path, node))
    return missing


def test_owned_production_definitions_have_substantive_docstrings() -> None:
    """Require the documentation floor for all recursively discovered production Python."""
    source_files = sorted(_PACKAGE_ROOT.rglob("*.py"))
    assert source_files, "workforce-validation production package must contain Python sources"

    missing = [
        symbol
        for source_file in source_files
        for symbol in _collect_missing_docstrings(source_file)
    ]
    assert not missing, "insufficient production docstrings:\n" + "\n".join(missing)
