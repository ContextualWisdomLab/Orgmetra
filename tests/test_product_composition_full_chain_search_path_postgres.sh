#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -f database/migrations/0001_foundation_schema.sql

# Execute the complete product-composition authority lineage from a caller-controlled schema.
# Each migration is included in the same session so transaction-local search_path hardening must
# be re-established by every migration that creates unqualified authority objects.
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
CREATE SCHEMA composition_full_chain_decoy;
SET search_path = composition_full_chain_decoy, public;
\i database/migrations/0018_product_composition_generation_registry.sql
\i database/migrations/0019_product_composition_activation_registry.sql
\i database/migrations/0020_product_composition_activation_authority_enforcement.sql
\i database/migrations/0021_product_composition_activation_observation_wall_clock.sql
\i database/migrations/0022_product_composition_recovery_attestation.sql
\i database/migrations/0023_product_composition_deployment_write_serialization.sql
\i database/migrations/0024_product_composition_activation_trigger_function_provenance.sql
\i database/migrations/0025_product_composition_activation_relation_owner_provenance.sql
SQL

public_relation_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM pg_catalog.pg_class AS relation
JOIN pg_catalog.pg_namespace AS namespace
  ON namespace.oid = relation.relnamespace
WHERE namespace.nspname = 'public'
  AND relation.relkind = 'r'
  AND relation.relname IN (
      'product_composition_generation',
      'product_composition_owner_release',
      'product_composition_route',
      'product_composition_route_method',
      'product_composition_deployment',
      'product_composition_activation_evidence',
      'product_composition_activation_owner_observation',
      'product_composition_activation_event',
      'product_composition_recovery_attestation'
  );
")"
if [[ "${public_relation_count}" != "9" ]]; then
    echo "full migration chain did not publish all product-composition authority relations in public" >&2
    exit 1
fi

decoy_relation_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM pg_catalog.pg_class AS relation
JOIN pg_catalog.pg_namespace AS namespace
  ON namespace.oid = relation.relnamespace
WHERE namespace.nspname = 'composition_full_chain_decoy'
  AND relation.relname LIKE 'product_composition_%';
")"
if [[ "${decoy_relation_count}" != "0" ]]; then
    echo "caller search_path redirected product-composition authority relations into decoy schema" >&2
    exit 1
fi

decoy_function_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM pg_catalog.pg_proc AS function_definition
JOIN pg_catalog.pg_namespace AS namespace
  ON namespace.oid = function_definition.pronamespace
WHERE namespace.nspname = 'composition_full_chain_decoy'
  AND function_definition.proname IN (
      'validate_product_composition_activation_observation_insert',
      'validate_product_composition_activation_insert',
      'reject_product_composition_activation_registry_truncate',
      'validate_product_composition_activation_observation_wall_clock',
      'validate_product_composition_recovery_attestation_insert',
      'lock_product_composition_deployment_write'
  );
")"
if [[ "${decoy_function_count}" != "0" ]]; then
    echo "caller search_path redirected product-composition trigger functions into decoy schema" >&2
    exit 1
fi

trusted_activation_trigger_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM pg_catalog.pg_trigger AS trigger_definition
JOIN pg_catalog.pg_class AS relation
  ON relation.oid = trigger_definition.tgrelid
JOIN pg_catalog.pg_namespace AS relation_namespace
  ON relation_namespace.oid = relation.relnamespace
JOIN pg_catalog.pg_proc AS function_definition
  ON function_definition.oid = trigger_definition.tgfoid
JOIN pg_catalog.pg_namespace AS function_namespace
  ON function_namespace.oid = function_definition.pronamespace
WHERE NOT trigger_definition.tgisinternal
  AND relation_namespace.nspname = 'public'
  AND relation.relname IN (
      'product_composition_deployment',
      'product_composition_activation_evidence',
      'product_composition_activation_owner_observation',
      'product_composition_activation_event',
      'product_composition_recovery_attestation'
  )
  AND function_namespace.nspname = 'public';
")"
if [[ "${trusted_activation_trigger_count}" != "16" ]]; then
    echo "activation/recovery authority triggers did not bind exclusively to trusted public functions" >&2
    exit 1
fi

shared_activation_owner_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
WITH deployment_owner AS (
    SELECT relation.relowner AS owner_oid
    FROM pg_catalog.pg_class AS relation
    JOIN pg_catalog.pg_namespace AS namespace
      ON namespace.oid = relation.relnamespace
    WHERE namespace.nspname = 'public'
      AND relation.relname = 'product_composition_deployment'
      AND relation.relkind = 'r'
)
SELECT count(*)
FROM pg_catalog.pg_class AS relation
JOIN pg_catalog.pg_namespace AS namespace
  ON namespace.oid = relation.relnamespace
CROSS JOIN deployment_owner
WHERE namespace.nspname = 'public'
  AND relation.relkind = 'r'
  AND relation.relname IN (
      'product_composition_deployment',
      'product_composition_activation_evidence',
      'product_composition_activation_owner_observation',
      'product_composition_activation_event',
      'product_composition_recovery_attestation'
  )
  AND relation.relowner = deployment_owner.owner_oid;
")"
if [[ "${shared_activation_owner_count}" != "5" ]]; then
    echo "activation/recovery authority relations do not share one durable owner" >&2
    exit 1
fi
