"""Repository-manifest metadata must describe target truth without fake provenance."""

from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_manifest_names_the_canonical_target_branch_without_fake_generation_provenance() -> None:
    """Static integrity metadata must not claim the checked-out PR head was generated on another branch."""
    manifest = json.loads((REPOSITORY_ROOT / "manifest.json").read_text(encoding="utf-8"))

    assert manifest.get("canonical_target_branch") == "develop"
    assert "generated_for_branch" not in manifest
