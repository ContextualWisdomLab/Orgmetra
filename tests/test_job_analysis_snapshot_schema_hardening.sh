#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

TENANT_ID="10000000-0000-7000-8000-000000000001"
OTHER_TENANT_ID="20000000-0000-7000-8000-000000000002"
ANALYSIS_ID="00000000-0000-7000-8000-000000000081"
LINK_PROBE_TASK_ID="00000000-0000-7000-8000-000000000182"
LINK_PROBE_KSAO_ID="00000000-0000-7000-8000-000000000183"
CROSS_TENANT_TASK_ID="00000000-0000-7000-8000-000000000282"
CROSS_TENANT_KSAO_ID="00000000-0000-7000-8000-000000000283"
CROSS_TENANT_COMMAND_ID="00000000-0000-7000-8000-000000000287"

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
CREATE ROLE orgmetra_rls_probe
    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
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
# another tenant. Require one and only one PUBLIC permissive policy, command ALL,
# and exact normalized USING/WITH CHECK expressions; a role-scoped policy could
# otherwise default-deny the probe role and produce a false-green isolation test.
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

    child_policy_state="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT
    count(*) FILTER (WHERE polpermissive)::text || ':' ||
    count(*) FILTER (
        WHERE polpermissive
          AND polcmd = '*'
          AND polroles = ARRAY[0::oid]
          AND regexp_replace(
              coalesce(pg_get_expr(polqual, polrelid), ''),
              '[[:space:]()]', '', 'g'
          ) = 'tenant_record_id=current_tenant_record_id'
          AND regexp_replace(
              coalesce(pg_get_expr(polwithcheck, polrelid), ''),
              '[[:space:]()]', '', 'g'
          ) = 'tenant_record_id=current_tenant_record_id'
    )::text
FROM pg_policy
WHERE polrelid = '${child_table}'::regclass;
")"
    if [[ "${child_policy_state}" != "1:1" ]]; then
        echo "${child_table} must have exactly one PUBLIC permissive ALL tenant policy with exact USING/WITH CHECK expressions: ${child_policy_state}" >&2
        exit 1
    fi
done

# Give the link write probe a fresh, constraint-valid task/KSAO pair. These are
# legitimate tenant rows seeded by the authorized tenant; the cross-tenant role
# later attempts only the missing link between them.
tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO job_analysis_task_item (
    tenant_record_id, analysis_record_id, task_record_id, task_statement,
    importance_level, difficulty_level, source_uri, source_title,
    source_version_code, retrieved_at, content_digest_sha256, origin_code
)
SELECT
    tenant_record_id, analysis_record_id, '${LINK_PROBE_TASK_ID}'::uuid,
    task_statement, importance_level, difficulty_level, source_uri, source_title,
    source_version_code, retrieved_at, content_digest_sha256, origin_code
FROM job_analysis_task_item
WHERE task_record_id = '00000000-0000-7000-8000-000000000082'::uuid;

INSERT INTO job_analysis_ksao_item (
    tenant_record_id, analysis_record_id, ksao_record_id, category_code,
    requirement_statement, importance_level, proficiency_level, source_uri,
    source_title, source_version_code, retrieved_at, content_digest_sha256,
    origin_code
)
SELECT
    tenant_record_id, analysis_record_id, '${LINK_PROBE_KSAO_ID}'::uuid,
    category_code, requirement_statement, importance_level, proficiency_level,
    source_uri, source_title, source_version_code, retrieved_at,
    content_digest_sha256, origin_code
FROM job_analysis_ksao_item
WHERE ksao_record_id = '00000000-0000-7000-8000-000000000083'::uuid;
SQL

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
        "GRANT SELECT, INSERT ON ${child_table} TO orgmetra_rls_probe;" >/dev/null

    other_tenant_child_rows="$(PGOPTIONS="-c orgmetra.tenant_record_id=${OTHER_TENANT_ID}" \
        psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc \
        "SET ROLE orgmetra_rls_probe; SELECT count(*) FROM ${child_table};")"
    if [[ "${other_tenant_child_rows}" != "0" ]]; then
        echo "row-level security leaked ${other_tenant_child_rows} ${child_table} row(s) across tenants" >&2
        exit 1
    fi

    case "${child_table}" in
        job_analysis_task_item)
            cross_tenant_insert_sql="
INSERT INTO job_analysis_task_item (
    tenant_record_id, analysis_record_id, task_record_id, task_statement,
    importance_level, difficulty_level, source_uri, source_title,
    source_version_code, retrieved_at, content_digest_sha256, origin_code
) VALUES (
    '${TENANT_ID}', '${ANALYSIS_ID}', '${CROSS_TENANT_TASK_ID}',
    'Cross-tenant RLS write probe', 1, 1, 'https://example.invalid/rls-probe',
    'RLS write probe', 'probe:v1', TIMESTAMPTZ '2026-09-11 00:00:00+00',
    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    'contract_probe'
);"
            ;;
        job_analysis_ksao_item)
            cross_tenant_insert_sql="
INSERT INTO job_analysis_ksao_item (
    tenant_record_id, analysis_record_id, ksao_record_id, category_code,
    requirement_statement, importance_level, proficiency_level, source_uri,
    source_title, source_version_code, retrieved_at, content_digest_sha256,
    origin_code
) VALUES (
    '${TENANT_ID}', '${ANALYSIS_ID}', '${CROSS_TENANT_KSAO_ID}',
    'knowledge_requirement', 'Cross-tenant RLS write probe', 1, 1,
    'https://example.invalid/rls-probe', 'RLS write probe', 'probe:v1',
    TIMESTAMPTZ '2026-09-11 00:00:00+00',
    'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
    'contract_probe'
);"
            ;;
        job_analysis_task_ksao_link)
            cross_tenant_insert_sql="
INSERT INTO job_analysis_task_ksao_link (
    tenant_record_id, analysis_record_id, task_record_id, ksao_record_id,
    relationship_strength, essential_for_task
) VALUES (
    '${TENANT_ID}', '${ANALYSIS_ID}', '${LINK_PROBE_TASK_ID}',
    '${LINK_PROBE_KSAO_ID}', 1, FALSE
);"
            ;;
        job_analysis_write_command)
            cross_tenant_insert_sql="
INSERT INTO job_analysis_write_command (
    tenant_record_id, write_command_id, analysis_record_id, idempotency_key,
    request_digest_sha256, actor_reference, purpose_code
) VALUES (
    '${TENANT_ID}', '${CROSS_TENANT_COMMAND_ID}', '${ANALYSIS_ID}',
    'cross-tenant-rls-probe-01',
    'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc',
    'keyverse_subject:rls_probe', 'job_analysis_write'
);"
            ;;
        *)
            echo "unhandled child table in cross-tenant INSERT probe: ${child_table}" >&2
            exit 1
            ;;
    esac

    set +e
    cross_tenant_insert_output="$({ \
        PGOPTIONS="-c orgmetra.tenant_record_id=${OTHER_TENANT_ID}" \
        psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c \
        "SET ROLE orgmetra_rls_probe; ${cross_tenant_insert_sql}" ; \
    } 2>&1)"
    cross_tenant_insert_status=$?
    set -e
    if [[ ${cross_tenant_insert_status} -eq 0 \
        || "${cross_tenant_insert_output}" != *"row-level security"* ]]; then
        echo "${child_table} cross-tenant INSERT was not rejected by RLS WITH CHECK: ${cross_tenant_insert_output}" >&2
        exit 1
    fi
done

echo "job-analysis PostgreSQL schema hardening contract passed"