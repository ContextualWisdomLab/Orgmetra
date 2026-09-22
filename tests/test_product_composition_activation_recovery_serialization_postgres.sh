#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

for migration in \
    database/migrations/0001_foundation_schema.sql \
    database/migrations/0018_product_composition_generation_registry.sql \
    database/migrations/0019_product_composition_activation_registry.sql \
    database/migrations/0020_product_composition_activation_authority_enforcement.sql \
    database/migrations/0021_product_composition_activation_observation_wall_clock.sql \
    database/migrations/0022_product_composition_recovery_attestation.sql \
    database/migrations/0023_product_composition_deployment_write_serialization.sql \
    database/migrations/0024_product_composition_activation_trigger_function_provenance.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO product_composition_deployment (deployment_id, environment_id)
VALUES ('orgmetra_gateway', 'production');
SQL

holder_pid=""
holder_application_name=""
writer_pid=""
cleanup() {
    if [[ -n "${writer_pid}" ]]; then
        kill "${writer_pid}" 2>/dev/null || true
        wait "${writer_pid}" 2>/dev/null || true
    fi
    if [[ -n "${holder_application_name}" ]]; then
        psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE application_name = '${holder_application_name}';
        " >/dev/null 2>&1 || true
    fi
    if [[ -n "${holder_pid}" ]]; then
        wait "${holder_pid}" 2>/dev/null || true
    fi
}
trap cleanup EXIT

wait_for_query_state() {
    local application_name="$1"
    local expected_wait_event_type="$2"
    local attempts=100
    local observed=""
    for ((attempt = 1; attempt <= attempts; attempt += 1)); do
        observed="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
            SELECT COALESCE(wait_event_type, '')
            FROM pg_stat_activity
            WHERE application_name = '${application_name}'
              AND state = 'active'
            LIMIT 1;
        ")"
        if [[ "${observed}" == "${expected_wait_event_type}" ]]; then
            return 0
        fi
        sleep 0.05
    done
    echo "${application_name} did not reach wait_event_type=${expected_wait_event_type}; observed=${observed}" >&2
    return 1
}

start_deployment_lock_holder() {
    local application_name="$1"
    holder_application_name="${application_name}"
    PGAPPNAME="${application_name}" psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 >/tmp/orgmetra-composition-holder.log 2>&1 <<'SQL' &
BEGIN;
SELECT 1
FROM product_composition_deployment
WHERE deployment_id = 'orgmetra_gateway'
  AND environment_id = 'production'
FOR UPDATE;
SELECT pg_sleep(30);
ROLLBACK;
SQL
    holder_pid=$!
    wait_for_query_state "${application_name}" "Timeout"
}

release_holder() {
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE application_name = '${holder_application_name}';
    " >/dev/null
    wait "${holder_pid}" 2>/dev/null || true
    holder_pid=""
    holder_application_name=""
}

start_deployment_lock_holder "composition_lock_holder_activation"
set +e
PGAPPNAME="composition_activation_direct_writer" psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 >/tmp/orgmetra-composition-activation-writer.log 2>&1 <<'SQL' &
INSERT INTO product_composition_activation_event (
    deployment_id,
    environment_id,
    activation_sequence,
    generation_id,
    previous_generation_id,
    event_kind,
    evidence_bundle_sha256
) VALUES (
    'orgmetra_gateway',
    'production',
    1,
    'generation_one',
    NULL,
    'activate',
    repeat('7', 64)
);
SQL
writer_pid=$!
set -e
wait_for_query_state "composition_activation_direct_writer" "Lock"
release_holder
set +e
wait "${writer_pid}"
activation_status=$?
set -e
writer_pid=""
if [[ ${activation_status} -eq 0 ]]; then
    echo "invalid activation writer unexpectedly committed after deployment lock release" >&2
    exit 1
fi

start_deployment_lock_holder "composition_lock_holder_recovery"
set +e
PGAPPNAME="composition_recovery_direct_writer" psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 >/tmp/orgmetra-composition-recovery-writer.log 2>&1 <<'SQL' &
INSERT INTO product_composition_recovery_attestation (
    deployment_id,
    environment_id,
    recovery_sequence,
    activation_sequence,
    generation_id,
    evidence_bundle_sha256
) VALUES (
    'orgmetra_gateway',
    'production',
    1,
    1,
    'generation_one',
    repeat('8', 64)
);
SQL
writer_pid=$!
set -e
wait_for_query_state "composition_recovery_direct_writer" "Lock"
release_holder
set +e
wait "${writer_pid}"
recovery_status=$?
set -e
writer_pid=""
if [[ ${recovery_status} -eq 0 ]]; then
    echo "invalid recovery writer unexpectedly committed after deployment lock release" >&2
    exit 1
fi

if ! grep -q "activation evidence does not bind exact deployment generation" /tmp/orgmetra-composition-activation-writer.log; then
    cat /tmp/orgmetra-composition-activation-writer.log >&2
    echo "activation writer did not continue into the existing lineage guard after lock release" >&2
    exit 1
fi

if ! grep -q "recovery attestation must bind the current active generation" /tmp/orgmetra-composition-recovery-writer.log; then
    cat /tmp/orgmetra-composition-recovery-writer.log >&2
    echo "recovery writer did not continue into the existing recovery guard after lock release" >&2
    exit 1
fi
