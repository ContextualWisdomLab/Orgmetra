from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
_MIGRATION = (
    _REPO_ROOT
    / "database"
    / "migrations"
    / "0025_product_composition_activation_relation_owner_provenance.sql"
)


def _validator_body(migration: str, function_name: str, next_function_name: str | None) -> str:
    """Return one final validator body so each durable boundary is asserted independently."""
    marker = f"CREATE OR REPLACE FUNCTION public.{function_name}()"
    body = migration.split(marker, 1)[1]
    if next_function_name is not None:
        body = body.split(
            f"CREATE OR REPLACE FUNCTION public.{next_function_name}()",
            1,
        )[0]
    return body


def test_activation_and_recovery_cap_bundle_lifetime_by_owner_observation() -> None:
    """Keep database authorization no longer-lived than its route-operation evidence."""
    migration = _MIGRATION.read_text(encoding="utf-8")
    activation = _validator_body(
        migration,
        "validate_product_composition_activation_insert",
        "validate_product_composition_recovery_attestation_insert",
    )
    recovery = _validator_body(
        migration,
        "validate_product_composition_recovery_attestation_insert",
        None,
    )

    for validator in (activation, recovery):
        assert "observation.observed_at_unix_ms <= wall_clock_unix_ms" in validator
        assert (
            "evidence_valid_until_unix_ms <= observation.valid_until_unix_ms"
            in validator
        )
