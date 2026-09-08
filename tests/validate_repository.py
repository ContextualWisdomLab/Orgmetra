#!/usr/bin/env python3
"""Validate the Orgmetra foundation pack structure, integrity, and contracts."""

from __future__ import annotations

import hashlib
import json
import re
import sys
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
    "docs/adr/0001-orgmetra-authoritative-hris-record.md",
    "docs/adr/0002-federated-cwl-integration-boundaries.md",
    "docs/adr/0003-bitemporal-hris-data-contract.md",
    "docs/adr/0004-employment-position-version-and-assignment-binding.md",
    "docs/adr/0005-exclusive-employment-and-staffable-seats.md",
    "docs/adr/0006-governed-audit-outbox-envelope.md",
    "docs/adr/0007-governed-job-analysis-evidence.md",
    "docs/adr/0008-purpose-bound-pii-authorization.md",
    "docs/adr/0009-performance-criterion-observation-scope.md",
    "docs/adr/0010-naruon-calendar-intent-boundary.md",
    "docs/adr/0011-bitemporal-workforce-composition.md",
    "docs/adr/0012-governed-migration-handoff.md",
    "docs/adr/0013-governed-requisition-review-packet.md",
    "docs/adr/0014-job-analysis-snapshot-persistence.md",
    "docs/doctoring/REFERENCES.md",
    "docs/superpowers/specs/2026-08-15-orgmetra-foundation-design.md",
    "docs/superpowers/plans/2026-08-15-orgmetra-foundation-implementation-plan.md",
    "database/migrations/0001_foundation_schema.sql",
    "database/migrations/0002_sealed_evidence_digest.sql",
    "database/migrations/0003_audit_outbox_persistence.sql",
    "database/migrations/0004_outbox_delivery_claim.sql",
    "database/migrations/0005_outbox_delivery_finalization.sql",
    "database/migrations/0006_outbox_delivery_dead_letter.sql",
    "database/migrations/0007_outbox_retry_exhaustion.sql",
    "database/migrations/0008_audit_outbox_review_hardening.sql",
    "database/migrations/0009_candidate_worker_conversion_governance.sql",
    "database/migrations/0010_validity_study_case_integrity.sql",
    "database/migrations/0011_criterion_observation_scope.sql",
    "database/migrations/0012_people_mutation_idempotency.sql",
    "database/migrations/0013_job_analysis_snapshot.sql",
    "packages/hris-kernel/src/orgmetra_hris_kernel/audit.py",
    "packages/hris-kernel/tests/test_audit_outbox.py",
    "schemas/openapi.yaml",
    "scripts/foundation-contract-core.mjs",
    "scripts/foundation-contract.mjs",
    "tests/dispatcher-inventory.test.mjs",
    "tests/foundation-contract.test.mjs",
    "tests/openapi-contract.test.mjs",
    "tests/test_bitemporal_postgres.sh",
    "tests/test_tenant_isolation_postgres.sh",
    "tests/test_evidence_sealing_postgres.sh",
    "tests/test_operational_uuid_postgres.sh",
    "tests/test_audit_outbox_postgres.sh",
    "tests/test_outbox_claim_postgres.sh",
    "tests/test_outbox_dead_letter_postgres.sh",
    "tests/test_audit_outbox_hardening_postgres.sh",
    "tests/test_candidate_worker_conversion_postgres.sh",
    "tests/test_validity_study_case_postgres.sh",
    "tests/test_criterion_observation_scope_postgres.sh",
    "tests/test_people_mutation_idempotency_postgres.sh",
    "tests/test_job_analysis_snapshot_postgres.sh",
    "tests/validate_repository.py",
]

UNFINISHED_MARKER_LINE_PATTERN = re.compile(
    r"^\s*(?:#{1,6}\s+|[-*+]\s+)?"
    r"(?:\[(?:TODO|TBD|FIXME)\]|\{\{(?:TODO|TBD|FIXME)\}\}|"
    r"<(?:TODO|TBD|FIXME)>|(?:TODO|TBD|FIXME)(?:\s*:\s*.*)?\s*)$",
    flags=re.IGNORECASE,
)


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


def _expected_manifest_document() -> dict[str, Any]:
    """Build deterministic provenance for the exact active branch artifact set."""
    files = []
    for relative_path in sorted(set(REQUIRED) - {"manifest.json"}):
        path = ROOT / relative_path
        if not path.is_file():
            _fail(f"cannot build manifest; required file is missing: {relative_path}")
        data = path.read_bytes()
        files.append(
            {
                "path": relative_path,
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
                "lines": _line_count(data),
            }
        )
    return {
        "package": "orgmetra-foundation-pack",
        "version": "0.1.0",
        "generated_for_branch": "feat/audit-outbox-envelope",
        "files": files,
    }


def _manifest_entries() -> dict[str, dict[str, Any]]:
    """Parse unique, relative manifest entries and reject self-reference."""
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        _fail(f"manifest.json is not readable JSON: {error}")

    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list):
        _fail("manifest.json must contain a files array")
    if manifest.get("generated_for_branch") != "feat/audit-outbox-envelope":
        _fail(
            "manifest generated_for_branch must identify the active generation branch "
            "feat/audit-outbox-envelope"
        )

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
    expected_document = _expected_manifest_document()
    expected_entries = {entry["path"]: entry for entry in expected_document["files"]}
    missing_entries = sorted(set(expected_entries) - set(entries))
    extra_entries = sorted(set(entries) - set(expected_entries))
    if missing_entries or extra_entries:
        _fail(
            "manifest path set mismatch: "
            f"missing={missing_entries}, extra={extra_entries}. "
            "Run `python tests/validate_repository.py --print-manifest` for exact repair data."
        )

    for relative_path, expected in expected_entries.items():
        observed = entries[relative_path]
        for field_name in ("sha256", "bytes", "lines"):
            if observed.get(field_name) != expected[field_name]:
                _fail(
                    f"manifest {field_name} mismatch for {relative_path}: "
                    f"expected {expected[field_name]!r}, observed {observed.get(field_name)!r}. "
                    "Run `python tests/validate_repository.py --print-manifest` for exact repair data."
                )


def _validate_database_contract() -> None:
    """Validate naming, temporal, tenant, audit, evidence, and append-only DDL contracts."""
    migration_paths = sorted((ROOT / "database/migrations").glob("*.sql"))
    if not migration_paths:
        _fail("No database migrations found")
    migration_prefixes = [path.name.split("_", 1)[0] for path in migration_paths]
    duplicate_prefixes = sorted(
        prefix for prefix in set(migration_prefixes) if migration_prefixes.count(prefix) > 1
    )
    if duplicate_prefixes:
        _fail(f"Duplicate migration number prefixes: {duplicate_prefixes}")
    sql = "\n".join(path.read_text(encoding="utf-8") for path in migration_paths)
    table_sql = sql

    table_pattern = re.compile(
        r"\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
        r"(?:(?P<schema>[a-z_][a-z0-9_]*)\.)?"
        r"(?P<table>[a-z_][a-z0-9_]*)",
        flags=re.IGNORECASE,
    )
    matches = list(table_pattern.finditer(table_sql))
    if not matches:
        _fail("No CREATE TABLE statement found")

    for match in matches:
        for identifier in filter(None, (match.group("schema"), match.group("table"))):
            if "_" not in identifier or identifier != identifier.lower():
                _fail(
                    "Database object name is not two-word lowercase snake_case: "
                    f"{identifier}"
                )

    for guard in (
        "effective_to IS NULL OR effective_to > effective_from",
        "recorded_to IS NULL OR recorded_to > recorded_from",
    ):
        if guard not in sql:
            _fail(f"Missing strict temporal interval guard: {guard}")

    required_fragments = [
        "CREATE EXTENSION IF NOT EXISTS btree_gist",
        "CREATE EXTENSION IF NOT EXISTS pgcrypto",
        "CREATE TABLE tenant_record",
        "tenant_record_id uuid NOT NULL REFERENCES tenant_record(tenant_record_id)",
        "CREATE TABLE person_name_record",
        "FOREIGN KEY (tenant_record_id, person_record_id)",
        "REFERENCES person_record(tenant_record_id, person_record_id)",
        "CONSTRAINT person_name_bitemporal_exclusion",
        "daterange(effective_from, effective_to, '[)') WITH &&",
        "tstzrange(recorded_from, recorded_to, '[)') WITH &&",
        "CREATE TABLE organization_unit_version",
        "CONSTRAINT organization_unit_parent_not_self_check",
        "CONSTRAINT organization_unit_bitemporal_exclusion",
        "CREATE TABLE job_profile_version",
        "job_family_code text NOT NULL",
        "job_version_code text NOT NULL",
        "CONSTRAINT job_profile_bitemporal_exclusion",
        "CREATE TABLE employment_record_version",
        "CONSTRAINT employment_record_bitemporal_exclusion",
        "CONSTRAINT employment_record_tenant_person_unique",
        "CREATE TABLE position_record_version",
        "CONSTRAINT position_record_bitemporal_exclusion",
        "CONSTRAINT assignment_employment_person_tenant_fk",
        "CREATE TRIGGER employment_record_version_bitemporal_guard",
        "CREATE TRIGGER position_record_version_bitemporal_guard",
        "CREATE FUNCTION protect_bitemporal_history",
        "to_jsonb(NEW) - 'recorded_to' <> to_jsonb(OLD) - 'recorded_to'",
        "CREATE TRIGGER person_record_bitemporal_guard",
        "CREATE TRIGGER person_name_bitemporal_guard",
        "CREATE TRIGGER employment_record_bitemporal_guard",
        "CREATE TRIGGER organization_unit_anchor_bitemporal_guard",
        "CREATE TRIGGER organization_unit_bitemporal_guard",
        "CREATE TRIGGER job_profile_anchor_bitemporal_guard",
        "CREATE TRIGGER job_profile_bitemporal_guard",
        "CREATE TRIGGER position_record_bitemporal_guard",
        "CREATE TRIGGER assignment_record_bitemporal_guard",
        "CREATE TRIGGER candidate_profile_bitemporal_guard",
        "CREATE TRIGGER performance_cycle_bitemporal_guard",
        "CREATE TRIGGER criterion_blueprint_bitemporal_guard",
        "CREATE TRIGGER criterion_observation_bitemporal_guard",
        "CREATE TRIGGER validity_study_bitemporal_guard",
        "CREATE TRIGGER compensation_record_bitemporal_guard",
        "CREATE TRIGGER employment_transition_bitemporal_guard",
        "CREATE TABLE decision_evidence_set",
        "evidence_set_digest text NOT NULL",
        "ALTER COLUMN evidence_set_digest DROP NOT NULL",
        "CONSTRAINT decision_evidence_seal_state_check",
        "CONSTRAINT selection_decision_evidence_set_unique",
        "CREATE FUNCTION protect_evidence_set_seal",
        "CREATE FUNCTION reject_sealed_evidence_insert",
        "sealed evidence set cannot accept new members",
        "CREATE FUNCTION seal_decision_evidence_set",
        "locked_evidence_set_id uuid",
        "decision evidence set must contain at least one member before finalization",
        "jsonb_agg(",
        "CREATE FUNCTION validate_evidence_set_decision_binding",
        "CREATE CONSTRAINT TRIGGER decision_evidence_set_binding_guard",
        "CREATE TRIGGER selection_decision_seal_evidence_guard",
        "CREATE TABLE validity_study_decision_link",
        "CREATE TABLE validity_study_outcome_link",
        "CREATE TABLE validity_study_evidence_set_link",
        "CREATE TABLE validity_study_case_record",
        "CREATE FUNCTION public.validate_validity_study_case",
        "CREATE FUNCTION public.reject_legacy_validity_study_link_insert",
        "CREATE TRIGGER validity_study_case_truncate_guard",
        "CREATE POLICY validity_study_case_scope_policy",
        "CREATE FUNCTION current_tenant_record_id",
        "FORCE ROW LEVEL SECURITY",
        "CREATE POLICY person_record_scope_policy",
        "CREATE POLICY selection_decision_scope_policy",
        "CREATE FUNCTION reject_append_only_mutation",
        "CREATE TRIGGER candidate_worker_link_append_only_guard",
        "CREATE TRIGGER selection_decision_append_only_guard",
        "CREATE TRIGGER selection_decision_evidence_append_only_guard",
        "CREATE FUNCTION validate_audit_event_envelope",
        "CREATE TABLE audit_event_record",
        "CREATE TABLE outbox_delivery_record",
        "digest(convert_to(p_canonical_event_json, 'UTF8'), 'sha256')",
        "CREATE TRIGGER audit_event_record_append_only_guard",
        "audit event records are append-only",
        "CREATE FUNCTION protect_outbox_delivery_transition",
        "outbox delivery must transition pending -> leased before completion",
        "CREATE FUNCTION record_audit_outbox_event",
        "CREATE POLICY audit_event_record_scope_policy",
        "CREATE POLICY outbox_delivery_record_scope_policy",
        "CREATE FUNCTION claim_outbox_delivery",
        "CREATE FUNCTION complete_outbox_delivery",
        "CREATE FUNCTION retry_outbox_delivery",
        "CREATE TABLE outbox_delivery_escalation_record",
        "CREATE TRIGGER outbox_delivery_escalation_append_only_guard",
        "CREATE POLICY outbox_delivery_escalation_scope_policy",
        "CREATE FUNCTION dead_letter_outbox_delivery",
        "terminal outbox delivery records are immutable",
        "outbox delivery stored attempt budget is exhausted and cannot be reclaimed",
        "outbox delivery stored attempt budget is exhausted and requires terminal dead-lettering",
        "CREATE TRIGGER audit_event_record_truncate_guard",
        "CREATE TRIGGER outbox_delivery_record_truncate_guard",
        "CREATE INDEX CONCURRENTLY outbox_delivery_due_work_index",
        "CREATE FUNCTION public.operator_dead_letter_expired_outbox_delivery",
        "CREATE ROLE orgmetra_outbox_recovery_owner",
        "CREATE ROLE orgmetra_outbox_operator",
        "SECURITY DEFINER",
        "REVOKE CREATE ON SCHEMA public FROM PUBLIC",
        "CREATE TABLE people_mutation_idempotency_record",
        "CONSTRAINT people_mutation_idempotency_command_unique",
        "CONSTRAINT people_mutation_idempotency_key_check",
        "CONSTRAINT people_mutation_idempotency_digest_check",
        "CREATE TRIGGER people_mutation_idempotency_append_only_guard",
        "CREATE FUNCTION public.reject_people_mutation_idempotency_truncate",
        "CREATE TRIGGER people_mutation_idempotency_truncate_guard",
        "REVOKE TRUNCATE ON people_mutation_idempotency_record FROM PUBLIC",
        "ALTER TABLE people_mutation_idempotency_record FORCE ROW LEVEL SECURITY",
        "CREATE POLICY people_mutation_idempotency_scope_policy",
        "CREATE TABLE job_analysis_snapshot",
        "CREATE TABLE job_analysis_task_item",
        "CREATE TABLE job_analysis_ksao_item",
        "CREATE TABLE job_analysis_task_ksao_link",
        "CREATE TABLE job_analysis_write_command",
        "CONSTRAINT job_analysis_write_command_idempotency_unique",
        "CREATE TRIGGER job_analysis_snapshot_append_only_guard",
        "ALTER TABLE job_analysis_snapshot FORCE ROW LEVEL SECURITY",
        "CREATE POLICY job_analysis_snapshot_scope_policy",
    ]
    for fragment in required_fragments:
        if fragment not in sql:
            _fail(f"Missing database contract fragment: {fragment}")

    tenant_matches = [match for match in matches if match.group("table") != "tenant_record"]
    for index, match in enumerate(matches):
        table_name = match.group("table")
        if table_name == "tenant_record":
            continue
        block_start = match.start()
        next_match_index = index + 1
        block_end = matches[next_match_index].start() if next_match_index < len(matches) else len(table_sql)
        table_block = table_sql[block_start:block_end]
        if "tenant_record_id uuid NOT NULL" not in table_block:
            _fail(f"Tenant binding is missing from table: {table_name}")
        if f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY" not in sql:
            _fail(f"Forced row-level security is missing from table: {table_name}")

    if len(tenant_matches) != len(matches) - 1:
        _fail("Tenant-scoped table discovery is internally inconsistent")


def _yaml_block(document: str, marker: str) -> str:
    """Return the indentation-bounded YAML block after one exact marker line."""
    lines = document.splitlines()
    try:
        start = lines.index(marker)
    except ValueError:
        return ""
    marker_indent = len(marker) - len(marker.lstrip())
    block: list[str] = []
    for line in lines[start + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= marker_indent:
            break
        block.append(line)
    return "\n".join(block)


def _require_in_block(block: str, label: str, fragment: str, description: str) -> None:
    """Require one fragment inside its owning YAML block rather than globally."""
    if fragment not in block:
        _fail(f"{label}: missing {description}")


def _validate_openapi_contract() -> None:
    """Require operation-local authentication, mutation context, and error contracts."""
    openapi = (ROOT / "schemas/openapi.yaml").read_text(encoding="utf-8")
    if not openapi.startswith("openapi: 3.2.0\n"):
        _fail("OpenAPI document must declare version 3.2.0")

    operations = [
        (
            "  /person-records:",
            "createPersonRecord",
            "orgmetra.people.write",
            "CreatePersonRecordCommand",
            (),
        ),
        (
            "  /job-profiles:",
            "createJobProfile",
            "orgmetra.job_architecture.write",
            "CreateJobProfileCommand",
            (),
        ),
        (
            "  /selection-decisions:",
            "recordSelectionDecision",
            "orgmetra.talent_acquisition.write",
            "RecordSelectionDecisionCommand",
            ("        '422':",),
        ),
        (
            "  /employment-records:",
            "createEmploymentRecord",
            "orgmetra.people.write",
            "CreateEmploymentRecordCommand",
            (),
        ),
        (
            "  /position-records:",
            "createPositionRecord",
            "orgmetra.job_architecture.write",
            "CreatePositionRecordCommand",
            (),
        ),
        (
            "  /assignment-records:",
            "createAssignmentRecord",
            "orgmetra.people.write",
            "CreateAssignmentRecordCommand",
            (),
        ),
    ]
    for marker, operation_id, scope, request_schema, extra_responses in operations:
        block = _yaml_block(openapi, marker)
        if not block:
            _fail(f"{operation_id}: path block is missing")
        _require_in_block(block, operation_id, f"operationId: {operation_id}", "operationId")
        _require_in_block(
            block,
            operation_id,
            f"            - {scope}",
            f"least-privilege scope {scope}",
        )
        for parameter_name in (
            "IdempotencyKey",
            "TenantReference",
            "ActorReference",
            "PurposeCode",
        ):
            _require_in_block(
                block,
                operation_id,
                f"$ref: '#/components/parameters/{parameter_name}'",
                f"required parameter {parameter_name}",
            )
        _require_in_block(
            block,
            operation_id,
            f"$ref: '#/components/schemas/{request_schema}'",
            f"request body binding {request_schema}",
        )
        for response in (
            "        '201':",
            "        '400':",
            "        '401':",
            "        '403':",
            "        '409':",
            *extra_responses,
        ):
            _require_in_block(block, operation_id, response, f"response {response.strip()}")
        _require_in_block(block, operation_id, "            Location:", "201 Location header")

    job_analysis_block = _yaml_block(
        openapi, "  /tenants/{tenant_record_id}/job-analysis-snapshots:"
    )
    if not job_analysis_block:
        _fail("persistJobAnalysisSnapshot: path block is missing")
    for fragment, description in (
        ("operationId: persistJobAnalysisSnapshot", "operationId"),
        ("            - orgmetra.job_architecture.write", "least-privilege write scope"),
        ("$ref: '#/components/parameters/IdempotencyKey'", "Idempotency-Key"),
        ("$ref: '#/components/parameters/PurposeCode'", "purpose parameter"),
        ("$ref: '#/components/schemas/PersistJobAnalysisSnapshotCommand'", "request schema"),
        ("        '201':", "201 response"),
        ("            Location:", "201 Location header"),
        ("        '415':", "unsupported-media response"),
    ):
        _require_in_block(job_analysis_block, "persistJobAnalysisSnapshot", fragment, description)

    job_analysis_read_block = _yaml_block(
        openapi,
        "  /tenants/{tenant_record_id}/job-analysis-snapshots/{analysis_record_id}:",
    )
    if not job_analysis_read_block:
        _fail("readJobAnalysisSnapshot: path block is missing")
    _require_in_block(
        job_analysis_read_block,
        "readJobAnalysisSnapshot",
        "operationId: readJobAnalysisSnapshot",
        "operationId",
    )
    _require_in_block(
        job_analysis_read_block,
        "readJobAnalysisSnapshot",
        "            - orgmetra.job_architecture.read",
        "least-privilege read scope",
    )

    for schema_name in (
        "CreateJobProfileCommand",
        "RecordSelectionDecisionCommand",
        "CreateEmploymentRecordCommand",
        "CreatePositionRecordCommand",
        "CreateAssignmentRecordCommand",
    ):
        block = _yaml_block(openapi, f"    {schema_name}:")
        if not block:
            _fail(f"{schema_name}: schema block is missing")
        _require_in_block(
            block,
            schema_name,
            "        - evidence_references",
            "required evidence_references",
        )
        _require_in_block(block, schema_name, "          maxItems: 100", "maxItems 100")
        _require_in_block(block, schema_name, "          uniqueItems: true", "uniqueItems")
        if schema_name != "CreateJobProfileCommand":
            _require_in_block(
                block,
                schema_name,
                "        - confirmation_reference",
                "human confirmation reference",
            )

    decision_block = _yaml_block(openapi, "    RecordSelectionDecisionCommand:")
    if not decision_block:
        _fail("RecordSelectionDecisionCommand: schema block is missing")
    _require_in_block(
        decision_block,
        "RecordSelectionDecisionCommand",
        "        - confirmation_reference",
        "human confirmation reference",
    )

    error_block = _yaml_block(openapi, "    ErrorResponse:")
    if not error_block:
        _fail("ErrorResponse: schema block is missing")
    for field_name in ("error_code", "message", "next_action", "support_reference"):
        _require_in_block(
            error_block,
            "ErrorResponse",
            f"        - {field_name}",
            f"required field {field_name}",
        )
    _require_in_block(
        error_block,
        "ErrorResponse",
        "Opaque random client-safe support identifier.",
        "opaque support-reference semantics",
    )

    if "keyverse_oidc: []" in openapi:
        _fail("OpenID Connect security requirements must declare a least-privilege scope")
    if re.search(r"(?m)^\s*(?:-\s+)?trace_id\s*:", openapi):
        _fail("Client error schemas must not expose internal trace identifiers")


def _validate_markdown() -> None:
    """Reject explicit unfinished-work markers with exact path/line and malformed fences."""
    for path in ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if UNFINISHED_MARKER_LINE_PATTERN.fullmatch(line):
                _fail(
                    "Explicit unfinished-work marker found in "
                    f"{path.relative_to(ROOT)}:{line_number}"
                )
        if text.count("```") % 2:
            _fail(f"Unbalanced code fence in {path.relative_to(ROOT)}")


def _validate_license() -> None:
    """Require the complete Apache License 2.0 grant text."""
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    if (
        "Apache License" not in license_text
        or "END OF TERMS AND CONDITIONS" not in license_text
    ):
        _fail("LICENSE is not the complete Apache License 2.0 text")


def main() -> None:
    """Run every foundation-pack validation gate or emit exact manifest repair data."""
    _require_files()
    if sys.argv[1:] == ["--print-manifest"]:
        print(json.dumps(_expected_manifest_document(), indent=2, sort_keys=False))
        return
    if sys.argv[1:]:
        _fail(f"Unsupported arguments: {sys.argv[1:]}")
    _validate_manifest()
    _validate_database_contract()
    _validate_openapi_contract()
    _validate_markdown()
    _validate_license()
    print("Orgmetra foundation pack validation passed")


if __name__ == "__main__":
    main()
