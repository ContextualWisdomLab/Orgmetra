from pathlib import Path


def test_generation_registry_blocks_truncate_on_every_durable_table() -> None:
    migration = (
        Path(__file__).resolve().parents[3]
        / "database"
        / "migrations"
        / "0018_product_composition_generation_registry.sql"
    ).read_text(encoding="utf-8")

    for table in (
        "product_composition_generation",
        "product_composition_owner_release",
        "product_composition_route",
        "product_composition_route_method",
    ):
        assert f"CREATE TRIGGER {table}_truncate_guard" in migration
        assert f"BEFORE TRUNCATE ON public.{table}" in migration

    assert "reject_product_composition_generation_registry_truncate" in migration
