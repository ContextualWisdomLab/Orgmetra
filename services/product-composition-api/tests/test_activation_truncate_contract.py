from pathlib import Path


def test_activation_registry_blocks_truncate_on_durable_authority() -> None:
    migration = (
        Path(__file__).resolve().parents[3]
        / "database"
        / "migrations"
        / "0019_product_composition_activation_registry.sql"
    ).read_text(encoding="utf-8")

    for table in (
        "product_composition_deployment",
        "product_composition_activation_event",
    ):
        assert f"CREATE TRIGGER {table}_truncate_guard" in migration
        assert f"BEFORE TRUNCATE ON {table}" in migration

    assert "reject_product_composition_activation_registry_truncate" in migration
