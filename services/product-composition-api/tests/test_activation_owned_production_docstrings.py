from __future__ import annotations

import ast
from pathlib import Path


_OWNED_PRODUCTION_MODULES = (
    "activation.py",
    "activation_authorization.py",
    "activation_runtime_integrity.py",
    "route_availability.py",
    "serving_snapshot.py",
)


def test_owned_activation_production_functions_have_docstrings() -> None:
    """Keep every function in the activation-owner production modules explicitly documented."""

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
