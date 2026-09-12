#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"
TENANT_ID='10000000-0000-7000-8000-000000000001'

for migration in \
    database/migrations/0001_foundation_schema.sql \
    database/migrations/0002_sealed_evidence_digest.sql \
    database/migrations/0003_audit_outbox_persistence.sql \
    database/migrations/0004_outbox_delivery_claim.sql \
    database/migrations/0005_outbox_delivery_finalization.sql \
    database/migrations/0006_outbox_delivery_dead_letter.sql \
    database/migrations/0007_outbox_retry_exhaustion.sql \
    database/migrations/0008_audit_outbox_review_hardening.sql \
    database/migrations/0009_candidate_worker_conversion_governance.sql \
    database/migrations/0010_validity_study_case_integrity.sql \
    database/migrations/0011_criterion_observation_scope.sql \
    database/migrations/0012_people_mutation_idempotency.sql \
    database/migrations/0013_job_analysis_snapshot.sql \
    database/migrations/0014_employment_separation_transition.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

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

separation_result="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -AtF '|' <<'SQL'
BEGIN;
SET LOCAL orgmetra.tenant_record_id = '10000000-0000-7000-8000-000000000001';
SELECT
    employment_record_id,
    separated_employment_record_version_id,
    recorded_at,
    replayed
FROM public.separate_employment_record_once(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000002'::uuid,
    '00000000-0000-7000-8000-000000000021'::uuid,
    DATE '2026-06-01',
    'voluntary_resignation',
    'separation_packet:sep-2026-001',
    'v1',
    'keyverse_subject:operator-17',
    'workforce_admin',
    'human_confirmation:separation-17',
    'employment-separation-key-17',
    '00000000-0000-4000-8000-000000000230'::uuid,
    '00000000-0000-4000-8000-000000000231'::uuid
);
COMMIT;
SQL
)"
if [[ "${separation_result}" != 00000000-0000-7000-8000-000000000002\|*\|*\|f ]]; then
    echo "employment separation did not return the first authoritative result: ${separation_result}" >&2
    exit 1
fi
separated_version_id="$(printf '%s' "${separation_result}" | cut -d'|' -f2)"
separation_recorded_at="$(printf '%s' "${separation_result}" | cut -d'|' -f3)"

separation_shape="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -AtF '|' <<SQL
SET orgmetra.tenant_record_id = '${TENANT_ID}';
SELECT concat_ws('|',
    (SELECT count(*) FROM employment_record_version
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND employment_record_id = '00000000-0000-7000-8000-000000000002'::uuid
        AND recorded_to IS NULL),
    (SELECT employment_status_code FROM employment_record_version
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND employment_record_id = '00000000-0000-7000-8000-000000000002'::uuid
        AND recorded_to IS NULL
        AND daterange(effective_from, effective_to, '[)') @> DATE '2026-05-31'),
    (SELECT employment_status_code FROM employment_record_version
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND employment_record_id = '00000000-0000-7000-8000-000000000002'::uuid
        AND recorded_to IS NULL
        AND daterange(effective_from, effective_to, '[)') @> DATE '2026-06-01'),
    (SELECT count(*) FROM employment_separation_record
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND employment_record_id = '00000000-0000-7000-8000-000000000002'::uuid),
    (SELECT count(*) FROM audit_event_record
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND audit_event_record_id = '00000000-0000-4000-8000-000000000230'::uuid
        AND (canonical_event_json::jsonb ->> 'time')::timestamptz = '${separation_recorded_at}'::timestamptz
        AND canonical_event_json::jsonb ->> 'type' = 'orgmetra.people.employment_separated'
        AND canonical_event_json::jsonb #>> '{data,result_code}' = 'employment_separated'),
    (SELECT count(*) FROM people_mutation_idempotency_record
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND command_route = 'employment-separations'
        AND created_record_id = '${separated_version_id}'::uuid)
);
SQL
)"
if [[ "${separation_shape}" != "2|active|terminated|1|1|1" ]]; then
    echo "employment separation did not preserve one current bitemporal history and evidence set: ${separation_shape}" >&2
    exit 1
fi

historic_status="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT employment_status_code
FROM employment_record_version
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND employment_record_id = '00000000-0000-7000-8000-000000000002'::uuid
  AND daterange(effective_from, effective_to, '[)') @> DATE '2026-07-01'
  AND tstzrange(recorded_from, recorded_to, '[)') @> TIMESTAMPTZ '2026-02-01 00:00:00+00';
")"
if [[ "${historic_status}" != "active" ]]; then
    echo "employment separation destroyed pre-separation knowledge history: ${historic_status}" >&2
    exit 1
fi

replay_result="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -AtF '|' <<'SQL'
BEGIN;
SET LOCAL orgmetra.tenant_record_id = '10000000-0000-7000-8000-000000000001';
SELECT
    employment_record_id,
    separated_employment_record_version_id,
    recorded_at,
    replayed
FROM public.separate_employment_record_once(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000002'::uuid,
    '00000000-0000-7000-8000-000000000021'::uuid,
    DATE '2026-06-01',
    'voluntary_resignation',
    'separation_packet:sep-2026-001',
    'v1',
    'keyverse_subject:operator-17',
    'workforce_admin',
    'human_confirmation:separation-17',
    'employment-separation-key-17',
    '00000000-0000-4000-8000-000000000232'::uuid,
    '00000000-0000-4000-8000-000000000233'::uuid
);
COMMIT;
SQL
)"
if [[ "${replay_result}" != "00000000-0000-7000-8000-000000000002|${separated_version_id}|${separation_recorded_at}|t" ]]; then
    echo "matching employment separation retry did not replay the first committed truth: ${replay_result}" >&2
    exit 1
fi

set +e
semantic_conflict_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;
SET LOCAL orgmetra.tenant_record_id = '10000000-0000-7000-8000-000000000001';
SELECT * FROM public.separate_employment_record_once(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000002'::uuid,
    '00000000-0000-7000-8000-000000000021'::uuid,
    DATE '2026-06-02',
    'voluntary_resignation',
    'separation_packet:sep-2026-001',
    'v1',
    'keyverse_subject:operator-17',
    'workforce_admin',
    'human_confirmation:separation-17',
    'employment-separation-key-17',
    '00000000-0000-4000-8000-000000000234'::uuid,
    '00000000-0000-4000-8000-000000000235'::uuid
);
COMMIT;
SQL
} 2>&1)"
semantic_conflict_status=$?
set -e
if [[ ${semantic_conflict_status} -eq 0 ]]; then
    echo "changed employment separation command reused an idempotency key" >&2
    exit 1
fi
if [[ "${semantic_conflict_output}" != *"idempotency key is bound to a different command"* ]]; then
    echo "changed employment separation command failed for an unexpected reason: ${semantic_conflict_output}" >&2
    exit 1
fi

final_counts="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SET orgmetra.tenant_record_id = '${TENANT_ID}';
SELECT concat_ws(',',
    (SELECT count(*) FROM employment_separation_record),
    (SELECT count(*) FROM audit_event_record WHERE canonical_event_json::jsonb ->> 'type' = 'orgmetra.people.employment_separated'),
    (SELECT count(*) FROM people_mutation_idempotency_record WHERE command_route = 'employment-separations')
);
")"
if [[ "${final_counts}" != "1,1,1" ]]; then
    echo "employment separation retry/conflict changed durable truth: ${final_counts}" >&2
    exit 1
fi

echo "PostgreSQL bitemporal concurrency and employment separation contract passed"
