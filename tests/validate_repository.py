#!/usr/bin/env python3
"""Validate the Orgmetra foundation pack structure and naming contracts."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md", "AGENTS.md", "CLAUDE.md", "ARCHITECTURE.md", "CHANGELOG.md", ".gitignore", "LICENSE", "NOTICE",
    "docs/PRD.md", "docs/TRD.md", "docs/USER_STORIES.md", "docs/STORYBOARD.md",
    "docs/WIREFRAMES.md", "docs/STORYBOOK.md", "docs/UML.md", "docs/ERD.md",
    "docs/DATA_MODEL.md", "docs/API_CONTRACT.md", "docs/SECURITY.md",
    "docs/THREAT_MODEL.md", "docs/TEST_STRATEGY.md", "docs/OPERABILITY.md",
    "docs/TRACEABILITY.md", "docs/adr/README.md", "docs/doctoring/REFERENCES.md",
    "database/migrations/0001_foundation_schema.sql", "schemas/openapi.yaml",
]

missing = [p for p in REQUIRED if not (ROOT / p).exists()]
if missing:
    raise SystemExit(f"Missing required files: {missing}")

sql = (ROOT / "database/migrations/0001_foundation_schema.sql").read_text(encoding="utf-8")
for match in re.finditer(r"CREATE TABLE\s+([a-z_]+)", sql):
    name = match.group(1)
    if "_" not in name:
        raise SystemExit(f"Database table name is not two-word snake_case: {name}")

for path in ROOT.rglob("*.md"):
    text = path.read_text(encoding="utf-8")
    lowered = text.lower()
    if "tbd" in lowered or "todo" in lowered or "placeholder" in lowered:
        raise SystemExit(f"Placeholder token found in {path}")
    if text.count("```") % 2:
        raise SystemExit(f"Unbalanced code fence in {path}")

print("Orgmetra foundation pack validation passed")

license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
if "Apache License" not in license_text or "END OF TERMS AND CONDITIONS" not in license_text:
    raise SystemExit("LICENSE is not the complete Apache License 2.0 text")
