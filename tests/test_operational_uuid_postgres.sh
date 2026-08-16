#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0002_sealed_evidence_digest.sql

uncovered_uuid_columns="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM pg_class relation
JOIN pg_namespace namespace ON namespace.oid = relation.relnamespace
JOIN pg_attribute attribute ON attribute.attrelid = relation.oid
WHERE namespace.nspname = current_schema()
  AND relation.relkind = 'r'
  AND attribute.attnum > 0
  AND NOT attribute.attisdropped
  AND attribute.atttypid = 'uuid'::regtype
  AND attribute.attname LIKE '%\\_id' ESCAPE '\\'
  AND NOT EXISTS (
      SELECT 1
      FROM pg_constraint constraint_record
      WHERE constraint_record.conrelid = relation.oid
        AND constraint_record.contype = 'c'
        AND attribute.attnum = ANY (constraint_record.conkey)
        AND pg_get_expr(constraint_record.conbin, constraint_record.conrelid)
            LIKE 'is_operational_uuid(%'
  );
")"
if [[ "${uncovered_uuid_columns}" != "0" ]]; then
    echo "foundation contains ${uncovered_uuid_columns} UUID identity columns without the operational UUID sentinel guard" >&2
    exit 1
fi

assert_reserved_tenant_rejected() {
    local tenant_id="$1"
    local tenant_reference="$2"
    local expected_label="$3"
    local output
    local status

    set +e
    output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
        -v tenant_id="${tenant_id}" \
        -v tenant_reference="${tenant_reference}" <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES (:'tenant_id'::uuid, :'tenant_reference');
SQL
    } 2>&1)"
    status=$?
    set -e

    if [[ ${status} -eq 0 || "${output}" != *"operational_uuid_"* ]]; then
        echo "${expected_label} escaped tenant identity validation or failed for the wrong reason: ${output}" >&2
        exit 1
    fi
}

assert_reserved_tenant_rejected \
    '00000000-0000-0000-0000-000000000000' \
    'tenant_reserved_nil' \
    'RFC 9562 Nil UUID'
assert_reserved_tenant_rejected \
    'ffffffff-ffff-ffff-ffff-ffffffffffff' \
    'tenant_reserved_max' \
    'RFC 9562 Max UUID'

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('10000000-0000-7000-8000-000000000001', 'tenant_alpha');
SQL

assert_reserved_person_rejected() {
    local person_id="$1"
    local expected_label="$2"
    local output
    local status

    set +e
    output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v person_id="${person_id}" <<'SQL'
INSERT INTO person_record (tenant_record_id, person_record_id)
VALUES ('10000000-0000-7000-8000-000000000001', :'person_id'::uuid);
SQL
    } 2>&1)"
    status=$?
    set -e

    if [[ ${status} -eq 0 || "${output}" != *"operational_uuid_"* ]]; then
        echo "${expected_label} escaped person identity validation or failed for the wrong reason: ${output}" >&2
        exit 1
    fi
}

assert_reserved_person_rejected \
    '00000000-0000-0000-0000-000000000000' \
    'RFC 9562 Nil UUID'
assert_reserved_person_rejected \
    'ffffffff-ffff-ffff-ffff-ffffffffffff' \
    'RFC 9562 Max UUID'

echo "PostgreSQL operational UUID sentinel contract passed"
