"""Static contracts for the tenant and audit migration."""

from __future__ import annotations

import re
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "database"
    / "migrations"
    / "0002_tenant_audit_boundary.sql"
)


def _migration_text() -> str:
    """Return the exact migration text under test."""

    return MIGRATION_PATH.read_text(encoding="utf-8")


def test_created_database_objects_use_descriptive_snake_case() -> None:
    migration_text = _migration_text()
    object_names = re.findall(
        r"CREATE\s+(?:TABLE|FUNCTION|INDEX|TRIGGER)\s+([a-z][a-z0-9_]*)",
        migration_text,
        flags=re.IGNORECASE,
    )

    assert object_names
    for object_name in object_names:
        assert object_name == object_name.lower()
        assert re.fullmatch(r"[a-z][a-z0-9_]*", object_name)
        assert "_" in object_name


def test_every_protected_table_has_forced_row_level_security() -> None:
    migration_text = _migration_text()
    protected_tables = {
        "tenant_record",
        "person_record",
        "person_name_record",
        "employment_record",
        "organization_unit",
        "job_profile",
        "position_record",
        "assignment_record",
        "candidate_profile",
        "candidate_worker_link",
        "criterion_blueprint",
        "criterion_observation",
        "selection_decision",
        "validity_study",
        "compensation_record",
        "employment_transition",
        "audit_event",
    }

    array_match = re.search(
        r"FOREACH protected_table IN ARRAY ARRAY\[(?P<body>.*?)\]",
        migration_text,
        flags=re.DOTALL,
    )
    assert array_match is not None
    listed_tables = set(re.findall(r"'([a-z][a-z0-9_]*)'", array_match["body"]))
    assert listed_tables == protected_tables
    assert "ENABLE ROW LEVEL SECURITY" in migration_text
    assert "FORCE ROW LEVEL SECURITY" in migration_text
    assert "WITH CHECK" in migration_text


def test_person_name_is_versioned_outside_durable_person_anchor() -> None:
    """Keep mutable names bitemporal instead of rewriting person identity."""

    migration_text = _migration_text()

    assert "CREATE TABLE person_name_record" in migration_text
    assert "ALTER TABLE person_record DROP COLUMN display_name" in migration_text
    assert "person_name_record_id uuid PRIMARY KEY" in migration_text
    assert "effective_from date NOT NULL" in migration_text
    assert "effective_to date" in migration_text
    assert "recorded_from timestamptz NOT NULL DEFAULT now()" in migration_text
    assert "recorded_to timestamptz" in migration_text
    assert "person_name_person_tenant_foreign_key" in migration_text


def test_migration_contains_no_blanket_masking_or_unbounded_public_grants() -> None:
    normalized = _migration_text().upper()

    assert "MASK" not in normalized
    assert "GRANT ALL" not in normalized
    assert " TO PUBLIC" not in normalized
    assert "BYPASSRLS" not in normalized
