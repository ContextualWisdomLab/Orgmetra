#!/usr/bin/env python3
"""Fail when a public Orgmetra domain symbol lacks a beginner-readable docstring."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "packages" / "orgmetra-domain" / "src" / "orgmetra_domain"
missing: list[str] = []

for path in sorted(SOURCE_ROOT.glob("*.py")):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    if not ast.get_docstring(tree):
        missing.append(f"{path}: module")
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            if not ast.get_docstring(node):
                missing.append(f"{path}:{node.lineno} {node.name}")
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if child.name.startswith("_") and child.name not in {
                        "__init__",
                        "__post_init__",
                    }:
                        continue
                    if not ast.get_docstring(child):
                        missing.append(f"{path}:{child.lineno} {node.name}.{child.name}")

if missing:
    raise SystemExit("Missing docstrings:\n" + "\n".join(missing))

print("Orgmetra public docstring validation passed")
