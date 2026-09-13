#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"
TENANT_ID='10000000-0000-7000-8000-000000000001'
PERSON_ID='00000000-0000-7000-8000-000000000001'
EMPLOYMENT_ID='00000000-0000-7000-8000-000000000106'
EXPECTED_VERSION_ID='00000000-0000-7000-8000-000000000207'
FIRST_APP='orgmetra_employment_separation_cleanup_first'
SECOND_APP='orgmetra_employment_separation_cleanup_second'
FIRST_KEY='employment-separation-cleanup-key-a'
SECOND_KEY='employment-separation-cleanup-key-b'

tenant_psql() {
    PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" command psql "$@"
}

prerequisite="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT CASE
    WHEN pg_catalog.to_regprocedure(
        'public.separate_employment_record_once(uuid,uuid,uuid,uuid,date,text,text,text,text,text,text,text,uuid,uuid)'
    ) IS NOT NULL THEN 1
    ELSE 0
END;
")"
if [[ "${prerequisite}" != "1" ]]; then
    echo "Employment separation failure-cleanup companion requires the root contract to run first" >&2
    exit 1
fi

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

terminate_named_backends_best_effort() {
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=0 -Atqc "
        SELECT pg_catalog.pg_terminate_backend(pid)
        FROM pg_catalog.pg_stat_activity
        WHERE application_name IN ('${FIRST_APP}', '${SECOND_APP}')
          AND pid <> pg_catalog.pg_backend_pid();
    " >/dev/null 2>&1 || true
}

cleanup() {
    local saved_status=$?
    set +e
    if [[ "${first_fd_open}" == "true" ]]; then
        exec 3>&-
        first_fd_open=false
    fi
    if [[ -n "${second_pid}" ]] && kill -0 "${second_pid}" 2>/dev/null; then
        kill "${second_pid}" 2>/dev/null || true
        wait "${second_pid}" 2>/dev/null || true
    fi
    if [[ -n "${first_pid}" ]] && kill -0 "${first_pid}" 2>/dev/null; then
        kill "${first_pid}" 2>/dev/null || true
        wait "${first_pid}" 2>/dev/null || true
    fi
    terminate_named_backends_best_effort
    rm -rf "${runtime_dir}"
    return "${saved_status}"
}
trap cleanup EXIT

PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
PGAPPNAME="${FIRST_APP}" \
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -AtqF '|' <"${first_fifo}" >"${first_output}" 2>&1 &
first_pid=$!
exec 3>"${first_fifo}"
first_fd_open=true
cat >&3 <<SQL
BEGIN;
SELECT employment_record_id, separated_employment_record_version_id, recorded_at, replayed
FROM public.separate_employment_record_once(
    '${TENANT_ID}'::uuid,
    '${PERSON_ID}'::uuid,
    '${EMPLOYMENT_ID}'::uuid,
    '${EXPECTED_VERSION_ID}'::uuid,
    DATE '2026-08-15',
    'voluntary_resignation',
    'separation_packet:sep-failure-cleanup',
    'v1',
    'keyverse_subject:operator-17',
    'workforce_admin',
    'human_confirmation:separation-failure-cleanup',
    '${FIRST_KEY}',
    '00000000-0000-4000-8000-000000000520'::uuid,
    '00000000-0000-4000-8000-000000000620'::uuid
);
SQL

first_ready=false
for _ in $(seq 1 100); do
    first_state="$(psql "${DATABASE_URL}" -Atqc "
        SELECT count(*)
        FROM pg_catalog.pg_stat_activity
        WHERE application_name = '${FIRST_APP}'
          AND state = 'idle in transaction'
          AND wait_event_type = 'Client'
          AND wait_event = 'ClientRead';
    ")"
    if [[ "${first_state}" == "1" ]]; then
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
    echo "first failure-cleanup transaction did not reach the observable pre-commit ClientRead boundary" >&2
    exit 1
fi

PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
PGAPPNAME="${SECOND_APP}" \
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -AtqF '|' >"${second_output}" 2>&1 <<SQL &
SET statement_timeout = '10s';
SELECT employment_record_id, separated_employment_record_version_id, recorded_at, replayed
FROM public.separate_employment_record_once(
    '${TENANT_ID}'::uuid,
    '${PERSON_ID}'::uuid,
    '${EMPLOYMENT_ID}'::uuid,
    '${EXPECTED_VERSION_ID}'::uuid,
    DATE '2026-08-15',
    'voluntary_resignation',
    'separation_packet:sep-failure-cleanup',
    'v1',
    'keyverse_subject:operator-17',
    'workforce_admin',
    'human_confirmation:separation-failure-cleanup',
    '${SECOND_KEY}',
    '00000000-0000-4000-8000-000000000521'::uuid,
    '00000000-0000-4000-8000-000000000621'::uuid
);
SQL
second_pid=$!

blocker_observed=false
for _ in $(seq 1 100); do
    blocking_count="$(psql "${DATABASE_URL}" -Atqc "
        SELECT count(*)
        FROM pg_catalog.pg_stat_activity AS second_session
        JOIN pg_catalog.pg_stat_activity AS first_session
          ON first_session.application_name = '${FIRST_APP}'
        WHERE second_session.application_name = '${SECOND_APP}'
          AND second_session.wait_event_type = 'Lock'
          AND second_session.wait_event IN ('transactionid', 'tuple')
          AND first_session.pid = ANY(pg_catalog.pg_blocking_pids(second_session.pid));
    ")"
    if [[ "${blocking_count}" == "1" ]]; then
        blocker_observed=true
        break
    fi
    if ! kill -0 "${second_pid}" 2>/dev/null; then
        break
    fi
    sleep 0.05
done
if [[ "${blocker_observed}" != "true" ]]; then
    cat "${second_output}" >&2 || true
    echo "failure-cleanup scenario never established an observable Employment blocker" >&2
    exit 1
fi

first_backend_pid="$(psql "${DATABASE_URL}" -Atqc "
    SELECT pid
    FROM pg_catalog.pg_stat_activity
    WHERE application_name = '${FIRST_APP}';
")"
second_backend_pid="$(psql "${DATABASE_URL}" -Atqc "
    SELECT pid
    FROM pg_catalog.pg_stat_activity
    WHERE application_name = '${SECOND_APP}';
")"
if [[ ! "${first_backend_pid}" =~ ^[0-9]+$ || ! "${second_backend_pid}" =~ ^[0-9]+$ ]]; then
    echo "failure-cleanup scenario could not bind exact PostgreSQL backend identities" >&2
    exit 1
fi

# Terminate the blocked loser first so releasing the winner cannot let the loser
# commit before its disconnected client is noticed. Then terminate the winner.
second_terminated="$(psql "${DATABASE_URL}" -Atqc "SELECT pg_catalog.pg_terminate_backend(${second_backend_pid});")"
if [[ "${second_terminated}" != "t" ]]; then
    echo "failed to terminate the blocked failure-cleanup backend" >&2
    exit 1
fi

second_server_gone=false
for _ in $(seq 1 100); do
    second_count="$(psql "${DATABASE_URL}" -Atqc "
        SELECT count(*)
        FROM pg_catalog.pg_stat_activity
        WHERE application_name = '${SECOND_APP}';
    ")"
    if [[ "${second_count}" == "0" ]]; then
        second_server_gone=true
        break
    fi
    sleep 0.05
done
if [[ "${second_server_gone}" != "true" ]]; then
    echo "blocked failure-cleanup backend did not quiesce after termination" >&2
    exit 1
fi

first_terminated="$(psql "${DATABASE_URL}" -Atqc "SELECT pg_catalog.pg_terminate_backend(${first_backend_pid});")"
if [[ "${first_terminated}" != "t" ]]; then
    echo "failed to terminate the pre-commit failure-cleanup backend" >&2
    exit 1
fi

exec 3>&-
first_fd_open=false

set +e
wait "${second_pid}"
second_status=$?
wait "${first_pid}"
first_status=$?
set -e
second_pid=''
first_pid=''
if [[ ${second_status} -eq 0 ]]; then
    echo "blocked failure-cleanup client unexpectedly reported success; first=${first_status} second=${second_status}" >&2
    exit 1
fi

server_quiesced=false
for _ in $(seq 1 100); do
    server_count="$(psql "${DATABASE_URL}" -Atqc "
        SELECT count(*)
        FROM pg_catalog.pg_stat_activity
        WHERE application_name IN ('${FIRST_APP}', '${SECOND_APP}');
    ")"
    if [[ "${server_count}" == "0" ]]; then
        server_quiesced=true
        break
    fi
    sleep 0.05
done
if [[ "${server_quiesced}" != "true" ]]; then
    psql "${DATABASE_URL}" -x -c "
        SELECT pid, application_name, state, wait_event_type, wait_event
        FROM pg_catalog.pg_stat_activity
        WHERE application_name IN ('${FIRST_APP}', '${SECOND_APP}');
    " >&2 || true
    echo "Employment separation failure cleanup left a PostgreSQL backend alive" >&2
    exit 1
fi

truth_after_failure="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -AtqF '|' <<SQL
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
       FROM public.people_mutation_idempotency_record
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND command_route = 'employment-separations'
        AND idempotency_key IN ('${FIRST_KEY}', '${SECOND_KEY}')),
    (SELECT count(*)
       FROM public.employment_record_version
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND employment_record_id = '${EMPLOYMENT_ID}'::uuid
        AND employment_record_version_id = '${EXPECTED_VERSION_ID}'::uuid
        AND employment_status_code = 'active'
        AND recorded_to IS NULL)
);
SQL
)"
if [[ "${truth_after_failure}" != "0|0|0|0|1" ]]; then
    echo "failure cleanup left partial separation truth or failed to restore the original current Employment version: ${truth_after_failure}" >&2
    exit 1
fi

echo "PostgreSQL Employment separation failure-cleanup contract passed"
