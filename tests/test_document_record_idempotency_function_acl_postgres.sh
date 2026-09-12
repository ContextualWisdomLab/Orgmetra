#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

for migration in \
    database/migrations/0001_foundation_schema.sql \
    database/migrations/0002_sealed_evidence_digest.sql \
    database/migrations/0021_document_record_persistence.sql \
    database/migrations/0022_document_record_evidence_unique_keys.sql \
    database/migrations/0023_document_record_canonical_encoding.sql \
    database/migrations/0024_document_record_idempotent_persistence.sql; do
    if [[ ! -f "${migration}" ]]; then
        echo "required document-record idempotency migration is missing: ${migration}" >&2
        exit 1
    fi
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

FUNCTION_OWNER_ROLE="orgmetra_document_persistence_owner"
FUNCTION_EXECUTOR_ROLE="orgmetra_document_persistence_executor"
PROBE_ROLE_SUFFIX="$(python3 - <<'PY'
import uuid

print(uuid.uuid4().hex[:24])
PY
)"
PROBE_ROLE="orgmetra_document_persist_acl_probe_${PROBE_ROLE_SUFFIX}"
FUNCTION_SIGNATURE="public.persist_document_record_once(uuid,text,uuid,text,text,text,text,text,text,text,text,text,text,text,timestamptz,text,text,text,text,text)"

cleanup_probe_role() {
    local mode="${1:-strict}"
    local role_exists

    if ! role_exists="$(psql "${DATABASE_URL}" -Atq -v ON_ERROR_STOP=1 -c \
        "SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = '${PROBE_ROLE}';" 2>/dev/null)"; then
        if [[ "${mode}" == "best-effort" ]]; then
            return 0
        fi
        echo "could not verify temporary function-ACL probe-role cleanup" >&2
        return 1
    fi
    if [[ "${role_exists}" != "1" ]]; then
        return 0
    fi
    if psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 >/dev/null 2>&1 <<SQL
DROP OWNED BY ${PROBE_ROLE};
DROP ROLE ${PROBE_ROLE};
SQL
    then
        return 0
    fi
    if [[ "${mode}" == "best-effort" ]]; then
        return 0
    fi
    echo "could not remove temporary function-ACL probe role ${PROBE_ROLE}" >&2
    return 1
}

cleanup() {
    cleanup_probe_role best-effort
}
trap cleanup EXIT

capability_role_state="$(psql "${DATABASE_URL}" -Atq -v ON_ERROR_STOP=1 -c "
SELECT
    owner_role.rolcanlogin::text || '|' ||
    owner_role.rolsuper::text || '|' ||
    owner_role.rolcreatedb::text || '|' ||
    owner_role.rolcreaterole::text || '|' ||
    owner_role.rolreplication::text || '|' ||
    owner_role.rolbypassrls::text || '|' ||
    executor_role.rolcanlogin::text || '|' ||
    executor_role.rolsuper::text || '|' ||
    executor_role.rolcreatedb::text || '|' ||
    executor_role.rolcreaterole::text || '|' ||
    executor_role.rolreplication::text || '|' ||
    executor_role.rolbypassrls::text
FROM pg_catalog.pg_roles AS owner_role
JOIN pg_catalog.pg_roles AS executor_role
  ON executor_role.rolname = '${FUNCTION_EXECUTOR_ROLE}'
WHERE owner_role.rolname = '${FUNCTION_OWNER_ROLE}';
")"
if [[ "${capability_role_state}" != "false|false|false|false|false|false|false|false|false|false|false|false" ]]; then
    echo "document persistence capability roles are missing or not deny-default NOLOGIN/NOBYPASSRLS roles: ${capability_role_state}" >&2
    exit 1
fi

function_authority_state="$(psql "${DATABASE_URL}" -Atq -v ON_ERROR_STOP=1 -c "
SELECT
    function_owner.rolname || '|' ||
    function_record.prosecdef::text || '|' ||
    pg_catalog.has_schema_privilege('${FUNCTION_OWNER_ROLE}', 'public', 'USAGE')::text || '|' ||
    pg_catalog.has_schema_privilege('${FUNCTION_OWNER_ROLE}', 'public', 'CREATE')::text || '|' ||
    pg_catalog.has_schema_privilege('${FUNCTION_EXECUTOR_ROLE}', 'public', 'USAGE')::text || '|' ||
    pg_catalog.has_schema_privilege('${FUNCTION_EXECUTOR_ROLE}', 'public', 'CREATE')::text || '|' ||
    pg_catalog.has_function_privilege('${FUNCTION_OWNER_ROLE}', '${FUNCTION_SIGNATURE}', 'EXECUTE')::text || '|' ||
    pg_catalog.has_function_privilege('${FUNCTION_EXECUTOR_ROLE}', '${FUNCTION_SIGNATURE}', 'EXECUTE')::text
FROM pg_catalog.pg_proc AS function_record
JOIN pg_catalog.pg_roles AS function_owner
  ON function_owner.oid = function_record.proowner
WHERE function_record.oid = '${FUNCTION_SIGNATURE}'::pg_catalog.regprocedure;
")"
if [[ "${function_authority_state}" != "${FUNCTION_OWNER_ROLE}|true|true|false|true|false|true|true" ]]; then
    echo "document persistence function is not a purpose-bound SECURITY DEFINER capability: ${function_authority_state}" >&2
    exit 1
fi

owner_table_state="$(psql "${DATABASE_URL}" -Atq -v ON_ERROR_STOP=1 -c "
SELECT
    pg_catalog.has_table_privilege('${FUNCTION_OWNER_ROLE}', 'public.document_record', 'SELECT')::text || '|' ||
    pg_catalog.has_table_privilege('${FUNCTION_OWNER_ROLE}', 'public.document_record', 'INSERT')::text || '|' ||
    pg_catalog.has_table_privilege('${FUNCTION_OWNER_ROLE}', 'public.document_record', 'UPDATE')::text || '|' ||
    pg_catalog.has_table_privilege('${FUNCTION_OWNER_ROLE}', 'public.document_record', 'DELETE')::text || '|' ||
    pg_catalog.has_table_privilege('${FUNCTION_OWNER_ROLE}', 'public.document_record', 'TRUNCATE')::text || '|' ||
    pg_catalog.has_table_privilege('${FUNCTION_OWNER_ROLE}', 'public.document_record_persist_receipt', 'SELECT')::text || '|' ||
    pg_catalog.has_table_privilege('${FUNCTION_OWNER_ROLE}', 'public.document_record_persist_receipt', 'INSERT')::text || '|' ||
    pg_catalog.has_table_privilege('${FUNCTION_OWNER_ROLE}', 'public.document_record_persist_receipt', 'UPDATE')::text || '|' ||
    pg_catalog.has_table_privilege('${FUNCTION_OWNER_ROLE}', 'public.document_record_persist_receipt', 'DELETE')::text || '|' ||
    pg_catalog.has_table_privilege('${FUNCTION_OWNER_ROLE}', 'public.document_record_persist_receipt', 'TRUNCATE')::text;
")"
if [[ "${owner_table_state}" != "true|true|false|false|false|true|true|false|false|false" ]]; then
    echo "document persistence function owner has an unexpected direct-table privilege set: ${owner_table_state}" >&2
    exit 1
fi

executor_table_state="$(psql "${DATABASE_URL}" -Atq -v ON_ERROR_STOP=1 -c "
SELECT
    pg_catalog.has_table_privilege('${FUNCTION_EXECUTOR_ROLE}', 'public.document_record', 'SELECT')::text || '|' ||
    pg_catalog.has_table_privilege('${FUNCTION_EXECUTOR_ROLE}', 'public.document_record', 'INSERT')::text || '|' ||
    pg_catalog.has_table_privilege('${FUNCTION_EXECUTOR_ROLE}', 'public.document_record', 'UPDATE')::text || '|' ||
    pg_catalog.has_table_privilege('${FUNCTION_EXECUTOR_ROLE}', 'public.document_record', 'DELETE')::text || '|' ||
    pg_catalog.has_table_privilege('${FUNCTION_EXECUTOR_ROLE}', 'public.document_record', 'TRUNCATE')::text || '|' ||
    pg_catalog.has_table_privilege('${FUNCTION_EXECUTOR_ROLE}', 'public.document_record_persist_receipt', 'SELECT')::text || '|' ||
    pg_catalog.has_table_privilege('${FUNCTION_EXECUTOR_ROLE}', 'public.document_record_persist_receipt', 'INSERT')::text || '|' ||
    pg_catalog.has_table_privilege('${FUNCTION_EXECUTOR_ROLE}', 'public.document_record_persist_receipt', 'UPDATE')::text || '|' ||
    pg_catalog.has_table_privilege('${FUNCTION_EXECUTOR_ROLE}', 'public.document_record_persist_receipt', 'DELETE')::text || '|' ||
    pg_catalog.has_table_privilege('${FUNCTION_EXECUTOR_ROLE}', 'public.document_record_persist_receipt', 'TRUNCATE')::text;
")"
if [[ "${executor_table_state}" != "false|false|false|false|false|false|false|false|false|false" ]]; then
    echo "document persistence executor can bypass the function through direct table privileges: ${executor_table_state}" >&2
    exit 1
fi

set +e
executor_direct_table_output="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 2>&1 <<SQL
SET ROLE ${FUNCTION_EXECUTOR_ROLE};
SELECT count(*) FROM public.document_record;
SQL
)"
executor_direct_table_status=$?
set -e
if [[ ${executor_direct_table_status} -eq 0 || "${executor_direct_table_output}" != *"permission denied for table document_record"* ]]; then
    echo "document persistence executor unexpectedly reached document_record directly: ${executor_direct_table_output}" >&2
    exit 1
fi

set +e
executor_function_output="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 2>&1 <<SQL
SET ROLE ${FUNCTION_EXECUTOR_ROLE};
SELECT *
FROM public.persist_document_record_once(
    NULL::uuid,
    NULL::text,
    NULL::uuid,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::timestamptz,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::text
);
SQL
)"
executor_function_status=$?
set -e
if [[ ${executor_function_status} -eq 0 || "${executor_function_output}" != *"document persistence command cannot contain null authoritative fields"* ]]; then
    echo "document persistence executor did not reach the reviewed function body through EXECUTE-only authority: ${executor_function_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
CREATE ROLE ${PROBE_ROLE}
    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT USAGE ON SCHEMA public TO ${PROBE_ROLE};
SQL

probe_acl_state="$(psql "${DATABASE_URL}" -Atq -v ON_ERROR_STOP=1 -c "
SELECT pg_catalog.has_function_privilege(
    '${PROBE_ROLE}',
    '${FUNCTION_SIGNATURE}',
    'EXECUTE'
)::text;
")"
if [[ "${probe_acl_state}" != "false" ]]; then
    echo "unprivileged probe role unexpectedly inherited document persistence EXECUTE: ${probe_acl_state}" >&2
    exit 1
fi

set +e
probe_output="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 2>&1 <<SQL
SET ROLE ${PROBE_ROLE};
SELECT *
FROM public.persist_document_record_once(
    NULL::uuid,
    NULL::text,
    NULL::uuid,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::timestamptz,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::text,
    NULL::text
);
SQL
)"
probe_status=$?
set -e
if [[ ${probe_status} -eq 0 || "${probe_output}" != *"permission denied for function persist_document_record_once"* ]]; then
    echo "unprivileged role reached the persistence function body instead of failing at EXECUTE authorization: ${probe_output}" >&2
    exit 1
fi

cleanup_probe_role strict
trap - EXIT
