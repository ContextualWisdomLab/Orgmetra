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

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
CREATE ROLE ${PROBE_ROLE}
    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT USAGE ON SCHEMA public TO ${PROBE_ROLE};
SQL

acl_state="$(psql "${DATABASE_URL}" -Atq -v ON_ERROR_STOP=1 -c "
SELECT
    pg_catalog.has_function_privilege(
        '${PROBE_ROLE}',
        '${FUNCTION_SIGNATURE}',
        'EXECUTE'
    )::text || '|' ||
    pg_catalog.has_function_privilege(
        pg_catalog.current_user,
        '${FUNCTION_SIGNATURE}',
        'EXECUTE'
    )::text;
")"
if [[ "${acl_state}" != "false|true" ]]; then
    echo "document-record persistence function ACL is not deny-by-default for non-owner roles: ${acl_state}" >&2
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
