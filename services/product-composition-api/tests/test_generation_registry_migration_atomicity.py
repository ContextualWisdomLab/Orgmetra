from pathlib import Path


def _migration_text() -> str:
    return (
        Path(__file__).resolve().parents[3]
        / "database"
        / "migrations"
        / "0018_product_composition_generation_registry.sql"
    ).read_text(encoding="utf-8")


def test_generation_registry_schema_and_guards_publish_atomically() -> None:
    normalized = _migration_text().strip()
    assert normalized.startswith("BEGIN;")
    assert normalized.endswith("COMMIT;")

    create_table = normalized.index("CREATE TABLE public.product_composition_generation")
    append_only_guard = normalized.index(
        "CREATE TRIGGER product_composition_generation_append_only_guard"
    )
    truncate_guard = normalized.index(
        "CREATE TRIGGER product_composition_generation_truncate_guard"
    )
    commit = normalized.rindex("COMMIT;")

    assert create_table < append_only_guard < commit
    assert create_table < truncate_guard < commit


def test_generation_registry_migration_ignores_caller_search_path() -> None:
    migration = _migration_text()
    normalized = migration.strip()

    assert normalized.startswith("BEGIN;\nSET LOCAL search_path = pg_catalog, public;")

    for relation_name in (
        "product_composition_generation",
        "product_composition_owner_release",
        "product_composition_route",
        "product_composition_route_method",
    ):
        assert f"CREATE TABLE public.{relation_name}" in migration
        assert f"ON public.{relation_name}" in migration

    assert "CREATE FUNCTION public.reject_product_composition_generation_registry_truncate()" in migration
    assert migration.count("EXECUTE FUNCTION public.reject_append_only_mutation();") == 4
    assert (
        migration.count(
            "EXECUTE FUNCTION public.reject_product_composition_generation_registry_truncate();"
        )
        == 4
    )

    assert "REFERENCES public.product_composition_generation(generation_id)" in migration
    assert (
        "REFERENCES public.product_composition_owner_release(generation_id, service_id)"
        in migration
    )
    assert (
        "REFERENCES public.product_composition_route(generation_id, route_id)" in migration
    )
