#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

for migration in \
    database/migrations/0001_foundation_schema.sql \
    database/migrations/0018_product_composition_generation_registry.sql \
    database/migrations/0019_product_composition_activation_registry.sql \
    database/migrations/0020_product_composition_activation_authority_enforcement.sql \
    database/migrations/0021_product_composition_activation_observation_wall_clock.sql \
    database/migrations/0022_product_composition_recovery_attestation.sql \
    database/migrations/0023_product_composition_deployment_write_serialization.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
CREATE SCHEMA composition_decoy;
CREATE FUNCTION composition_decoy.reject_append_only_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN NEW;
END;
$$;
SQL

PGOPTIONS='-c search_path=composition_decoy,public' \
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -f database/migrations/0024_product_composition_activation_trigger_function_provenance.sql

binding_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
WITH expected(trigger_name, relation_name) AS (
    VALUES
        ('product_composition_activation_event_00_deployment_lock_guard', 'product_composition_activation_event'),
        ('product_composition_activation_event_lineage_guard', 'product_composition_activation_event'),
        ('product_composition_recovery_attestation_00_deployment_lock_guard', 'product_composition_recovery_attestation'),
        ('product_composition_recovery_attestation_insert_guard', 'product_composition_recovery_attestation'),
        ('product_composition_activation_owner_observation_insert_guard', 'product_composition_activation_owner_observation'),
        ('product_composition_activation_owner_observation_wall_clock_guard', 'product_composition_activation_owner_observation'),
        ('product_composition_deployment_append_only_guard', 'product_composition_deployment'),
        ('product_composition_activation_evidence_append_only_guard', 'product_composition_activation_evidence'),
        ('product_composition_activation_owner_observation_append_only_guard', 'product_composition_activation_owner_observation'),
        ('product_composition_activation_event_append_only_guard', 'product_composition_activation_event'),
        ('product_composition_recovery_attestation_append_only_guard', 'product_composition_recovery_attestation'),
        ('product_composition_deployment_truncate_guard', 'product_composition_deployment'),
        ('product_composition_activation_evidence_truncate_guard', 'product_composition_activation_evidence'),
        ('product_composition_activation_owner_observation_truncate_guard', 'product_composition_activation_owner_observation'),
        ('product_composition_activation_event_truncate_guard', 'product_composition_activation_event'),
        ('product_composition_recovery_attestation_truncate_guard', 'product_composition_recovery_attestation')
), deployment_owner AS (
    SELECT relation.relowner AS owner_oid
    FROM pg_catalog.pg_class AS relation
    JOIN pg_catalog.pg_namespace AS namespace
      ON namespace.oid = relation.relnamespace
    WHERE namespace.nspname = 'public'
      AND relation.relname = 'product_composition_deployment'
)
SELECT count(*)
FROM expected
JOIN pg_catalog.pg_class AS relation
  ON relation.relname = expected.relation_name
JOIN pg_catalog.pg_namespace AS relation_namespace
  ON relation_namespace.oid = relation.relnamespace
 AND relation_namespace.nspname = 'public'
JOIN pg_catalog.pg_trigger AS trigger_definition
  ON trigger_definition.tgrelid = relation.oid
 AND trigger_definition.tgname = expected.trigger_name
 AND NOT trigger_definition.tgisinternal
JOIN pg_catalog.pg_proc AS function_definition
  ON function_definition.oid = trigger_definition.tgfoid
JOIN pg_catalog.pg_namespace AS function_namespace
  ON function_namespace.oid = function_definition.pronamespace
CROSS JOIN deployment_owner
WHERE function_namespace.nspname = 'public'
  AND function_definition.proowner = deployment_owner.owner_oid;
")"

if [[ "${binding_count}" != "16" ]]; then
    echo "expected 16 trusted public trigger bindings, observed ${binding_count}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO public.product_composition_deployment (deployment_id, environment_id)
VALUES ('orgmetra_gateway', 'production');
SQL

set +e
PGOPTIONS='-c search_path=composition_decoy,public' \
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 >/tmp/orgmetra-composition-trigger-provenance.log 2>&1 <<'SQL'
UPDATE public.product_composition_deployment
SET registered_at = clock_timestamp()
WHERE deployment_id = 'orgmetra_gateway'
  AND environment_id = 'production';
SQL
update_status=$?
set -e

if [[ ${update_status} -eq 0 ]]; then
    echo "hostile search_path bypassed the append-only trigger binding" >&2
    exit 1
fi

grep -q "append-only" /tmp/orgmetra-composition-trigger-provenance.log
