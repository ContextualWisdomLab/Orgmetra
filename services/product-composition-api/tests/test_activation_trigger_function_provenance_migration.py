"""Contracts for schema-qualified provenance in durable activation state."""

from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
_TRIGGER_MIGRATION = (
    _REPO_ROOT
    / "database"
    / "migrations"
    / "0024_product_composition_activation_trigger_function_provenance.sql"
)
_RELATION_OWNER_MIGRATION = (
    _REPO_ROOT
    / "database"
    / "migrations"
    / "0025_product_composition_activation_relation_owner_provenance.sql"
)


def test_activation_trigger_functions_rebind_to_public_owned_authority() -> None:
    """Require final-schema triggers to bind trusted public functions under a writer fence."""
    sql = _TRIGGER_MIGRATION.read_text(encoding="utf-8").strip()

    assert sql.startswith("BEGIN;")
    assert sql.endswith("COMMIT;")
    for relation in (
        "product_composition_deployment",
        "product_composition_activation_evidence",
        "product_composition_activation_owner_observation",
        "product_composition_activation_event",
        "product_composition_recovery_attestation",
    ):
        assert f"public.{relation}" in sql
    assert "IN SHARE ROW EXCLUSIVE MODE;" in sql
    assert "pg_catalog.to_regprocedure(" in sql
    assert "pg_catalog.format('public.%I()', function_name)" in sql
    assert "function_owner IS DISTINCT FROM expected_owner" in sql
    assert "CREATE TRIGGER product_composition_activation_event_00_deployment_lock_guard" in sql
    assert "EXECUTE FUNCTION public.lock_product_composition_deployment_write();" in sql
    assert "CREATE TRIGGER product_composition_activation_event_lineage_guard" in sql
    assert "EXECUTE FUNCTION public.validate_product_composition_activation_insert();" in sql
    assert "CREATE TRIGGER product_composition_recovery_attestation_insert_guard" in sql
    assert "EXECUTE FUNCTION public.validate_product_composition_recovery_attestation_insert();" in sql
    assert "EXECUTE FUNCTION public.reject_append_only_mutation();" in sql
    assert (
        "EXECUTE FUNCTION public.reject_product_composition_activation_registry_truncate();"
        in sql
    )


def test_all_rebound_trigger_function_calls_are_schema_qualified() -> None:
    """Reject search-path dependent trigger-function resolution in the final trigger migration."""
    sql = _TRIGGER_MIGRATION.read_text(encoding="utf-8")

    execute_lines = [
        line.strip()
        for line in sql.splitlines()
        if line.strip().startswith("EXECUTE FUNCTION ")
    ]
    assert execute_lines
    assert all(line.startswith("EXECUTE FUNCTION public.") for line in execute_lines)


def test_activation_authority_relations_share_generation_authority_owner() -> None:
    """Reject both split ownership and a uniformly retargeted activation authority owner."""
    sql = _RELATION_OWNER_MIGRATION.read_text(encoding="utf-8").strip()

    assert sql.startswith("BEGIN;")
    assert sql.endswith("COMMIT;")
    assert "SET LOCAL search_path = pg_catalog, public;" in sql
    assert "IN SHARE ROW EXCLUSIVE MODE;" in sql
    assert "relation.relname = 'product_composition_generation'" in sql
    assert "generation authority owner" in sql
    for relation in (
        "product_composition_deployment",
        "product_composition_activation_evidence",
        "product_composition_activation_owner_observation",
        "product_composition_activation_event",
        "product_composition_recovery_attestation",
    ):
        assert f"'{relation}'" in sql
    assert "relation_owner IS DISTINCT FROM expected_owner" in sql
    assert "ALTER TABLE" not in sql
