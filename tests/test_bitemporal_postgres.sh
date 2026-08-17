#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"
TENANT_ID='10000000-0000-7000-8000-000000000001'

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0002_sealed_evidence_digest.sql

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('10000000-0000-7000-8000-000000000001', 'tenant_alpha');
INSERT INTO person_record (tenant_record_id, person_record_id)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000001'
);
INSERT INTO employment_record (
    tenant_record_id, employment_record_id, person_record_id
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000002',
    '00000000-0000-7000-8000-000000000001'
);
INSERT INTO employment_record_version (
    tenant_record_id, employment_record_version_id, employment_record_id,
    employment_status_code, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000021',
    '00000000-0000-7000-8000-000000000002',
    'active', DATE '2026-01-01', TIMESTAMPTZ '2026-01-02 00:00:00+00'
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

PGAPPNAME=orgmetra_bitemporal_writer psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL' &
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

writer_ready=false
for _ in $(seq 1 80); do
    writer_state="$(psql "${DATABASE_URL}" -Atqc "
        SELECT count(*)
        FROM pg_stat_activity
        WHERE application_name = 'orgmetra_bitemporal_writer'
          AND wait_event = 'PgSleep';
    ")"
    if [[ "${writer_state}" == "1" ]]; then
        writer_ready=true
        break
    fi
    sleep 0.05
done
if [[ "${writer_ready}" != "true" ]]; then
    set +e
    wait "${writer_pid}"
    writer_status=$?
    set -e
    echo "concurrent writer never became observable; exit_status=${writer_status}" >&2
    exit 1
fi

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
wait "${writer_pid}"
writer_status=$?
set -e

if [[ ${writer_status} -ne 0 ]]; then
    echo "concurrent fixture writer failed unexpectedly with status ${writer_status}" >&2
    exit 1
fi
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

set +e
employment_mutation_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
UPDATE employment_record_version SET employment_status_code = 'terminated'
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND employment_record_version_id = '00000000-0000-7000-8000-000000000021';
"; } 2>&1)"
employment_mutation_status=$?
set -e
if [[ ${employment_mutation_status} -eq 0 ]]; then
    echo "employment bitemporal business mutation unexpectedly succeeded" >&2
    exit 1
fi
if [[ "${employment_mutation_output}" != *"bitemporal correction may only close an open recorded interval"* ]]; then
    echo "employment mutation failed for an unexpected reason: ${employment_mutation_output}" >&2
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

set +e
overlap_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO employment_record_version (
    tenant_record_id, employment_record_version_id, employment_record_id,
    employment_status_code, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000022',
    '00000000-0000-7000-8000-000000000002',
    'leave', DATE '2026-01-01', TIMESTAMPTZ '2026-01-03 00:00:00+00'
);
SQL
} 2>&1)"
overlap_status=$?
set -e
if [[ ${overlap_status} -eq 0 ]]; then
    echo "overlapping employment versions unexpectedly succeeded" >&2
    exit 1
fi
if [[ "${overlap_output}" != *"employment_record_bitemporal_exclusion"* ]]; then
    echo "employment overlap failed for an unexpected reason: ${overlap_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_profile (
    tenant_record_id, candidate_profile_id, application_status_code, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000031',
    'offer', TIMESTAMPTZ '2026-03-01 00:00:00+00'
);
SQL

set +e
candidate_link_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO candidate_worker_link (
    tenant_record_id, candidate_worker_link_id, candidate_profile_id, person_record_id, linked_at
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000032',
    '00000000-0000-7000-8000-000000000031',
    '00000000-0000-7000-8000-000000000001',
    TIMESTAMPTZ '2026-03-02 00:00:00+00'
);
SQL
} 2>&1)"
candidate_link_status=$?
set -e
if [[ ${candidate_link_status} -eq 0 ]]; then
    echo "ungoverned candidate-to-worker link unexpectedly succeeded" >&2
    exit 1
fi
if [[ "${candidate_link_output}" != *"candidate_worker_link is legacy-only"* ]]; then
    echo "candidate link failed for an unexpected reason: ${candidate_link_output}" >&2
    exit 1
fi

echo "PostgreSQL bitemporal concurrency contract passed"
