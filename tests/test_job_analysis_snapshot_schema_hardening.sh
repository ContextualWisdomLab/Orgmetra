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

echo "job-analysis PostgreSQL schema hardening contract passed"
