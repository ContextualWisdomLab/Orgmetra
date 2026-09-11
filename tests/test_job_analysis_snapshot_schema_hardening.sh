#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

TENANT_ID="10000000-0000-7000-8000-000000000001"
OTHER_TENANT_ID="20000000-0000-7000-8000-000000000002"
ANALYSIS_ID="00000000-0000-7000-8000-000000000081"

tenant_psql() {
    PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" command psql "$@"
}

set +e
delete_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c \
    "DELETE FROM job_analysis_snapshot WHERE analysis_record_id = '${ANALYSIS_ID}'::uuid;" ; } 2>&1)"
delete_status=$?
set -e
if [[ ${delete_status} -eq 0 || "${delete_output}" != *"append-only"* ]]; then
    echo "job-analysis snapshot DELETE was not rejected by the append-only guard: ${delete_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
CREATE ROLE orgmetra_rls_probe NOLOGIN;
GRANT SELECT ON job_analysis_snapshot TO orgmetra_rls_probe;
SQL

other_tenant_rows="$(PGOPTIONS="-c orgmetra.tenant_record_id=${OTHER_TENANT_ID}" \
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc \
    "SET ROLE orgmetra_rls_probe; SELECT count(*) FROM job_analysis_snapshot;")"
if [[ "${other_tenant_rows}" != "0" ]]; then
    echo "row-level security leaked ${other_tenant_rows} job-analysis snapshot row(s) across tenants" >&2
    exit 1
fi

supporting_index_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM pg_indexes
WHERE schemaname = current_schema()
  AND indexname IN (
      'job_analysis_snapshot_position_idx',
      'job_analysis_snapshot_criterion_idx',
      'job_analysis_write_command_analysis_idx'
  );
")"
if [[ "${supporting_index_count}" != "3" ]]; then
    echo "job-analysis parent/write-command supporting indexes are incomplete: ${supporting_index_count}/3" >&2
    exit 1
fi

redundant_unique_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM pg_constraint
WHERE conname IN (
    'job_analysis_task_item_identity_unique',
    'job_analysis_ksao_item_identity_unique'
);
")"
if [[ "${redundant_unique_count}" != "0" ]]; then
    echo "redundant task/KSAO UNIQUE constraints remain: ${redundant_unique_count}" >&2
    exit 1
fi

# Migration 0013 declares an append-only guard and a tenant RLS policy on every
# child table, not only the root snapshot. Prove the four child tables carry the
# same immutable, tenant-isolated guarantee that the root table is checked for.
child_tables=(
    job_analysis_task_item
    job_analysis_ksao_item
    job_analysis_task_ksao_link
    job_analysis_write_command
)

# Catalog proof first: a missing FORCE-RLS policy would also return zero rows to
# another tenant, so the behavioral check below is only meaningful once each
# child table is confirmed to have ENABLE+FORCE RLS and its scoped policy.
for child_table in "${child_tables[@]}"; do
    child_rls_state="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT c.relrowsecurity::text || ':' || c.relforcerowsecurity::text
FROM pg_class c
WHERE c.oid = '${child_table}'::regclass;
")"
    if [[ "${child_rls_state}" != "true:true" ]]; then
        echo "${child_table} must ENABLE and FORCE row-level security: ${child_rls_state}" >&2
        exit 1
    fi

    child_policy_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM pg_policy
WHERE polrelid = '${child_table}'::regclass
  AND polcmd = '*'
  AND polpermissive
  AND pg_get_expr(polqual, polrelid) LIKE '%current_tenant_record_id()%'
  AND pg_get_expr(polwithcheck, polrelid) LIKE '%current_tenant_record_id()%';
")"
    if [[ "${child_policy_count}" != "1" ]]; then
        echo "${child_table} must have exactly one scoped ALL policy: ${child_policy_count}" >&2
        exit 1
    fi
done

for child_table in "${child_tables[@]}"; do
    child_row_count="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc \
        "SELECT count(*) FROM ${child_table};")"
    if [[ "${child_row_count}" == "0" ]]; then
        echo "${child_table} has no seeded row; the append-only proof would be vacuous" >&2
        exit 1
    fi

    set +e
    child_update_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c \
        "UPDATE ${child_table} SET tenant_record_id = tenant_record_id;" ; } 2>&1)"
    child_update_status=$?
    set -e
    if [[ ${child_update_status} -eq 0 || "${child_update_output}" != *"append-only"* ]]; then
        echo "${child_table} UPDATE was not rejected by the append-only guard: ${child_update_output}" >&2
        exit 1
    fi

    set +e
    child_delete_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c \
        "DELETE FROM ${child_table};" ; } 2>&1)"
    child_delete_status=$?
    set -e
    if [[ ${child_delete_status} -eq 0 || "${child_delete_output}" != *"append-only"* ]]; then
        echo "${child_table} DELETE was not rejected by the append-only guard: ${child_delete_output}" >&2
        exit 1
    fi
done

for child_table in "${child_tables[@]}"; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c \
        "GRANT SELECT ON ${child_table} TO orgmetra_rls_probe;" >/dev/null

    other_tenant_child_rows="$(PGOPTIONS="-c orgmetra.tenant_record_id=${OTHER_TENANT_ID}" \
        psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc \
        "SET ROLE orgmetra_rls_probe; SELECT count(*) FROM ${child_table};")"
    if [[ "${other_tenant_child_rows}" != "0" ]]; then
        echo "row-level security leaked ${other_tenant_child_rows} ${child_table} row(s) across tenants" >&2
        exit 1
    fi
done

echo "job-analysis PostgreSQL schema hardening contract passed"
