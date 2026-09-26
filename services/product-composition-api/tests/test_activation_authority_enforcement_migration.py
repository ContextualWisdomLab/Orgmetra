from __future__ import annotations

from pathlib import Path


def _migration_text() -> str:
    return (
        Path(__file__).resolve().parents[3]
        / "database"
        / "migrations"
        / "0020_product_composition_activation_authority_enforcement.sql"
    ).read_text(encoding="utf-8")


def test_current_activation_schema_requires_authorization_evidence() -> None:
    migration = _migration_text()

    assert "WHERE evidence_bundle_sha256 IS NULL" in migration
    assert "cannot enforce authorized activation while structural events exist" in migration
    assert "ALTER COLUMN evidence_bundle_sha256 SET NOT NULL" in migration


def test_authority_upgrade_fences_writers_before_preflight_and_not_null_publish() -> None:
    migration = _migration_text().strip()

    assert migration.endswith("COMMIT;")

    begin = migration.index("BEGIN;")
    lock = migration.index(
        "LOCK TABLE public.product_composition_activation_event IN SHARE ROW EXCLUSIVE MODE;"
    )
    preflight = migration.index("WHERE evidence_bundle_sha256 IS NULL")
    enforce = migration.index("ALTER COLUMN evidence_bundle_sha256 SET NOT NULL")
    commit = migration.rindex("COMMIT;")

    assert begin < lock < preflight < enforce < commit
