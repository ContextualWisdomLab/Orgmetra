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

set +e
repeatable_read_output="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 2>&1 <<'SQL'
BEGIN ISOLATION LEVEL REPEATABLE READ;
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
ROLLBACK;
SQL
)"
repeatable_read_status=$?
set -e

if [[ ${repeatable_read_status} -eq 0 \
      || "${repeatable_read_output}" != *"document persistence idempotency requires read committed transaction isolation"* ]]; then
    echo "document-record replay boundary did not fail closed under REPEATABLE READ: ${repeatable_read_output}" >&2
    exit 1
fi

read_committed="$(psql "${DATABASE_URL}" -Atqc "SHOW transaction_isolation;")"
if [[ "${read_committed}" != "read committed" ]]; then
    echo "Foundation PostgreSQL acceptance does not exercise the supported retry isolation: ${read_committed}" >&2
    exit 1
fi
