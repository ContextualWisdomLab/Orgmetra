#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"
TENANT_ID='10000000-0000-7000-8000-000000000001'
PERSON_ID='10000000-0000-7000-8000-000000000101'
EMPLOYMENT_ASSIGNMENT_FIRST='10000000-0000-7000-8000-000000000111'
VERSION_ASSIGNMENT_FIRST='10000000-0000-7000-8000-000000000211'
EMPLOYMENT_SEPARATION_FIRST='10000000-0000-7000-8000-000000000112'
VERSION_SEPARATION_FIRST='10000000-0000-7000-8000-000000000212'
ORGANIZATION_ID='10000000-0000-7000-8000-000000000121'
JOB_ID='10000000-0000-7000-8000-000000000131'
POSITION_ID='10000000-0000-7000-8000-000000000141'
ASSIGNMENT_FIRST_ID='10000000-0000-7000-8000-000000000151'
ASSIGNMENT_LOSER_ID='10000000-0000-7000-8000-000000000152'
HISTORICAL_ASSIGNMENT_ID='10000000-0000-7000-8000-000000000153'

# This root deliberately stops at the separation domain migration before applying
# the new serialization guard. Capability-owner migrations 0015/0016 use
# cluster-global roles and are verified by their own isolated acceptance lane.
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
    database/migrations/0014_employment_separation_transition.sql \
    database/migrations/0017_assignment_employment_separation_serialization.sql; do
    psql "${DATABASE_URL}" -X -v ON_ERROR_STOP=1 -f "${migration}" >/dev/null
done

tenant_psql() {
    PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" command psql "$@"
}

psql "${DATABASE_URL}" -X -v ON_ERROR_STOP=1 <<SQL >/dev/null
INSERT INTO public.tenant_record (tenant_record_id, tenant_reference)
VALUES ('${TENANT_ID}'::uuid, 'assignment_separation_serialization');

INSERT INTO public.person_record (tenant_record_id, person_record_id, recorded_from)
VALUES ('${TENANT_ID}'::uuid, '${PERSON_ID}'::uuid, TIMESTAMPTZ '2026-01-02 00:00:00+00');

INSERT INTO public.employment_record (
    tenant_record_id, employment_record_id, person_record_id, recorded_from
) VALUES
    ('${TENANT_ID}'::uuid, '${EMPLOYMENT_ASSIGNMENT_FIRST}'::uuid, '${PERSON_ID}'::uuid, TIMESTAMPTZ '2026-01-02 00:00:00+00'),
    ('${TENANT_ID}'::uuid, '${EMPLOYMENT_SEPARATION_FIRST}'::uuid, '${PERSON_ID}'::uuid, TIMESTAMPTZ '2026-01-02 00:00:00+00');

INSERT INTO public.employment_record_version (
    tenant_record_id,
    employment_record_version_id,
    employment_record_id,
    employment_status_code,
    employment_concurrency_code,
    effective_from,
    effective_to,
    recorded_from
) VALUES
    ('${TENANT_ID}'::uuid, '${VERSION_ASSIGNMENT_FIRST}'::uuid, '${EMPLOYMENT_ASSIGNMENT_FIRST}'::uuid,
     'active', 'concurrent', DATE '2026-01-01', NULL, TIMESTAMPTZ '2026-01-02 00:00:00+00'),
    ('${TENANT_ID}'::uuid, '${VERSION_SEPARATION_FIRST}'::uuid, '${EMPLOYMENT_SEPARATION_FIRST}'::uuid,
     'active', 'concurrent', DATE '2026-01-01', NULL, TIMESTAMPTZ '2026-01-02 00:00:00+00');

INSERT INTO public.organization_unit (tenant_record_id, organization_unit_id, recorded_from)
VALUES ('${TENANT_ID}'::uuid, '${ORGANIZATION_ID}'::uuid, TIMESTAMPTZ '2026-01-02 00:00:00+00');

INSERT INTO public.job_profile (tenant_record_id, job_profile_id, recorded_from)
VALUES ('${TENANT_ID}'::uuid, '${JOB_ID}'::uuid, TIMESTAMPTZ '2026-01-02 00:00:00+00');

INSERT INTO public.position_record (
    tenant_record_id, position_record_id, organization_unit_id, job_profile_id, recorded_from
) VALUES (
    '${TENANT_ID}'::uuid,
    '${POSITION_ID}'::uuid,
    '${ORGANIZATION_ID}'::uuid,
    '${JOB_ID}'::uuid,
    TIMESTAMPTZ '2026-01-02 00:00:00+00'
);
SQL

runtime_dir="$(mktemp -d)"
assignment_fifo="${runtime_dir}/assignment-first.sql"
separation_fifo="${runtime_dir}/separation-first.sql"
assignment_output="${runtime_dir}/assignment-first.out"
separation_after_assignment_output="${runtime_dir}/separation-after-assignment.out"
separation_output="${runtime_dir}/separation-first.out"
assignment_after_separation_output="${runtime_dir}/assignment-after-separation.out"
mkfifo "${assignment_fifo}" "${separation_fifo}"
assignment_pid=''
separation_after_assignment_pid=''
separation_pid=''
assignment_after_separation_pid=''
assignment_fd_open=false
separation_fd_open=false

cleanup() {
    set +e
    if [[ "${assignment_fd_open}" == "true" ]]; then exec 3>&-; fi
    if [[ "${separation_fd_open}" == "true" ]]; then exec 4>&-; fi
    for pid in "${assignment_pid}" "${separation_after_assignment_pid}" "${separation_pid}" "${assignment_after_separation_pid}"; do
        if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
            kill "${pid}" 2>/dev/null || true
            wait "${pid}" 2>/dev/null || true
        fi
    done
    psql "${DATABASE_URL}" -X -v ON_ERROR_STOP=0 -Atqc "
        SELECT pg_catalog.pg_terminate_backend(pid)
        FROM pg_catalog.pg_stat_activity
        WHERE application_name LIKE 'orgmetra_assignment_separation_%'
          AND pid <> pg_catalog.pg_backend_pid();
    " >/dev/null 2>&1 || true
    rm -rf "${runtime_dir}"
}
trap cleanup EXIT

wait_for_client_read() {
    local app_name=$1
    local client_pid=$2
    for _ in $(seq 1 120); do
        state="$(psql "${DATABASE_URL}" -X -Atqc "
            SELECT count(*)
            FROM pg_catalog.pg_stat_activity
            WHERE application_name = '${app_name}'
              AND state = 'idle in transaction'
              AND wait_event_type = 'Client'
              AND wait_event = 'ClientRead';
        ")"
        if [[ "${state}" == "1" ]]; then
            return 0
        fi
        if ! kill -0 "${client_pid}" 2>/dev/null; then
            return 1
        fi
        sleep 0.05
    done
    return 1
}

wait_for_blocker() {
    local blocked_app=$1
    local blocker_app=$2
    for _ in $(seq 1 120); do
        lock_row="$(psql "${DATABASE_URL}" -X -AtqF '|' -c "
            SELECT blocked.wait_event, count(*)
            FROM pg_catalog.pg_stat_activity AS blocked
            JOIN pg_catalog.pg_stat_activity AS blocker
              ON blocker.application_name = '${blocker_app}'
            WHERE blocked.application_name = '${blocked_app}'
              AND blocked.wait_event_type = 'Lock'
              AND blocked.wait_event IN ('transactionid', 'tuple')
              AND blocker.pid = ANY(pg_catalog.pg_blocking_pids(blocked.pid))
            GROUP BY blocked.wait_event;
        ")"
        if [[ -n "${lock_row}" && "${lock_row#*|}" == "1" ]]; then
            return 0
        fi
        sleep 0.05
    done
    return 1
}

# Scenario A: Assignment obtains the Employment anchor first. Separation must wait
# on that exact row-level conflict and, after the Assignment commits, fail closed
# because the new Assignment extends through/after the requested separation date.
PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
PGAPPNAME='orgmetra_assignment_separation_assignment_first' \
psql "${DATABASE_URL}" -X -v ON_ERROR_STOP=1 -Atq <"${assignment_fifo}" >"${assignment_output}" 2>&1 &
assignment_pid=$!
exec 3>"${assignment_fifo}"
assignment_fd_open=true
cat >&3 <<SQL
BEGIN;
INSERT INTO public.assignment_record (
    tenant_record_id, assignment_record_id, employment_record_id, person_record_id,
    position_record_id, allocation_ratio, effective_from, effective_to, recorded_from
) VALUES (
    '${TENANT_ID}'::uuid, '${ASSIGNMENT_FIRST_ID}'::uuid, '${EMPLOYMENT_ASSIGNMENT_FIRST}'::uuid,
    '${PERSON_ID}'::uuid, '${POSITION_ID}'::uuid, 0.5000, DATE '2026-08-15', NULL,
    TIMESTAMPTZ '2026-08-15 00:00:00+00'
);
SQL

if ! wait_for_client_read 'orgmetra_assignment_separation_assignment_first' "${assignment_pid}"; then
    cat "${assignment_output}" >&2 || true
    echo "assignment-first transaction did not reach the observable pre-commit ClientRead boundary" >&2
    exit 1
fi

PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
PGAPPNAME='orgmetra_assignment_separation_separation_after_assignment' \
psql "${DATABASE_URL}" -X -v ON_ERROR_STOP=1 -Atq >"${separation_after_assignment_output}" 2>&1 <<SQL &
SET statement_timeout = '10s';
SELECT employment_record_id
FROM public.separate_employment_record_once(
    '${TENANT_ID}'::uuid,
    '${PERSON_ID}'::uuid,
    '${EMPLOYMENT_ASSIGNMENT_FIRST}'::uuid,
    '${VERSION_ASSIGNMENT_FIRST}'::uuid,
    DATE '2026-08-15',
    'voluntary_resignation',
    'separation_packet:assignment-first',
    'v1',
    'keyverse_subject:operator-17',
    'workforce_admin',
    'human_confirmation:assignment-first',
    'assignment-first-separation-key',
    '10000000-0000-4000-8000-000000000501'::uuid,
    '10000000-0000-4000-8000-000000000601'::uuid
);
SQL
separation_after_assignment_pid=$!

if ! wait_for_blocker 'orgmetra_assignment_separation_separation_after_assignment' 'orgmetra_assignment_separation_assignment_first'; then
    cat "${separation_after_assignment_output}" >&2 || true
    echo "separation never observed the uncommitted Assignment as the Employment-anchor blocker" >&2
    exit 1
fi

printf 'COMMIT;\n\\q\n' >&3
exec 3>&-
assignment_fd_open=false
set +e
wait "${assignment_pid}"
assignment_status=$?
wait "${separation_after_assignment_pid}"
separation_after_assignment_status=$?
set -e
assignment_pid=''
separation_after_assignment_pid=''

if [[ ${assignment_status} -ne 0 ]]; then
    cat "${assignment_output}" >&2 || true
    echo "assignment-first writer failed unexpectedly" >&2
    exit 1
fi
if [[ ${separation_after_assignment_status} -eq 0 ]] || ! grep -q 'assignment coordination before termination' "${separation_after_assignment_output}"; then
    cat "${separation_after_assignment_output}" >&2 || true
    echo "separation did not fail closed after the competing Assignment committed" >&2
    exit 1
fi

scenario_a_truth="$(tenant_psql "${DATABASE_URL}" -X -v ON_ERROR_STOP=1 -AtqF '|' -c "
SELECT concat_ws('|',
    (SELECT count(*) FROM public.assignment_record
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND assignment_record_id = '${ASSIGNMENT_FIRST_ID}'::uuid),
    (SELECT count(*) FROM public.employment_separation_record
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND employment_record_id = '${EMPLOYMENT_ASSIGNMENT_FIRST}'::uuid)
);")"
if [[ "${scenario_a_truth}" != "1|0" ]]; then
    echo "assignment-first durable truth is inconsistent: ${scenario_a_truth}" >&2
    exit 1
fi

# Scenario B: Separation obtains the same Employment anchor first. Assignment must
# block, then re-evaluate coverage after the separation commit and fail rather than
# insert a fact extending into the terminal Employment interval.
PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
PGAPPNAME='orgmetra_assignment_separation_separation_first' \
psql "${DATABASE_URL}" -X -v ON_ERROR_STOP=1 -AtqF '|' <"${separation_fifo}" >"${separation_output}" 2>&1 &
separation_pid=$!
exec 4>"${separation_fifo}"
separation_fd_open=true
cat >&4 <<SQL
BEGIN;
SELECT employment_record_id, separated_employment_record_version_id, recorded_at, replayed
FROM public.separate_employment_record_once(
    '${TENANT_ID}'::uuid,
    '${PERSON_ID}'::uuid,
    '${EMPLOYMENT_SEPARATION_FIRST}'::uuid,
    '${VERSION_SEPARATION_FIRST}'::uuid,
    DATE '2026-08-15',
    'voluntary_resignation',
    'separation_packet:separation-first',
    'v1',
    'keyverse_subject:operator-17',
    'workforce_admin',
    'human_confirmation:separation-first',
    'separation-first-key',
    '10000000-0000-4000-8000-000000000502'::uuid,
    '10000000-0000-4000-8000-000000000602'::uuid
);
SQL

if ! wait_for_client_read 'orgmetra_assignment_separation_separation_first' "${separation_pid}"; then
    cat "${separation_output}" >&2 || true
    echo "separation-first transaction did not reach the observable pre-commit ClientRead boundary" >&2
    exit 1
fi

PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
PGAPPNAME='orgmetra_assignment_separation_assignment_after_separation' \
psql "${DATABASE_URL}" -X -v ON_ERROR_STOP=1 -Atq >"${assignment_after_separation_output}" 2>&1 <<SQL &
SET statement_timeout = '10s';
INSERT INTO public.assignment_record (
    tenant_record_id, assignment_record_id, employment_record_id, person_record_id,
    position_record_id, allocation_ratio, effective_from, effective_to, recorded_from
) VALUES (
    '${TENANT_ID}'::uuid, '${ASSIGNMENT_LOSER_ID}'::uuid, '${EMPLOYMENT_SEPARATION_FIRST}'::uuid,
    '${PERSON_ID}'::uuid, '${POSITION_ID}'::uuid, 0.5000, DATE '2026-08-15', NULL,
    TIMESTAMPTZ '2026-08-15 00:00:00+00'
);
SQL
assignment_after_separation_pid=$!

if ! wait_for_blocker 'orgmetra_assignment_separation_assignment_after_separation' 'orgmetra_assignment_separation_separation_first'; then
    cat "${assignment_after_separation_output}" >&2 || true
    echo "Assignment never observed the uncommitted separation as the Employment-anchor blocker" >&2
    exit 1
fi

printf 'COMMIT;\n\\q\n' >&4
exec 4>&-
separation_fd_open=false
set +e
wait "${separation_pid}"
separation_status=$?
wait "${assignment_after_separation_pid}"
assignment_after_separation_status=$?
set -e
separation_pid=''
assignment_after_separation_pid=''

if [[ ${separation_status} -ne 0 ]]; then
    cat "${separation_output}" >&2 || true
    echo "separation-first writer failed unexpectedly" >&2
    exit 1
fi
if [[ ${assignment_after_separation_status} -eq 0 ]] || ! grep -q 'assignment requires current active or leave Employment coverage' "${assignment_after_separation_output}"; then
    cat "${assignment_after_separation_output}" >&2 || true
    echo "Assignment did not fail closed after the competing separation committed" >&2
    exit 1
fi

scenario_b_truth="$(tenant_psql "${DATABASE_URL}" -X -v ON_ERROR_STOP=1 -AtqF '|' -c "
SELECT concat_ws('|',
    (SELECT count(*) FROM public.employment_separation_record
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND employment_record_id = '${EMPLOYMENT_SEPARATION_FIRST}'::uuid),
    (SELECT count(*) FROM public.assignment_record
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND assignment_record_id = '${ASSIGNMENT_LOSER_ID}'::uuid)
);")"
if [[ "${scenario_b_truth}" != "1|0" ]]; then
    echo "separation-first durable truth is inconsistent: ${scenario_b_truth}" >&2
    exit 1
fi

# Historical Assignment truth ending exactly at separation remains legal. The guard
# must reject only intervals not fully covered by a current active/leave version.
tenant_psql "${DATABASE_URL}" -X -v ON_ERROR_STOP=1 -Atq <<SQL
INSERT INTO public.assignment_record (
    tenant_record_id, assignment_record_id, employment_record_id, person_record_id,
    position_record_id, allocation_ratio, effective_from, effective_to, recorded_from
) VALUES (
    '${TENANT_ID}'::uuid, '${HISTORICAL_ASSIGNMENT_ID}'::uuid, '${EMPLOYMENT_SEPARATION_FIRST}'::uuid,
    '${PERSON_ID}'::uuid, '${POSITION_ID}'::uuid, 0.2500, DATE '2026-08-01', DATE '2026-08-15',
    TIMESTAMPTZ '2026-08-16 00:00:00+00'
);
SQL

historical_count="$(tenant_psql "${DATABASE_URL}" -X -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*) FROM public.assignment_record
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND assignment_record_id = '${HISTORICAL_ASSIGNMENT_ID}'::uuid;")"
if [[ "${historical_count}" != "1" ]]; then
    echo "historical Assignment ending at separation was incorrectly rejected" >&2
    exit 1
fi

echo "PostgreSQL Assignment/Employment-separation serialization contract passed"
