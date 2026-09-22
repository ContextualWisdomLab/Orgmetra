"""Contract for database-enforced owner-observation wall-clock evidence."""

from pathlib import Path


_MIGRATION = Path("database/migrations/0021_product_composition_activation_observation_wall_clock.sql")


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
