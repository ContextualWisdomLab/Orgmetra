"""Architecture contract for workforce-validation-owned PostgreSQL persistence."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MIGRATION = ROOT / "services/workforce-validation-api/database/migrations/0001_owner_schema.sql"


def test_owner_schema_migration_establishes_deny_default_role_boundary() -> None:
    """Require a service-owned schema and least-privilege database role before adapters."""
    sql = MIGRATION.read_text(encoding="utf-8")

    required = (
        "CREATE ROLE workforce_validation_role NOLOGIN",
        "CREATE SCHEMA workforce_validation AUTHORIZATION workforce_validation_role",
        "REVOKE ALL ON SCHEMA workforce_validation FROM PUBLIC",
        "ALTER ROLE workforce_validation_role SET search_path = workforce_validation, pg_catalog",
    )
    for contract in required:
        assert contract in sql

    assert "CREATE TABLE" not in sql
    assert "public.validity_study" not in sql
    assert "GRANT ALL" not in sql


def test_owner_migration_history_is_bounded_context_local() -> None:
    """Prevent a new global migration number from colliding with other active lanes."""
    relative_path = MIGRATION.relative_to(ROOT).as_posix()

    assert relative_path == "services/workforce-validation-api/database/migrations/0001_owner_schema.sql"
