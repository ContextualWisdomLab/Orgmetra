#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"
TENANT_ID='10000000-0000-7000-8000-000000000001'
FOREIGN_TENANT_ID='20000000-0000-7000-8000-000000000001'
PERSON_ID='00000000-0000-7000-8000-000000000001'

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

tenant_psql() {
    PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" command psql "$@"
}
foreign_tenant_psql() {
    PGOPTIONS="-c orgmetra.tenant_record_id=${FOREIGN_TENANT_ID}" command psql "$@"
}

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES
    ('10000000-0000-7000-8000-000000000001', 'tenant_alpha'),
    ('20000000-0000-7000-8000-000000000001', 'tenant_beta');

INSERT INTO person_record (tenant_record_id, person_record_id, recorded_from)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000001',
    TIMESTAMPTZ '2026-01-02 00:00:00+00'
);

INSERT INTO employment_record (
    tenant_record_id, employment_record_id, person_record_id, recorded_from
) VALUES
    (
        '10000000-0000-7000-8000-000000000001',
        '00000000-0000-7000-8000-000000000101',
        '00000000-0000-7000-8000-000000000001',
        TIMESTAMPTZ '2026-01-02 00:00:00+00'
    ),
    (
        '10000000-0000-7000-8000-000000000001',
        '00000000-0000-7000-8000-000000000102',
        '00000000-0000-7000-8000-000000000001',
        TIMESTAMPTZ '2026-01-02 00:00:00+00'
    ),
    (
        '10000000-0000-7000-8000-000000000001',
        '00000000-0000-7000-8000-000000000103',
        '00000000-0000-7000-8000-000000000001',
        TIMESTAMPTZ '2026-01-02 00:00:00+00'
    ),
    (
        '10000000-0000-7000-8000-000000000001',
        '00000000-0000-7000-8000-000000000104',
        '00000000-0000-7000-8000-000000000001',
        TIMESTAMPTZ '2026-01-02 00:00:00+00'
    );

INSERT INTO employment_record_version (
    tenant_record_id,
    employment_record_version_id,
    employment_record_id,
    employment_status_code,
    employment_concurrency_code,
    effective_from,
    effective_to,
    recorded_from
) VALUES
    (
        '10000000-0000-7000-8000-000000000001',
        '00000000-0000-7000-8000-000000000201',
        '00000000-0000-7000-8000-000000000101',
        'active', 'exclusive', DATE '2026-01-01', NULL,
        TIMESTAMPTZ '2026-01-02 00:00:00+00'
    ),
    (
        '10000000-0000-7000-8000-000000000001',
        '00000000-0000-7000-8000-000000000202',
        '00000000-0000-7000-8000-000000000102',
        'active', 'concurrent', DATE '2026-01-01', NULL,
        TIMESTAMPTZ '2026-01-02 00:00:00+00'
    ),
    (
        '10000000-0000-7000-8000-000000000001',
        '00000000-0000-7000-8000-000000000203',
        '00000000-0000-7000-8000-000000000103',
        'active', 'concurrent', DATE '2026-01-01', DATE '2026-09-01',
        TIMESTAMPTZ '2026-01-02 00:00:00+00'
    ),
    (
        '10000000-0000-7000-8000-000000000001',
        '00000000-0000-7000-8000-000000000204',
        '00000000-0000-7000-8000-000000000103',
        'leave', 'concurrent', DATE '2026-09-01', NULL,
        TIMESTAMPTZ '2026-01-02 00:00:00+00'
    ),
    (
        '10000000-0000-7000-8000-000000000001',
        '00000000-0000-7000-8000-000000000205',
        '00000000-0000-7000-8000-000000000104',
        'active', 'concurrent', DATE '2026-01-01', NULL,
        TIMESTAMPTZ '2026-01-02 00:00:00+00'
    );

INSERT INTO organization_unit (tenant_record_id, organization_unit_id, recorded_from)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000301',
    TIMESTAMPTZ '2026-01-02 00:00:00+00'
);
INSERT INTO job_profile (tenant_record_id, job_profile_id, recorded_from)
VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000302',
    TIMESTAMPTZ '2026-01-02 00:00:00+00'
);
INSERT INTO position_record (
    tenant_record_id, position_record_id, organization_unit_id, job_profile_id, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000303',
    '00000000-0000-7000-8000-000000000301',
    '00000000-0000-7000-8000-000000000302',
    TIMESTAMPTZ '2026-01-02 00:00:00+00'
);
INSERT INTO assignment_record (
    tenant_record_id,
    assignment_record_id,
    employment_record_id,
    person_record_id,
    position_record_id,
    allocation_ratio,
    effective_from,
    effective_to,
    recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000401',
    '00000000-0000-7000-8000-000000000104',
    '00000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000303',
    1.0000,
    DATE '2026-01-01',
    NULL,
    TIMESTAMPTZ '2026-01-02 00:00:00+00'
);
SQL

first_result="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -AtqF '|' <<'SQL'
SELECT employment_record_id, separated_employment_record_version_id, recorded_at, replayed
FROM public.separate_employment_record_once(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000101'::uuid,
    '00000000-0000-7000-8000-000000000201'::uuid,
    DATE '2026-06-01',
    'voluntary_resignation',
    'separation_packet:sep-2026-001',
    'v1',
    'keyverse_subject:operator-17',
    'workforce_admin',
    'human_confirmation:separation-17',
    'employment-separation-key-17',
    '00000000-0000-4000-8000-000000000501'::uuid,
    '00000000-0000-4000-8000-000000000601'::uuid
);
SQL
)"
first_employment_id="$(printf '%s' "${first_result}" | cut -d'|' -f1)"
first_version_id="$(printf '%s' "${first_result}" | cut -d'|' -f2)"
first_recorded_at="$(printf '%s' "${first_result}" | cut -d'|' -f3)"
first_replayed="$(printf '%s' "${first_result}" | cut -d'|' -f4)"
if [[ "${first_employment_id}" != "00000000-0000-7000-8000-000000000101" || -z "${first_version_id}" || -z "${first_recorded_at}" || "${first_replayed}" != "f" ]]; then
    echo "first employment separation result is invalid: ${first_result}" >&2
    exit 1
fi

shape="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -AtqF '|' <<SQL
SELECT concat_ws('|',
    (SELECT count(*) FROM public.employment_record_version
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND employment_record_id = '00000000-0000-7000-8000-000000000101'::uuid
        AND recorded_to IS NULL),
    (SELECT employment_status_code FROM public.employment_record_version
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND employment_record_id = '00000000-0000-7000-8000-000000000101'::uuid
        AND recorded_to IS NULL
        AND daterange(effective_from, effective_to, '[)') @> DATE '2026-05-31'),
    (SELECT employment_status_code FROM public.employment_record_version
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND employment_record_id = '00000000-0000-7000-8000-000000000101'::uuid
        AND recorded_to IS NULL
        AND daterange(effective_from, effective_to, '[)') @> DATE '2026-06-01'),
    (SELECT count(*) FROM public.employment_separation_record
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND employment_record_id = '00000000-0000-7000-8000-000000000101'::uuid
        AND separated_employment_record_version_id = '${first_version_id}'::uuid
        AND recorded_at = '${first_recorded_at}'::timestamptz),
    (SELECT count(*) FROM public.audit_event_record
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND audit_event_record_id = '00000000-0000-4000-8000-000000000501'::uuid
        AND (canonical_event_json::jsonb ->> 'time')::timestamptz = '${first_recorded_at}'::timestamptz
        AND canonical_event_json::jsonb ->> 'type' = 'orgmetra.people.employment_separated'
        AND canonical_event_json::jsonb ->> 'subject' = 'employment_record:00000000-0000-7000-8000-000000000101'
        AND canonical_event_json::jsonb #>> '{data,result_code}' = 'employment_separated'),
    (SELECT count(*) FROM public.people_mutation_idempotency_record
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND command_route = 'employment-separations'
        AND created_record_id = '${first_version_id}'::uuid)
);
SQL
)"
if [[ "${shape}" != "2|active|terminated|1|1|1" ]]; then
    echo "employment separation durable shape is invalid: ${shape}" >&2
    exit 1
fi

historic_status="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT employment_status_code
FROM public.employment_record_version
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND employment_record_id = '00000000-0000-7000-8000-000000000101'::uuid
  AND daterange(effective_from, effective_to, '[)') @> DATE '2026-07-01'
  AND tstzrange(recorded_from, recorded_to, '[)') @> TIMESTAMPTZ '2026-02-01 00:00:00+00';
")"
if [[ "${historic_status}" != "active" ]]; then
    echo "separation destroyed earlier knowledge history: ${historic_status}" >&2
    exit 1
fi

replay_result="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -AtqF '|' <<'SQL'
SELECT employment_record_id, separated_employment_record_version_id, recorded_at, replayed
FROM public.separate_employment_record_once(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000101'::uuid,
    '00000000-0000-7000-8000-000000000201'::uuid,
    DATE '2026-06-01',
    'voluntary_resignation',
    'separation_packet:sep-2026-001',
    'v1',
    'keyverse_subject:operator-17',
    'workforce_admin',
    'human_confirmation:separation-17',
    'employment-separation-key-17',
    '00000000-0000-4000-8000-000000000502'::uuid,
    '00000000-0000-4000-8000-000000000602'::uuid
);
SQL
)"
if [[ "${replay_result}" != "${first_employment_id}|${first_version_id}|${first_recorded_at}|t" ]]; then
    echo "matching separation retry did not replay first committed result: ${replay_result}" >&2
    exit 1
fi

set +e
semantic_conflict_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT * FROM public.separate_employment_record_once(
    '${TENANT_ID}'::uuid,
    '${PERSON_ID}'::uuid,
    '00000000-0000-7000-8000-000000000101'::uuid,
    '00000000-0000-7000-8000-000000000201'::uuid,
    DATE '2026-06-02',
    'voluntary_resignation',
    'separation_packet:sep-2026-001',
    'v1',
    'keyverse_subject:operator-17',
    'workforce_admin',
    'human_confirmation:separation-17',
    'employment-separation-key-17',
    '00000000-0000-4000-8000-000000000503'::uuid,
    '00000000-0000-4000-8000-000000000603'::uuid
);"; } 2>&1)"
semantic_conflict_status=$?
set -e
if [[ ${semantic_conflict_status} -eq 0 || "${semantic_conflict_output}" != *"idempotency key is bound to a different command"* ]]; then
    echo "same-key semantic conflict was not rejected correctly: ${semantic_conflict_output}" >&2
    exit 1
fi

set +e
stale_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT * FROM public.separate_employment_record_once(
    '${TENANT_ID}'::uuid,
    '${PERSON_ID}'::uuid,
    '00000000-0000-7000-8000-000000000101'::uuid,
    '00000000-0000-7000-8000-000000000201'::uuid,
    DATE '2026-07-01',
    'voluntary_resignation',
    'separation_packet:sep-2026-002',
    'v1',
    'keyverse_subject:operator-17',
    'workforce_admin',
    'human_confirmation:separation-18',
    'employment-separation-key-18',
    '00000000-0000-4000-8000-000000000504'::uuid,
    '00000000-0000-4000-8000-000000000604'::uuid
);"; } 2>&1)"
stale_status=$?
set -e
if [[ ${stale_status} -eq 0 || "${stale_output}" != *"expected version is stale or unavailable"* ]]; then
    echo "stale expected Employment version was not rejected correctly: ${stale_output}" >&2
    exit 1
fi

set +e
foreign_tenant_output="$({ foreign_tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT * FROM public.separate_employment_record_once(
    '${TENANT_ID}'::uuid,
    '${PERSON_ID}'::uuid,
    '00000000-0000-7000-8000-000000000102'::uuid,
    '00000000-0000-7000-8000-000000000202'::uuid,
    DATE '2026-08-01',
    'voluntary_resignation',
    'separation_packet:sep-foreign',
    'v1',
    'keyverse_subject:operator-17',
    'workforce_admin',
    'human_confirmation:separation-foreign',
    'employment-separation-key-foreign',
    '00000000-0000-4000-8000-000000000505'::uuid,
    '00000000-0000-4000-8000-000000000605'::uuid
);"; } 2>&1)"
foreign_tenant_status=$?
set -e
if [[ ${foreign_tenant_status} -eq 0 || "${foreign_tenant_output}" != *"tenant context does not match command tenant"* ]]; then
    echo "cross-tenant separation was not rejected before mutation: ${foreign_tenant_output}" >&2
    exit 1
fi

set +e
future_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT * FROM public.separate_employment_record_once(
    '${TENANT_ID}'::uuid,
    '${PERSON_ID}'::uuid,
    '00000000-0000-7000-8000-000000000103'::uuid,
    '00000000-0000-7000-8000-000000000203'::uuid,
    DATE '2026-06-01',
    'voluntary_resignation',
    'separation_packet:sep-future',
    'v1',
    'keyverse_subject:operator-17',
    'workforce_admin',
    'human_confirmation:separation-future',
    'employment-separation-key-future',
    '00000000-0000-4000-8000-000000000506'::uuid,
    '00000000-0000-4000-8000-000000000606'::uuid
);"; } 2>&1)"
future_status=$?
set -e
if [[ ${future_status} -eq 0 || "${future_output}" != *"future Employment version coordination"* ]]; then
    echo "future Employment version was not protected from implicit cancellation: ${future_output}" >&2
    exit 1
fi

set +e
assignment_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT * FROM public.separate_employment_record_once(
    '${TENANT_ID}'::uuid,
    '${PERSON_ID}'::uuid,
    '00000000-0000-7000-8000-000000000104'::uuid,
    '00000000-0000-7000-8000-000000000205'::uuid,
    DATE '2026-06-01',
    'voluntary_resignation',
    'separation_packet:sep-assignment',
    'v1',
    'keyverse_subject:operator-17',
    'workforce_admin',
    'human_confirmation:separation-assignment',
    'employment-separation-key-assignment',
    '00000000-0000-4000-8000-000000000507'::uuid,
    '00000000-0000-4000-8000-000000000607'::uuid
);"; } 2>&1)"
assignment_status=$?
set -e
if [[ ${assignment_status} -eq 0 || "${assignment_output}" != *"assignment coordination before termination"* ]]; then
    echo "open Assignment was not protected from implicit termination: ${assignment_output}" >&2
    exit 1
fi

set +e
unreviewed_reason_output="$({ tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT * FROM public.separate_employment_record_once(
    '${TENANT_ID}'::uuid,
    '${PERSON_ID}'::uuid,
    '00000000-0000-7000-8000-000000000102'::uuid,
    '00000000-0000-7000-8000-000000000202'::uuid,
    DATE '2026-08-01',
    'manager_notes_compensation_case',
    'separation_packet:sep-unreviewed-reason',
    'v1',
    'keyverse_subject:operator-17',
    'workforce_admin',
    'human_confirmation:separation-unreviewed-reason',
    'employment-separation-key-unreviewed-reason',
    '00000000-0000-4000-8000-000000000510'::uuid,
    '00000000-0000-4000-8000-000000000610'::uuid
);"; } 2>&1)"
unreviewed_reason_status=$?
set -e
if [[ ${unreviewed_reason_status} -eq 0 || "${unreviewed_reason_output}" != *"reason code is invalid"* ]]; then
    echo "unreviewed separation reason was not rejected before mutation: ${unreviewed_reason_output}" >&2
    exit 1
fi

first_concurrent_output="$(mktemp)"
second_concurrent_output="$(mktemp)"
cleanup() {
    rm -f "${first_concurrent_output}" "${second_concurrent_output}"
}
trap cleanup EXIT

PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
PGAPPNAME='orgmetra_employment_separation_first' \
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -AtqF '|' >"${first_concurrent_output}" <<'SQL' &
BEGIN;
SELECT employment_record_id, separated_employment_record_version_id, recorded_at, replayed
FROM public.separate_employment_record_once(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000102'::uuid,
    '00000000-0000-7000-8000-000000000202'::uuid,
    DATE '2026-08-01',
    'voluntary_resignation',
    'separation_packet:sep-concurrent',
    'v1',
    'keyverse_subject:operator-17',
    'workforce_admin',
    'human_confirmation:separation-concurrent',
    'employment-separation-key-concurrent',
    '00000000-0000-4000-8000-000000000508'::uuid,
    '00000000-0000-4000-8000-000000000608'::uuid
);
SELECT pg_sleep(5);
COMMIT;
SQL
first_pid=$!

first_ready=false
for _ in $(seq 1 80); do
    first_state="$(psql "${DATABASE_URL}" -Atqc "
        SELECT count(*)
        FROM pg_catalog.pg_stat_activity
        WHERE application_name = 'orgmetra_employment_separation_first'
          AND wait_event = 'PgSleep';
    ")"
    if [[ "${first_state}" == "1" ]]; then
        first_ready=true
        break
    fi
    sleep 0.05
done
if [[ "${first_ready}" != "true" ]]; then
    set +e
    wait "${first_pid}"
    first_status=$?
    set -e
    echo "first separation transaction never became observable; exit_status=${first_status}" >&2
    exit 1
fi

PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
PGAPPNAME='orgmetra_employment_separation_second' \
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -AtqF '|' >"${second_concurrent_output}" <<'SQL' &
SET statement_timeout = '10s';
SELECT employment_record_id, separated_employment_record_version_id, recorded_at, replayed
FROM public.separate_employment_record_once(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000102'::uuid,
    '00000000-0000-7000-8000-000000000202'::uuid,
    DATE '2026-08-01',
    'voluntary_resignation',
    'separation_packet:sep-concurrent',
    'v1',
    'keyverse_subject:operator-17',
    'workforce_admin',
    'human_confirmation:separation-concurrent',
    'employment-separation-key-concurrent',
    '00000000-0000-4000-8000-000000000509'::uuid,
    '00000000-0000-4000-8000-000000000609'::uuid
);
SQL
second_pid=$!

lock_graph_observed=false
for _ in $(seq 1 80); do
    blocking_count="$(psql "${DATABASE_URL}" -Atqc "
        SELECT count(*)
        FROM pg_catalog.pg_stat_activity AS second_session
        JOIN pg_catalog.pg_stat_activity AS first_session
          ON first_session.application_name = 'orgmetra_employment_separation_first'
        WHERE second_session.application_name = 'orgmetra_employment_separation_second'
          AND second_session.wait_event_type = 'Lock'
          AND second_session.wait_event = 'advisory'
          AND first_session.pid = ANY(pg_catalog.pg_blocking_pids(second_session.pid));
    ")"
    if [[ "${blocking_count}" == "1" ]]; then
        lock_graph_observed=true
        break
    fi
    sleep 0.05
done

set +e
wait "${first_pid}"
first_status=$?
wait "${second_pid}"
second_status=$?
set -e
if [[ "${lock_graph_observed}" != "true" ]]; then
    echo "second exact-key separation never exposed the first backend as its advisory-lock blocker" >&2
    exit 1
fi
if [[ ${first_status} -ne 0 || ${second_status} -ne 0 ]]; then
    echo "concurrent separation sessions failed: first=${first_status} second=${second_status}" >&2
    exit 1
fi

first_concurrent_row="$(grep '^00000000-0000-7000-8000-000000000102|' "${first_concurrent_output}" | head -n 1)"
second_concurrent_row="$(grep '^00000000-0000-7000-8000-000000000102|' "${second_concurrent_output}" | head -n 1)"
first_concurrent_identity="$(printf '%s' "${first_concurrent_row}" | cut -d'|' -f1-3)"
second_concurrent_identity="$(printf '%s' "${second_concurrent_row}" | cut -d'|' -f1-3)"
if [[ -z "${first_concurrent_identity}" || "${second_concurrent_identity}" != "${first_concurrent_identity}" ]]; then
    echo "concurrent exact-key separation did not converge on one committed identity" >&2
    exit 1
fi
if [[ "$(printf '%s' "${first_concurrent_row}" | cut -d'|' -f4)" != "f" || "$(printf '%s' "${second_concurrent_row}" | cut -d'|' -f4)" != "t" ]]; then
    echo "concurrent separation did not produce one first-write and one replay: first=${first_concurrent_row} second=${second_concurrent_row}" >&2
    exit 1
fi

final_counts="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT concat_ws(',',
    (SELECT count(*) FROM public.employment_separation_record),
    (SELECT count(*) FROM public.audit_event_record WHERE canonical_event_json::jsonb ->> 'type' = 'orgmetra.people.employment_separated'),
    (SELECT count(*) FROM public.people_mutation_idempotency_record WHERE command_route = 'employment-separations')
);
")"
if [[ "${final_counts}" != "2,2,2" ]]; then
    echo "rejected/replayed separations changed durable truth unexpectedly: ${final_counts}" >&2
    exit 1
fi

echo "PostgreSQL Employment separation transition contract passed"
