"""Documentation quality contract for the Keyverse identity lifecycle adapter."""

import ast
from pathlib import Path


def test_owned_python_definitions_have_docstrings() -> None:
    """Require beginner-readable docstrings for every owned Python definition."""
    root = Path(__file__).parents[1]
    missing: list[str] = []
    for path in sorted((root / "src").rglob("*.py")) + sorted((root / "tests").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if ast.get_docstring(node) is None:
                    name = getattr(node, "name", "<module>")
                    missing.append(f"{path.relative_to(root)}:{getattr(node, 'lineno', 1)}:{name}")
    assert missing == []
