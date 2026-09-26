"""Contracts for database-level activation/recovery writer serialization."""

from pathlib import Path


_MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "database"
    / "migrations"
    / "0023_product_composition_deployment_write_serialization.sql"
)


def test_activation_and_recovery_share_one_database_level_deployment_lock() -> None:
    """Require direct SQL writers to serialize on the same deployment row as the application."""
    sql = _MIGRATION.read_text(encoding="utf-8").strip()

    assert sql.startswith("BEGIN;\nSET LOCAL search_path = pg_catalog, public;")
    assert sql.endswith("COMMIT;")
    assert (
        "LOCK TABLE public.product_composition_activation_event "
        "IN SHARE ROW EXCLUSIVE MODE;"
    ) in sql
    assert (
        "LOCK TABLE public.product_composition_recovery_attestation "
        "IN SHARE ROW EXCLUSIVE MODE;"
    ) in sql
    assert "CREATE FUNCTION public.lock_product_composition_deployment_write()" in sql
    assert "FROM public.product_composition_deployment" in sql
    assert "FOR UPDATE;" in sql
    assert (
        "CREATE TRIGGER product_composition_activation_event_00_deployment_lock_guard"
    ) in sql
    assert "BEFORE INSERT ON public.product_composition_activation_event" in sql
    assert "EXECUTE FUNCTION public.lock_product_composition_deployment_write();" in sql
    assert (
        "CREATE TRIGGER product_composition_recovery_attestation_00_deployment_lock_guard"
    ) in sql
    assert "BEFORE INSERT ON public.product_composition_recovery_attestation" in sql


def test_writer_fences_precede_shared_lock_trigger_publication() -> None:
    """Drain predecessor direct writers before publishing the shared deployment lock guards."""
    sql = _MIGRATION.read_text(encoding="utf-8")

    activation_fence = sql.index(
        "LOCK TABLE public.product_composition_activation_event IN SHARE ROW EXCLUSIVE MODE;"
    )
    recovery_fence = sql.index(
        "LOCK TABLE public.product_composition_recovery_attestation IN SHARE ROW EXCLUSIVE MODE;"
    )
    activation_guard = sql.index(
        "CREATE TRIGGER product_composition_activation_event_00_deployment_lock_guard"
    )
    recovery_guard = sql.index(
        "CREATE TRIGGER product_composition_recovery_attestation_00_deployment_lock_guard"
    )

    assert activation_fence < activation_guard
    assert recovery_fence < recovery_guard
