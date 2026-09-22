from pathlib import Path


def test_generation_registry_schema_and_guards_publish_atomically() -> None:
    migration = (
        Path(__file__).resolve().parents[3]
        / "database"
        / "migrations"
        / "0018_product_composition_generation_registry.sql"
    ).read_text(encoding="utf-8")

    normalized = migration.strip()
    assert normalized.startswith("BEGIN;")
    assert normalized.endswith("COMMIT;")

    create_table = normalized.index("CREATE TABLE product_composition_generation")
    append_only_guard = normalized.index(
        "CREATE TRIGGER product_composition_generation_append_only_guard"
    )
    truncate_guard = normalized.index(
        "CREATE TRIGGER product_composition_generation_truncate_guard"
    )
    commit = normalized.rindex("COMMIT;")

    assert create_table < append_only_guard < commit
    assert create_table < truncate_guard < commit
