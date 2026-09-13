#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"
TENANT_ID='10000000-0000-7000-8000-000000000001'
PERSON_ID='00000000-0000-7000-8000-000000000001'
EMPLOYMENT_ID='00000000-0000-7000-8000-000000000107'
EXPECTED_VERSION_ID='00000000-0000-7000-8000-000000000208'
FIRST_APP='orgmetra_employment_separation_uncertain_commit'
IDEMPOTENCY_KEY='employment-separation-uncertain-commit-key'
FIRST_AUDIT_ID='00000000-0000-4000-8000-000000000530'
FIRST_OUTBOX_ID='00000000-0000-4000-8000-000000000630'
RETRY_AUDIT_ID='00000000-0000-4000-8000-000000000531'
RETRY_OUTBOX_ID='00000000-0000-4000-8000-000000000631'

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
    echo "Employment separation uncertain-commit companion requires the root contract to run first" >&2
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
first_output="${runtime_dir}/first.out"
first_pid=''

terminate_named_backend_best_effort() {
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=0 -Atqc "
        SELECT pg_catalog.pg_terminate_backend(pid)
        FROM pg_catalog.pg_stat_activity
        WHERE application_name = '${FIRST_APP}'
          AND pid <> pg_catalog.pg_backend_pid();
    " >/dev/null 2>&1 || true
}

cleanup() {
    local saved_status=$?
    set +e
    if [[ -n "${first_pid}" ]] && kill -0 "${first_pid}" 2>/dev/null; then
        kill "${first_pid}" 2>/dev/null || true
        wait "${first_pid}" 2>/dev/null || true
    fi
    terminate_named_backend_best_effort
    rm -rf "${runtime_dir}"
    return "${saved_status}"
}
trap cleanup EXIT

# The first client commits the separation, then remains in pg_sleep. The observer
# below qualifies commit through durable database state, not through first-client
# output. Terminating the still-running backend makes the caller observe failure
# after the authoritative transaction has already committed.
PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
PGAPPNAME="${FIRST_APP}" \
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -AtqF '|' >"${first_output}" 2>&1 <<SQL &
BEGIN;
SELECT employment_record_id, separated_employment_record_version_id, recorded_at, replayed
FROM public.separate_employment_record_once(
    '${TENANT_ID}'::uuid,
    '${PERSON_ID}'::uuid,
    '${EMPLOYMENT_ID}'::uuid,
    '${EXPECTED_VERSION_ID}'::uuid,
    DATE '2026-08-15',
    'voluntary_resignation',
    'separation_packet:sep-uncertain-commit',
    'v1',
    'keyverse_subject:operator-17',
    'workforce_admin',
    'human_confirmation:separation-uncertain-commit',
    '${IDEMPOTENCY_KEY}',
    '${FIRST_AUDIT_ID}'::uuid,
    '${FIRST_OUTBOX_ID}'::uuid
);
COMMIT;
SELECT pg_catalog.pg_sleep(300);
SQL
first_pid=$!

committed=false
first_backend_pid=''
first_truth=''
for _ in $(seq 1 200); do
    first_backend_pid="$(psql "${DATABASE_URL}" -Atqc "
        SELECT pid
        FROM pg_catalog.pg_stat_activity
        WHERE application_name = '${FIRST_APP}';
    ")"
    if [[ "${first_backend_pid}" =~ ^[0-9]+$ ]]; then
        first_truth="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -AtqF '|' <<SQL
SELECT concat_ws('|',
    separation.separated_employment_record_version_id,
    separation.recorded_at,
    (SELECT count(*)
       FROM public.employment_separation_record AS s
      WHERE s.tenant_record_id = '${TENANT_ID}'::uuid
        AND s.employment_record_id = '${EMPLOYMENT_ID}'::uuid),
    (SELECT count(*)
       FROM public.people_mutation_idempotency_record AS idem
      WHERE idem.tenant_record_id = '${TENANT_ID}'::uuid
        AND idem.command_route = 'employment-separations'
        AND idem.idempotency_key = '${IDEMPOTENCY_KEY}'),
    (SELECT count(*)
       FROM public.audit_event_record AS audit
      WHERE audit.tenant_record_id = '${TENANT_ID}'::uuid
        AND audit.audit_event_record_id = '${FIRST_AUDIT_ID}'::uuid),
    (SELECT count(*)
       FROM public.outbox_delivery_record AS outbox
      WHERE outbox.tenant_record_id = '${TENANT_ID}'::uuid
        AND outbox.outbox_delivery_record_id = '${FIRST_OUTBOX_ID}'::uuid)
)
FROM public.employment_separation_record AS separation
WHERE separation.tenant_record_id = '${TENANT_ID}'::uuid
  AND separation.employment_record_id = '${EMPLOYMENT_ID}'::uuid;
SQL
)"
        IFS='|' read -r durable_version durable_recorded_at separation_count idempotency_count audit_count outbox_count <<<"${first_truth}"
        if [[ -n "${durable_version:-}" && -n "${durable_recorded_at:-}" \
              && "${separation_count:-}" == "1" && "${idempotency_count:-}" == "1" \
              && "${audit_count:-}" == "1" && "${outbox_count:-}" == "1" ]]; then
            committed=true
            break
        fi
    fi
    if ! kill -0 "${first_pid}" 2>/dev/null; then
        break
    fi
    sleep 0.05
done
if [[ "${committed}" != "true" || ! "${first_backend_pid}" =~ ^[0-9]+$ ]]; then
    cat "${first_output}" >&2 || true
    echo "uncertain-commit scenario never exposed one durable committed separation while the first client remained connected" >&2
    exit 1
fi

first_wait="$(psql "${DATABASE_URL}" -AtqF '|' -c "
    SELECT state, wait_event_type, wait_event
    FROM pg_catalog.pg_stat_activity
    WHERE pid = ${first_backend_pid}
      AND application_name = '${FIRST_APP}';
")"
if [[ "${first_wait}" != "active|Timeout|PgSleep" ]]; then
    echo "first uncertain-commit backend was not held after commit in pg_sleep: ${first_wait}" >&2
    exit 1
fi

terminated="$(psql "${DATABASE_URL}" -Atqc "SELECT pg_catalog.pg_terminate_backend(${first_backend_pid});")"
if [[ "${terminated}" != "t" ]]; then
    echo "failed to terminate committed uncertain-outcome backend" >&2
    exit 1
fi

set +e
wait "${first_pid}"
first_status=$?
set -e
first_pid=''
if [[ ${first_status} -eq 0 ]]; then
    cat "${first_output}" >&2 || true
    echo "first uncertain-commit client unexpectedly reported success after backend termination" >&2
    exit 1
fi

server_quiesced=false
for _ in $(seq 1 100); do
    server_count="$(psql "${DATABASE_URL}" -Atqc "
        SELECT count(*)
        FROM pg_catalog.pg_stat_activity
        WHERE application_name = '${FIRST_APP}';
    ")"
    if [[ "${server_count}" == "0" ]]; then
        server_quiesced=true
        break
    fi
    sleep 0.05
done
if [[ "${server_quiesced}" != "true" ]]; then
    echo "uncertain-commit backend did not quiesce after termination" >&2
    exit 1
fi

retry_result="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -AtqF '|' <<SQL
SELECT employment_record_id, separated_employment_record_version_id, recorded_at, replayed
FROM public.separate_employment_record_once(
    '${TENANT_ID}'::uuid,
    '${PERSON_ID}'::uuid,
    '${EMPLOYMENT_ID}'::uuid,
    '${EXPECTED_VERSION_ID}'::uuid,
    DATE '2026-08-15',
    'voluntary_resignation',
    'separation_packet:sep-uncertain-commit',
    'v1',
    'keyverse_subject:operator-17',
    'workforce_admin',
    'human_confirmation:separation-uncertain-commit',
    '${IDEMPOTENCY_KEY}',
    '${RETRY_AUDIT_ID}'::uuid,
    '${RETRY_OUTBOX_ID}'::uuid
);
SQL
)"
IFS='|' read -r durable_version durable_recorded_at _separation_count _idempotency_count _audit_count _outbox_count <<<"${first_truth}"
if [[ "${retry_result}" != "${EMPLOYMENT_ID}|${durable_version}|${durable_recorded_at}|t" ]]; then
    echo "retry after uncertain commit did not recover the exact first committed result: ${retry_result}" >&2
    exit 1
fi

final_truth="$(tenant_psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -AtqF '|' <<SQL
SELECT concat_ws('|',
    (SELECT count(*)
       FROM public.employment_separation_record
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND employment_record_id = '${EMPLOYMENT_ID}'::uuid),
    (SELECT count(*)
       FROM public.people_mutation_idempotency_record
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND command_route = 'employment-separations'
        AND idempotency_key = '${IDEMPOTENCY_KEY}'),
    (SELECT count(*)
       FROM public.audit_event_record
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND audit_event_record_id IN ('${FIRST_AUDIT_ID}'::uuid, '${RETRY_AUDIT_ID}'::uuid)),
    (SELECT count(*)
       FROM public.outbox_delivery_record
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND outbox_delivery_record_id IN ('${FIRST_OUTBOX_ID}'::uuid, '${RETRY_OUTBOX_ID}'::uuid)),
    (SELECT count(*)
       FROM public.audit_event_record
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND audit_event_record_id = '${RETRY_AUDIT_ID}'::uuid),
    (SELECT count(*)
       FROM public.outbox_delivery_record
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND outbox_delivery_record_id = '${RETRY_OUTBOX_ID}'::uuid)
);
SQL
)"
if [[ "${final_truth}" != "1|1|1|1|0|0" ]]; then
    echo "uncertain-commit replay duplicated or replaced first-write durable truth: ${final_truth}" >&2
    exit 1
fi

echo "PostgreSQL Employment separation uncertain-commit recovery contract passed"
