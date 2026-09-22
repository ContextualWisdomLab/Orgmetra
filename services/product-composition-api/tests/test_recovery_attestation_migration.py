"""Contracts for durable recovery re-admission attribution."""

from pathlib import Path


_MIGRATION = Path("database/migrations/0022_product_composition_recovery_attestation.sql")


def test_recovery_attestation_binds_current_state_and_fresh_recovery_evidence() -> None:
    """Require PostgreSQL to retain and independently validate successful recovery evidence."""
    sql = _MIGRATION.read_text(encoding="utf-8")

    assert "CREATE TABLE public.product_composition_recovery_attestation" in sql
    assert "CREATE FUNCTION public.validate_product_composition_recovery_attestation_insert()" in sql
    assert "FOREIGN KEY (deployment_id, environment_id, activation_sequence)" in sql
    assert "evidence_bundle_sha256" in sql
    assert "evidence_authorization_action IS DISTINCT FROM 'recover'" in sql
    assert "evidence_authorized_state_sequence IS DISTINCT FROM NEW.activation_sequence" in sql
    assert "NEW.generation_id IS DISTINCT FROM latest_generation_id" in sql
    assert "clock_timestamp()" in sql
    assert "observation.observed_at_unix_ms <= wall_clock_unix_ms" in sql
    assert "wall_clock_unix_ms < observation.valid_until_unix_ms" in sql


def test_recovery_attestation_history_is_append_only() -> None:
    """Require successful recovery attestations to survive process restart and audit replay."""
    sql = _MIGRATION.read_text(encoding="utf-8")

    assert "BEFORE UPDATE OR DELETE ON public.product_composition_recovery_attestation" in sql
    assert "EXECUTE FUNCTION public.reject_append_only_mutation()" in sql
    assert "BEFORE TRUNCATE ON public.product_composition_recovery_attestation" in sql
    assert (
        "EXECUTE FUNCTION public.reject_product_composition_activation_registry_truncate();"
        in sql
    )


def test_recovery_attestation_schema_becomes_visible_atomically_with_all_guards() -> None:
    """Do not expose the new durable table before its validation and append-only guards exist."""
    sql = _MIGRATION.read_text(encoding="utf-8").strip()

    assert sql.startswith("BEGIN;\nSET LOCAL search_path = pg_catalog, public;")
    assert sql.endswith("COMMIT;")
    assert sql.index("CREATE TABLE public.product_composition_recovery_attestation") < sql.index(
        "CREATE TRIGGER product_composition_recovery_attestation_insert_guard"
    )
