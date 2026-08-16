#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"
TENANT_ID='10000000-0000-7000-8000-000000000001'

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('10000000-0000-7000-8000-000000000001', 'tenant_alpha');
INSERT INTO person_record (tenant_record_id, person_record_id)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000001'
);
INSERT INTO organization_unit (tenant_record_id, organization_unit_id)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000006'
);
INSERT INTO job_profile (tenant_record_id, job_profile_id)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000007'
);
SQL

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL' &
BEGIN;
INSERT INTO organization_unit_version (
    tenant_record_id, organization_unit_version_id, organization_unit_id, unit_name,
    organization_type_code, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000013',
    '00000000-0000-7000-8000-000000000006',
    'People', 'department', DATE '2026-01-01',
    TIMESTAMPTZ '2026-01-02 00:00:00+00'
);
SELECT pg_sleep(2);
COMMIT;
SQL
writer_pid=$!
sleep 0.5

set +e
conflict_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
SET statement_timeout = '5s';
INSERT INTO organization_unit_version (
    tenant_record_id, organization_unit_version_id, organization_unit_id, unit_name,
    organization_type_code, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000014',
    '00000000-0000-7000-8000-000000000006',
    'People and Culture', 'department', DATE '2026-01-01',
    TIMESTAMPTZ '2026-01-03 00:00:00+00'
);
SQL
} 2>&1)"
conflict_status=$?
set -e
wait "${writer_pid}"

if [[ ${conflict_status} -eq 0 ]]; then
    echo "overlapping concurrent bitemporal version unexpectedly succeeded" >&2
    exit 1
fi
if [[ "${conflict_output}" != *"organization_unit_bitemporal_exclusion"* ]]; then
    echo "concurrent conflict failed for an unexpected reason: ${conflict_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;
UPDATE organization_unit_version
SET recorded_to = TIMESTAMPTZ '2026-02-01 00:00:00+00'
WHERE tenant_record_id = '10000000-0000-7000-8000-000000000001'
  AND organization_unit_version_id = '00000000-0000-7000-8000-000000000013';
INSERT INTO organization_unit_version (
    tenant_record_id, organization_unit_version_id, organization_unit_id, unit_name,
    organization_type_code, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000015',
    '00000000-0000-7000-8000-000000000006',
    'People and Culture', 'department', DATE '2026-01-01',
    TIMESTAMPTZ '2026-02-01 00:00:00+00'
);
COMMIT;
SQL

visible_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*) FROM organization_unit_version
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND organization_unit_id = '00000000-0000-7000-8000-000000000006'
  AND daterange(effective_from, effective_to, '[)') @> DATE '2026-01-15'
  AND tstzrange(recorded_from, recorded_to, '[)') @> TIMESTAMPTZ '2026-02-02 00:00:00+00';
")"
if [[ "${visible_count}" != "1" ]]; then
    echo "expected one organization version at one effective/knowledge coordinate, got ${visible_count}" >&2
    exit 1
fi

set +e
mutation_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
UPDATE organization_unit_version SET unit_name = 'Silent rewrite'
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND organization_unit_version_id = '00000000-0000-7000-8000-000000000015';
"; } 2>&1)"
mutation_status=$?
set -e
if [[ ${mutation_status} -eq 0 ]]; then
    echo "in-place bitemporal business mutation unexpectedly succeeded" >&2
    exit 1
fi
if [[ "${mutation_output}" != *"bitemporal correction may only close an open recorded interval"* ]]; then
    echo "business mutation failed for an unexpected reason: ${mutation_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO person_name_record (
    tenant_record_id, person_name_record_id, person_record_id, display_name,
    effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000011',
    '00000000-0000-7000-8000-000000000001',
    'Ada Lovelace', DATE '2026-01-01', TIMESTAMPTZ '2026-01-02 00:00:00+00'
);
INSERT INTO job_profile_version (
    tenant_record_id, job_profile_version_id, job_profile_id, job_title, job_family_code,
    job_version_code, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000016',
    '00000000-0000-7000-8000-000000000007',
    'Principal AI Product Architect', 'product', '2026.1', DATE '2026-01-01',
    TIMESTAMPTZ '2026-01-02 00:00:00+00'
);
SQL

echo "PostgreSQL bitemporal concurrency contract passed"
