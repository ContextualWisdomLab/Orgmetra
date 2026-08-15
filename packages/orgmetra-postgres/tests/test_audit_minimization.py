"""Prevent HR content from drifting into the authoritative audit table."""

from __future__ import annotations

import re
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "database"
    / "migrations"
    / "0002_tenant_audit_boundary.sql"
)


def test_audit_event_contains_references_not_hr_content() -> None:
    migration_text = MIGRATION_PATH.read_text(encoding="utf-8")
    table_match = re.search(
        r"CREATE TABLE audit_event \((?P<body>.*?)\n\);",
        migration_text,
        flags=re.DOTALL,
    )
    assert table_match is not None
    table_body = table_match["body"]

    required_columns = {
        "audit_event_id",
        "tenant_record_id",
        "actor_reference",
        "purpose_code",
        "correlation_reference",
        "decision_reference",
        "evidence_reference",
        "action_code",
        "resource_type_code",
        "resource_record_id",
        "occurred_at",
    }
    declared_columns = {
        match.group(1)
        for match in re.finditer(r"^\s{4}([a-z][a-z0-9_]*)\s", table_body, re.MULTILINE)
        if match.group(1) != "CONSTRAINT"
    }
    assert declared_columns == required_columns

    forbidden_terms = {
        "display_name",
        "legal_name",
        "email_address",
        "phone_number",
        "document_content",
        "resume_content",
        "assessment_response",
        "compensation_amount",
    }
    assert forbidden_terms.isdisjoint(declared_columns)
