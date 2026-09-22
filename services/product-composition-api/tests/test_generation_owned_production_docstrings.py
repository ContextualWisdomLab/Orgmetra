from __future__ import annotations

import ast
from pathlib import Path


_OWNED_PRODUCTION_MODULES = (
    "registry.py",
    "postgres_registry.py",
)


def test_owned_generation_production_functions_have_docstrings() -> None:
    """Keep every function in generation-owner production modules explicitly documented."""

    source_root = (
        Path(__file__).parents[1]
        / "src"
        / "orgmetra_product_composition"
    )
    missing: list[str] = []
    for module_name in _OWNED_PRODUCTION_MODULES:
        tree = ast.parse((source_root / module_name).read_text(encoding="utf-8"))
        missing.extend(
            f"{module_name}:{node.name}"
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and ast.get_docstring(node) is None
        )

    assert missing == []
