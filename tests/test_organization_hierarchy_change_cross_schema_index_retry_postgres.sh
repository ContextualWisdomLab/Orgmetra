#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

fixture_schema="unrelated_hierarchy_index_fixture"
cleanup() {
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "DROP SCHEMA IF EXISTS ${fixture_schema} CASCADE;" >/dev/null
    rm -f /tmp/orgmetra-cross-schema-index-retry.log
}
trap cleanup EXIT

cleanup

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
CREATE SCHEMA ${fixture_schema};
CREATE TABLE ${fixture_schema}.unrelated_index_owner (
    tenant_record_id uuid NOT NULL,
    recorded_from timestamptz NOT NULL
);
CREATE INDEX organization_unit_tenant_recorded_from_idx
    ON ${fixture_schema}.unrelated_index_owner (tenant_record_id, recorded_from);
SQL

set +e
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -f database/migrations/0028_organization_hierarchy_change_concurrency_hardening.sql \
    >/tmp/orgmetra-cross-schema-index-retry.log 2>&1
retry_status=$?
set -e
if [[ ${retry_status} -ne 0 ]]; then
    cat /tmp/orgmetra-cross-schema-index-retry.log >&2
    echo "migration 0028 treated an unrelated-schema same-name index as a public contract failure" >&2
    exit 1
fi

public_index_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM pg_class AS index_class
JOIN pg_namespace AS namespace
  ON namespace.oid = index_class.relnamespace
JOIN pg_index AS index_state
  ON index_state.indexrelid = index_class.oid
WHERE namespace.nspname = 'public'
  AND index_class.relname = 'organization_unit_tenant_recorded_from_idx'
  AND index_state.indisvalid
  AND index_state.indisready
  AND pg_get_indexdef(index_class.oid, 1, true) = 'tenant_record_id'
  AND pg_get_indexdef(index_class.oid, 2, true) = 'recorded_from';")"
if [[ "${public_index_count}" != "1" ]]; then
    echo "migration 0028 did not preserve exactly one valid public hierarchy index: ${public_index_count}" >&2
    exit 1
fi

echo "organization hierarchy cross-schema index retry contract passed"
