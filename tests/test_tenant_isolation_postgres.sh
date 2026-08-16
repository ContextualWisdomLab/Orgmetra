#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES
  ('10000000-0000-7000-8000-000000000001', 'tenant_alpha'),
  ('20000000-0000-7000-8000-000000000001', 'tenant_beta');

INSERT INTO person_record (tenant_record_id, person_record_id)
VALUES ('10000000-0000-7000-8000-000000000001', '00000000-0000-7000-8000-000000000001');
SQL

set +e
cross_tenant_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO employment_record (
    tenant_record_id, employment_record_id, person_record_id,
    employment_status_code, effective_from
) VALUES (
    '20000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000003',
    '00000000-0000-7000-8000-000000000001',
    'active', DATE '2026-01-01'
);
SQL
} 2>&1)"
cross_tenant_status=$?
set -e
if [[ ${cross_tenant_status} -eq 0 ]]; then
    echo "cross-tenant foreign-key reference unexpectedly succeeded" >&2
    exit 1
fi
if [[ "${cross_tenant_output}" != *"foreign key constraint"* ]]; then
    echo "cross-tenant write failed for an unexpected reason: ${cross_tenant_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
CREATE ROLE orgmetra_tenant_reader;
GRANT SELECT ON tenant_record, person_record TO orgmetra_tenant_reader;
SET ROLE orgmetra_tenant_reader;
SET orgmetra.tenant_record_id = '10000000-0000-7000-8000-000000000001';
DO $$
BEGIN
    IF (SELECT count(*) FROM person_record) <> 1 THEN
        RAISE EXCEPTION 'tenant alpha should see exactly its own person row';
    END IF;
END;
$$;
SET orgmetra.tenant_record_id = '20000000-0000-7000-8000-000000000001';
DO $$
BEGIN
    IF (SELECT count(*) FROM person_record) <> 0 THEN
        RAISE EXCEPTION 'tenant beta observed tenant alpha person row';
    END IF;
END;
$$;
RESET ROLE;
SQL

echo "PostgreSQL tenant-isolation contract passed"
