#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"
TENANT_ID='10000000-0000-7000-8000-000000000001'
PERSON_ID='00000000-0000-7000-8000-000000000001'
EMPLOYMENT_ID='00000000-0000-7000-8000-000000000105'
EXPECTED_VERSION_ID='00000000-0000-7000-8000-000000000206'

# This is a companion to test_employment_separation_postgres.sh. The root contract
# owns schema migration and tenant/person setup; this scenario adds only an isolated
# Employment fixture so it can prove aggregate serialization without reapplying schema.
tenant_psql() {
    PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" command psql "$@"
}

tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO public.employment_record (
    tenant_record_id,
    employment_record_id,
    person_record_id,
    recorded_from
) VALUES (
    '${TENANT_ID}'::uuid,
    '${EMPLOYMENT_ID}'::uuid,
    '${PERSON_ID}'::uuid,
    TIMESTAMPTZ '2026-01-02 00:00:00+00'
);

INSERT INTO public.employment_record_version (
    tenant_record_id,
    employment_record_version_id,
    employment_record_id,
    employment_status_code,
    employment_concurrency_code,
    effective_from,
    effective_to,
    recorded_from
) VALUES (
    '${TENANT_ID}'::uuid,
    '${EXPECTED_VERSION_ID}'::uuid,
    '${EMPLOYMENT_ID}'::uuid,
    'active',
    'concurrent',
    DATE '2026-01-01',
    NULL,
    TIMESTAMPTZ '2026-01-02 00:00:00+00'
);
SQL

runtime_dir="$(mktemp -d)"
first_fifo="${runtime_dir}/first.sql"
first_output="${runtime_dir}/first.out"
second_output="${runtime_dir}/second.out"
mkfifo "${first_fifo}"
first_pid=''
second_pid=''
first_fd_open=false
cleanup() {
    if [[ "${first_fd_open}" == "true" ]]; then
        exec 3>&-
        first_fd_open=false
    fi
    if [[ -n "${first_pid}" ]] && kill -0 "${first_pid}" 2>/dev/null; then
        kill "${first_pid}" 2>/dev/null || true
        wait "${first_pid}" 2>/dev/null || true
    fi
    if [[ -n "${second_pid}" ]] && kill -0 "${second_pid}" 2>/dev/null; then
        kill "${second_pid}" 2>/dev/null || true
        wait "${second_pid}" 2>/dev/null || true
    fi
    rm -rf "${runtime_dir}"
}
trap cleanup EXIT

PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
PGAPPNAME='orgmetra_employment_separation_distinct_first' \
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -AtqF '|' <"${first_fifo}" >"${first_output}" 2>&1 &
first_pid=$!
exec 3>"${first_fifo}"
first_fd_open=true
cat >&3 <<'SQL'
BEGIN;
SELECT employment_record_id, separated_employment_record_version_id, recorded_at, replayed
FROM public.separate_employment_record_once(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000105'::uuid,
    '00000000-0000-7000-8000-000000000206'::uuid,
    DATE '2026-08-15',
    'voluntary_resignation',
    'separation_packet:sep-distinct-key',
    'v1',
    'keyverse_subject:operator-17',
    'workforce_admin',
    'human_confirmation:separation-distinct-key',
    'employment-separation-distinct-key-a',
    '00000000-0000-4000-8000-000000000510'::uuid,
    '00000000-0000-4000-8000-000000000610'::uuid
);
\echo ORGMETRA_DISTINCT_FIRST_READY
SQL

first_ready=false
for _ in $(seq 1 100); do
    if grep -q '^ORGMETRA_DISTINCT_FIRST_READY$' "${first_output}" 2>/dev/null; then
        first_ready=true
        break
    fi
    if ! kill -0 "${first_pid}" 2>/dev/null; then
        break
    fi
    sleep 0.05
done
if [[ "${first_ready}" != "true" ]]; then
    cat "${first_output}" >&2 || true
    echo "first distinct-key separation transaction did not reach the controlled pre-commit boundary" >&2
    exit 1
fi

PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
PGAPPNAME='orgmetra_employment_separation_distinct_second' \
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -AtqF '|' >"${second_output}" 2>&1 <<'SQL' &
SET statement_timeout = '10s';
SELECT employment_record_id, separated_employment_record_version_id, recorded_at, replayed
FROM public.separate_employment_record_once(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000105'::uuid,
    '00000000-0000-7000-8000-000000000206'::uuid,
    DATE '2026-08-15',
    'voluntary_resignation',
    'separation_packet:sep-distinct-key',
    'v1',
    'keyverse_subject:operator-17',
    'workforce_admin',
    'human_confirmation:separation-distinct-key',
    'employment-separation-distinct-key-b',
    '00000000-0000-4000-8000-000000000511'::uuid,
    '00000000-0000-4000-8000-000000000611'::uuid
);
SQL
second_pid=$!

aggregate_blocker_observed=false
observed_wait_event=''
for _ in $(seq 1 100); do
    lock_row="$(psql "${DATABASE_URL}" -AtqF '|' -c "
        SELECT second_session.wait_event,
               count(*)
        FROM pg_catalog.pg_stat_activity AS second_session
        JOIN pg_catalog.pg_stat_activity AS first_session
          ON first_session.application_name = 'orgmetra_employment_separation_distinct_first'
        WHERE second_session.application_name = 'orgmetra_employment_separation_distinct_second'
          AND second_session.wait_event_type = 'Lock'
          AND second_session.wait_event IN ('transactionid', 'tuple')
          AND first_session.pid = ANY(pg_catalog.pg_blocking_pids(second_session.pid))
        GROUP BY second_session.wait_event;
    ")"
    if [[ -n "${lock_row}" ]]; then
        observed_wait_event="${lock_row%%|*}"
        if [[ "${lock_row#*|}" == "1" ]]; then
            aggregate_blocker_observed=true
            break
        fi
    fi
    if ! kill -0 "${second_pid}" 2>/dev/null; then
        break
    fi
    sleep 0.05
done

# Release the first transaction only after the second backend has either exposed
# its database blocker or failed. The polling interval is coordination, not proof;
# pg_blocking_pids plus a row/transaction lock wait is the acceptance evidence.
printf 'COMMIT;\n\\q\n' >&3
exec 3>&-
first_fd_open=false

set +e
wait "${first_pid}"
first_status=$?
wait "${second_pid}"
second_status=$?
set -e
first_pid=''
second_pid=''

if [[ "${aggregate_blocker_observed}" != "true" ]]; then
    cat "${second_output}" >&2 || true
    echo "different idempotency keys never exposed the first Employment transaction as a row-level blocker" >&2
    exit 1
fi
if [[ "${observed_wait_event}" == "advisory" || -z "${observed_wait_event}" ]]; then
    echo "distinct-key concurrency was incorrectly qualified through the idempotency advisory lock: ${observed_wait_event}" >&2
    exit 1
fi
if [[ ${first_status} -ne 0 ]]; then
    cat "${first_output}" >&2 || true
    echo "first distinct-key separation failed unexpectedly: ${first_status}" >&2
    exit 1
fi
if [[ ${second_status} -eq 0 ]]; then
    cat "${second_output}" >&2 || true
    echo "second distinct-key separation unexpectedly committed against the stale expected Employment version" >&2
    exit 1
fi
if ! grep -q 'expected version is stale or unavailable' "${second_output}"; then
    cat "${second_output}" >&2 || true
    echo "distinct-key loser did not fail as an authoritative stale-version conflict" >&2
    exit 1
fi

first_row="$(grep '^00000000-0000-7000-8000-000000000105|' "${first_output}" | head -n 1)"
if [[ -z "${first_row}" || "$(printf '%s' "${first_row}" | cut -d'|' -f4)" != "f" ]]; then
    cat "${first_output}" >&2 || true
    echo "distinct-key winner did not return one first-write result" >&2
    exit 1
fi

truth_counts="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -AtqF '|' <<SQL
SELECT concat_ws('|',
    (SELECT count(*)
       FROM public.employment_separation_record
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND employment_record_id = '${EMPLOYMENT_ID}'::uuid),
    (SELECT count(*)
       FROM public.audit_event_record
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND canonical_event_json::jsonb ->> 'type' = 'orgmetra.people.employment_separated'
        AND canonical_event_json::jsonb ->> 'subject' = 'employment_record:${EMPLOYMENT_ID}'),
    (SELECT count(*)
       FROM public.outbox_delivery_record AS outbox
       JOIN public.audit_event_record AS audit
         ON audit.tenant_record_id = outbox.tenant_record_id
        AND audit.audit_event_record_id = outbox.audit_event_record_id
      WHERE audit.tenant_record_id = '${TENANT_ID}'::uuid
        AND audit.canonical_event_json::jsonb ->> 'type' = 'orgmetra.people.employment_separated'
        AND audit.canonical_event_json::jsonb ->> 'subject' = 'employment_record:${EMPLOYMENT_ID}'),
    (SELECT count(*)
       FROM public.people_mutation_idempotency_record AS idem
       JOIN public.employment_separation_record AS separation
         ON separation.tenant_record_id = idem.tenant_record_id
        AND separation.separated_employment_record_version_id = idem.created_record_id
      WHERE idem.tenant_record_id = '${TENANT_ID}'::uuid
        AND idem.command_route = 'employment-separations'
        AND separation.employment_record_id = '${EMPLOYMENT_ID}'::uuid),
    (SELECT count(*)
       FROM public.people_mutation_idempotency_record
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND command_route = 'employment-separations'
        AND idempotency_key = 'employment-separation-distinct-key-b')
);
SQL
)"
if [[ "${truth_counts}" != "1|1|1|1|0" ]]; then
    echo "distinct-key concurrency produced duplicate or loser-side durable truth: ${truth_counts}" >&2
    exit 1
fi

echo "PostgreSQL Employment separation distinct-key concurrency contract passed"
