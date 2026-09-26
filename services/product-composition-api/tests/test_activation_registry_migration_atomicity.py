from pathlib import Path


def _migration_text() -> str:
    return (
        Path(__file__).resolve().parents[3]
        / "database"
        / "migrations"
        / "0019_product_composition_activation_registry.sql"
    ).read_text(encoding="utf-8")


def test_activation_registry_schema_and_guards_publish_atomically() -> None:
    normalized = _migration_text().strip()
    assert normalized.startswith("BEGIN;\nSET LOCAL search_path = pg_catalog, public;")
    assert normalized.endswith("COMMIT;")

    create_table = normalized.index("CREATE TABLE public.product_composition_deployment")
    lineage_guard = normalized.index(
        "CREATE TRIGGER product_composition_activation_event_lineage_guard"
    )
    truncate_guard = normalized.index(
        "CREATE TRIGGER product_composition_activation_event_truncate_guard"
    )
    commit = normalized.rindex("COMMIT;")

    assert create_table < lineage_guard < commit
    assert create_table < truncate_guard < commit


def test_activation_registry_migration_pins_authority_objects_to_public() -> None:
    migration = _migration_text()

    for relation_name in (
        "product_composition_deployment",
        "product_composition_activation_evidence",
        "product_composition_activation_owner_observation",
        "product_composition_activation_event",
    ):
        assert f"CREATE TABLE public.{relation_name}" in migration
        assert f"ON public.{relation_name}" in migration

    for function_name in (
        "validate_product_composition_activation_observation_insert",
        "validate_product_composition_activation_insert",
        "reject_product_composition_activation_registry_truncate",
    ):
        assert f"CREATE FUNCTION public.{function_name}()" in migration
        assert f"EXECUTE FUNCTION public.{function_name}();" in migration

    assert "REFERENCES public.product_composition_generation" in migration
    assert "REFERENCES public.product_composition_owner_release" in migration
    assert "REFERENCES public.product_composition_route_method" in migration
