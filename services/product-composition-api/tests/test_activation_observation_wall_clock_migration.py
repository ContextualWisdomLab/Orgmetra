"""Contract for database-enforced owner-observation wall-clock evidence."""

from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
_MIGRATION = (
    _REPO_ROOT
    / "database"
    / "migrations"
    / "0021_product_composition_activation_observation_wall_clock.sql"
)
_UPGRADE_CONTRACT = (
    _REPO_ROOT
    / "tests"
    / "test_product_composition_activation_observation_wall_clock_upgrade_postgres.sh"
)


def test_current_schema_rejects_future_dated_owner_observations() -> None:
    """Require current PostgreSQL truth to reject observations dated after DB wall clock."""
    sql = _MIGRATION.read_text(encoding="utf-8")

    assert "future-dated owner observation history" in sql
    assert "IF EXISTS" in sql
    assert "validate_product_composition_activation_observation_wall_clock" in sql
    assert "clock_timestamp()" in sql
    assert "NEW.observed_at_unix_ms > wall_clock_unix_ms" in sql
    assert "NEW.valid_until_unix_ms <= wall_clock_unix_ms" in sql
    assert "BEFORE INSERT ON public.product_composition_activation_owner_observation" in sql


def test_wall_clock_upgrade_fences_preflight_and_trigger_installation_atomically() -> None:
    """Prevent a concurrent impossible observation from slipping between scan and trigger install."""
    sql = _MIGRATION.read_text(encoding="utf-8")
    begin_index = sql.index("BEGIN;")
    lock_index = sql.index(
        "LOCK TABLE public.product_composition_activation_owner_observation "
        "IN SHARE ROW EXCLUSIVE MODE;"
    )
    preflight_index = sql.index("DO $$")
    trigger_index = sql.index(
        "CREATE TRIGGER product_composition_activation_owner_observation_wall_clock_guard"
    )
    commit_index = sql.rindex("COMMIT;")

    assert begin_index < lock_index < preflight_index < trigger_index < commit_index
    assert sql[:begin_index].strip().startswith("-- Reject owner-operation observations")
    assert sql[commit_index + len("COMMIT;") :].strip() == ""


def test_upgrade_race_contract_waits_for_observed_writer_state() -> None:
    """Require DB-observed writer readiness instead of a scheduler-sensitive fixed sleep."""
    contract = _UPGRADE_CONTRACT.read_text(encoding="utf-8")

    assert "pg_stat_activity" in contract
    assert "writer_ready" in contract
    assert "writer was not observed inside the predecessor transaction" in contract
    assert "sleep 1" not in contract
