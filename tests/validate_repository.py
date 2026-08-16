#!/usr/bin/env python3
"""Validate the Orgmetra foundation pack structure, integrity, and contracts."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "manifest.json"
REQUIRED = [
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "ARCHITECTURE.md",
    "CHANGELOG.md",
    ".gitignore",
    "LICENSE",
    "NOTICE",
    "manifest.json",
    "package.json",
    ".github/workflows/foundation-ci.yml",
    "docs/PRD.md",
    "docs/TRD.md",
    "docs/USER_STORIES.md",
    "docs/STORYBOARD.md",
    "docs/WIREFRAMES.md",
    "docs/STORYBOOK.md",
    "docs/UML.md",
    "docs/ERD.md",
    "docs/DATA_MODEL.md",
    "docs/API_CONTRACT.md",
    "docs/SECURITY.md",
    "docs/THREAT_MODEL.md",
    "docs/TEST_STRATEGY.md",
    "docs/OPERABILITY.md",
    "docs/TRACEABILITY.md",
    "docs/adr/README.md",
    "docs/doctoring/REFERENCES.md",
    "docs/superpowers/specs/2026-08-15-orgmetra-foundation-design.md",
    "docs/superpowers/plans/2026-08-15-orgmetra-foundation-implementation-plan.md",
    "database/migrations/0001_foundation_schema.sql",
    "schemas/openapi.yaml",
    "scripts/foundation-contract-core.mjs",
    "scripts/foundation-contract.mjs",
    "tests/foundation-contract.test.mjs",
    "tests/validate_repository.py",
]


def _fail(message: str) -> None:
    """Stop validation with one operator-readable message."""
    raise SystemExit(message)


def _require_files() -> None:
    """Require every foundation artifact before inspecting its contents."""
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        _fail(f"Missing required files: {missing}")


def _line_count(data: bytes) -> int:
    """Count text lines using the same split-lines contract as the manifest."""
    return len(data.decode("utf-8").splitlines())


def _manifest_entries() -> dict[str, dict[str, Any]]:
    """Parse unique, relative manifest entries and reject self-reference."""
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        _fail(f"manifest.json is not readable JSON: {error}")

    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list):
        _fail("manifest.json must contain a files array")

    entries: dict[str, dict[str, Any]] = {}
    for raw_entry in manifest["files"]:
        if not isinstance(raw_entry, dict):
            _fail("manifest file entries must be objects")
        path_value = raw_entry.get("path")
        if not isinstance(path_value, str) or not path_value:
            _fail("manifest file path must be a non-empty string")
        relative = Path(path_value)
        if relative.is_absolute() or ".." in relative.parts or path_value != relative.as_posix():
            _fail(f"manifest path is not a safe normalized relative path: {path_value}")
        if path_value == "manifest.json":
            _fail("manifest.json must exclude itself to avoid recursive integrity data")
        if path_value in entries:
            _fail(f"duplicate manifest path: {path_value}")
        entries[path_value] = raw_entry
    return entries


def _validate_manifest() -> None:
    """Compare every manifest digest, byte count, and line count with disk."""
    entries = _manifest_entries()
    required_entries = set(REQUIRED) - {"manifest.json"}
    missing_entries = sorted(required_entries - set(entries))
    if missing_entries:
        _fail(f"required files missing from manifest: {missing_entries}")

    for relative_path, entry in sorted(entries.items()):
        path = ROOT / relative_path
        if not path.is_file():
            _fail(f"manifest path does not exist as a regular file: {relative_path}")
        data = path.read_bytes()
        expected = {
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
            "lines": _line_count(data),
        }
        for field_name, expected_value in expected.items():
            if entry.get(field_name) != expected_value:
                _fail(
                    f"manifest {field_name} mismatch for {relative_path}: "
                    f"expected {expected_value!r}, observed {entry.get(field_name)!r}"
                )


def _validate_database_contract() -> None:
    """Validate naming, temporal, evidence, and append-only DDL contracts."""
    sql = (
        ROOT / "database/migrations/0001_foundation_schema.sql"
    ).read_text(encoding="utf-8")

    table_pattern = re.compile(
        r"\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
        r"(?:(?P<schema>[a-z_][a-z0-9_]*)\.)?"
        r"(?P<table>[a-z_][a-z0-9_]*)",
        flags=re.IGNORECASE,
    )
    matches = list(table_pattern.finditer(sql))
    if not matches:
        _fail("No CREATE TABLE statement found")

    for match in matches:
        for identifier in filter(None, (match.group("schema"), match.group("table"))):
            if "_" not in identifier or identifier != identifier.lower():
                _fail(
                    "Database object name is not two-word lowercase snake_case: "
                    f"{identifier}"
                )

    non_empty_period_guards = [
        "effective_to IS NULL OR effective_to > effective_from",
        "recorded_to IS NULL OR recorded_to > recorded_from",
    ]
    for guard in non_empty_period_guards:
        if guard not in sql:
            _fail(f"Missing strict temporal interval guard: {guard}")

    required_fragments = [
        "CREATE EXTENSION IF NOT EXISTS btree_gist",
        "CREATE TABLE person_name_record",
        "CONSTRAINT person_name_bitemporal_exclusion",
        "daterange(effective_from, effective_to, '[)') WITH &&",
        "tstzrange(recorded_from, recorded_to, '[)') WITH &&",
        "CREATE TABLE organization_unit_version",
        "organization_unit_id uuid NOT NULL REFERENCES organization_unit(organization_unit_id)",
        "parent_organization_unit_id uuid REFERENCES organization_unit(organization_unit_id)",
        "organization_type_code text NOT NULL",
        "CONSTRAINT organization_unit_parent_not_self_check",
        "CONSTRAINT organization_unit_bitemporal_exclusion",
        "CREATE TABLE job_profile_version",
        "job_profile_id uuid NOT NULL REFERENCES job_profile(job_profile_id)",
        "job_family_code text NOT NULL",
        "job_version_code text NOT NULL",
        "CONSTRAINT job_profile_bitemporal_exclusion",
        "CREATE FUNCTION protect_bitemporal_history",
        "to_jsonb(NEW) - 'recorded_to' <> to_jsonb(OLD) - 'recorded_to'",
        "CREATE TRIGGER person_name_bitemporal_guard",
        "CREATE TRIGGER organization_unit_bitemporal_guard",
        "CREATE TRIGGER job_profile_bitemporal_guard",
        "CREATE TABLE performance_cycle",
        "performance_cycle_id uuid NOT NULL REFERENCES performance_cycle(performance_cycle_id)",
        "CONSTRAINT performance_cycle_effective_period_check",
        "CONSTRAINT performance_cycle_recorded_period_check",
        "CREATE TABLE selection_decision_evidence",
        "CREATE FUNCTION reject_append_only_mutation",
        "CREATE TRIGGER candidate_worker_link_append_only_guard",
        "CREATE TRIGGER selection_decision_append_only_guard",
        "CREATE TRIGGER selection_decision_evidence_append_only_guard",
        "BEFORE UPDATE OR DELETE ON candidate_worker_link",
        "BEFORE UPDATE OR DELETE ON selection_decision_evidence",
    ]
    for fragment in required_fragments:
        if fragment not in sql:
            _fail(f"Missing database contract fragment: {fragment}")


def _validate_openapi_contract() -> None:
    """Require authentication and complete mutation context in the API schema."""
    openapi = (ROOT / "schemas/openapi.yaml").read_text(encoding="utf-8")
    required_fragments = [
        "openapi: 3.2.0",
        "securitySchemes:",
        "type: openIdConnect",
        "security:",
        "name: Idempotency-Key",
        "name: X-Tenant-Reference",
        "name: X-Actor-Reference",
        "name: X-Purpose-Code",
        "CreatedJobProfile:",
        "job_profile_id:",
        "RecordSelectionDecisionCommand:",
        "confirmation_reference",
        "evidence_references:",
        "minItems: 1",
        "maxItems: 100",
        "- orgmetra.people.write",
        "- orgmetra.job_architecture.write",
        "- orgmetra.talent_acquisition.write",
        "next_action:",
        "support_reference:",
        "Opaque random client-safe support identifier.",
    ]
    for fragment in required_fragments:
        if fragment not in openapi:
            _fail(f"Missing OpenAPI contract fragment: {fragment}")

    if "keyverse_oidc: []" in openapi:
        _fail("OpenID Connect security requirements must declare a least-privilege scope")

    if re.search(r"(?m)^\s*(?:-\s+)?trace_id\s*:", openapi):
        _fail("Client error schemas must not expose internal trace identifiers")

    if re.search(r"(?m)^ {8,}-\s+name:\s+(?:people-core|job-architecture|talent-acquisition)\s*$", openapi):
        _fail("Operation tags must be string values, not tag objects")


def _validate_markdown() -> None:
    """Reject unfinished markers and malformed Markdown fences."""
    forbidden_tokens = ("tbd", "todo", "placeholder")
    for path in ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for token in forbidden_tokens:
            if token in lowered:
                _fail(f"Unfinished marker {token!r} found in {path}")
        if text.count("```") % 2:
            _fail(f"Unbalanced code fence in {path}")


def _validate_license() -> None:
    """Require the complete Apache License 2.0 grant text."""
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    if (
        "Apache License" not in license_text
        or "END OF TERMS AND CONDITIONS" not in license_text
    ):
        _fail("LICENSE is not the complete Apache License 2.0 text")


def main() -> None:
    """Run every foundation-pack validation gate."""
    _require_files()
    _validate_manifest()
    _validate_database_contract()
    _validate_openapi_contract()
    _validate_markdown()
    _validate_license()
    print("Orgmetra foundation pack validation passed")


if __name__ == "__main__":
    main()
