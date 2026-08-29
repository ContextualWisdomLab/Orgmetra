#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

for migration in \
    database/migrations/0001_foundation_schema.sql \
    database/migrations/0002_sealed_evidence_digest.sql \
    database/migrations/0003_audit_outbox_persistence.sql \
    database/migrations/0004_outbox_delivery_claim.sql \
    database/migrations/0005_outbox_delivery_finalization.sql \
    database/migrations/0006_outbox_delivery_dead_letter.sql \
    database/migrations/0007_outbox_retry_exhaustion.sql \
    database/migrations/0008_audit_outbox_review_hardening.sql \
    database/migrations/0016_outbox_retry_policy.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

TENANT_ALPHA="10000000-0000-7000-8000-000000000001"
TENANT_BETA="10000000-0000-7000-8000-000000000002"
EVENT_ALPHA="00000000-0000-4000-8000-000000000181"
DELIVERY_ALPHA="00000000-0000-4000-8000-000000000191"
POLICY_ALPHA="00000000-0000-4000-8000-0000000001a1"

canonical_event='{"data":{"high_impact":false,"result_code":"recorded"},"datacontenttype":"application/json","id":"00000000-0000-4000-8000-000000000181","orgmetraactor":"keyverse_subject:01JACTOROPAQUE","orgmetraevidence":"employment-offer:v3","orgmetrapurpose":"workforce_administration","orgmetrareason":"hire_completion","orgmetratenant":"10000000-0000-7000-8000-000000000001","source":"urn:orgmetra:people_core","specversion":"1.0","subject":"assignment_record:01JTESTOPAQUE","time":"2026-08-17T03:00:00Z","type":"orgmetra.people.assignment.recorded"}'

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v tenant_alpha="${TENANT_ALPHA}" \
    -v tenant_beta="${TENANT_BETA}" \
    -v event_alpha="${EVENT_ALPHA}" \
    -v delivery_alpha="${DELIVERY_ALPHA}" \
    -v policy_alpha="${POLICY_ALPHA}" \
    -v payload="${canonical_event}" <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES
    (:'tenant_alpha'::uuid, 'tenant_alpha'),
    (:'tenant_beta'::uuid, 'tenant_beta');

SET orgmetra.tenant_record_id = :'tenant_alpha';

INSERT INTO outbox_retry_policy_record (
    tenant_record_id,
    outbox_retry_policy_record_id,
    delivery_target_code,
    policy_version,
    base_delay_seconds,
    maximum_delay_seconds,
    recorded_from
)
VALUES (
    :'tenant_alpha'::uuid,
    :'policy_alpha'::uuid,
    'payroll_gateway',
    1,
    2,
    8,
    transaction_timestamp()
);

SELECT record_audit_outbox_event(
    :'tenant_alpha'::uuid,
    :'event_alpha'::uuid,
    :'delivery_alpha'::uuid,
    :'payload',
    encode(digest(convert_to(:'payload', 'UTF8'), 'sha256'), 'hex'),
    'payroll_gateway'
);

DO $orgmetra_retry_policy_reader$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_catalog.pg_roles
        WHERE rolname = 'orgmetra_retry_policy_reader'
    ) THEN
        RAISE EXCEPTION 'retry policy reader role unexpectedly pre-exists';
    END IF;
    CREATE ROLE orgmetra_retry_policy_reader NOLOGIN NOBYPASSRLS;
END;
$orgmetra_retry_policy_reader$;
GRANT USAGE ON SCHEMA public TO orgmetra_retry_policy_reader;
GRANT SELECT ON outbox_retry_policy_record TO orgmetra_retry_policy_reader;
SQL

set +e
backdated_policy_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v tenant_alpha="${TENANT_ALPHA}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_alpha';
INSERT INTO outbox_retry_policy_record (
    tenant_record_id,
    outbox_retry_policy_record_id,
    delivery_target_code,
    policy_version,
    base_delay_seconds,
    maximum_delay_seconds,
    recorded_from
)
VALUES (
    :'tenant_alpha'::uuid,
    '00000000-0000-4000-8000-0000000001b1'::uuid,
    'benefits_gateway',
    1,
    2,
    8,
    '2000-01-01T00:00:00Z'::timestamptz
);
SQL
} 2>&1)"
backdated_policy_status=$?
set -e
if [[ ${backdated_policy_status} -eq 0 || "${backdated_policy_output}" != *"recorded_from must equal current transaction time"* ]]; then
    echo "retry policy accepted forged historical system-recorded time or failed for the wrong reason: ${backdated_policy_output}" >&2
    exit 1
fi

policy_visibility="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atq \
    -v tenant_alpha="${TENANT_ALPHA}" \
    -v tenant_beta="${TENANT_BETA}" <<'SQL'
SET ROLE orgmetra_retry_policy_reader;
SET orgmetra.tenant_record_id = :'tenant_alpha';
SELECT count(*)::text FROM outbox_retry_policy_record;
SET orgmetra.tenant_record_id = :'tenant_beta';
SELECT count(*)::text FROM outbox_retry_policy_record;
RESET ROLE;
SQL
)"
if [[ "${policy_visibility}" != $'1\n0' ]]; then
    echo "retry policy RLS did not isolate tenants: ${policy_visibility}" >&2
    exit 1
fi

computed_delays="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atq <<'SQL'
SELECT string_agg(
    calculate_outbox_retry_delay_seconds(attempt_count, 2, 8)::text,
    ',' ORDER BY attempt_count
)
FROM generate_series(1, 6) AS attempt_series(attempt_count);
SQL
)"
if [[ "${computed_delays}" != "2,4,8,8,8,8" ]]; then
    echo "retry backoff was not exponential and capped: ${computed_delays}" >&2
    exit 1
fi

first_claim="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atq -v tenant_alpha="${TENANT_ALPHA}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_alpha';
SELECT delivery_attempt_count::text
FROM claim_outbox_delivery(
    :'tenant_alpha'::uuid,
    'payroll_gateway',
    'dispatcher_worker:policy-owner',
    300
);
SQL
)"
if [[ "${first_claim}" != "1" ]]; then
    echo "retry policy fixture did not reach first leased attempt: ${first_claim}" >&2
    exit 1
fi

set +e
forged_delay_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v tenant_alpha="${TENANT_ALPHA}" \
    -v delivery_alpha="${DELIVERY_ALPHA}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_alpha';
SELECT retry_outbox_delivery(
    :'tenant_alpha'::uuid,
    :'delivery_alpha'::uuid,
    'dispatcher_worker:policy-owner',
    'remote_timeout',
    7
);
SQL
} 2>&1)"
forged_delay_status=$?
set -e
if [[ ${forged_delay_status} -eq 0 || "${forged_delay_output}" != *"retry delay does not match active outbox retry policy"* ]]; then
    echo "caller-selected retry delay bypassed active policy or failed for the wrong reason: ${forged_delay_output}" >&2
    exit 1
fi

retry_result="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atq \
    -v tenant_alpha="${TENANT_ALPHA}" \
    -v delivery_alpha="${DELIVERY_ALPHA}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_alpha';
WITH applied_policy AS (
    SELECT *
    FROM retry_outbox_delivery_with_policy(
        :'tenant_alpha'::uuid,
        :'delivery_alpha'::uuid,
        'dispatcher_worker:policy-owner',
        'remote_timeout'
    )
)
SELECT
    policy_version::text || '|'
    || retry_delay_seconds::text
FROM applied_policy;
SQL
)"
if [[ "${retry_result}" != "1|2" ]]; then
    echo "governed retry did not use the active durable policy: ${retry_result}" >&2
    exit 1
fi

retry_state="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atq \
    -v tenant_alpha="${TENANT_ALPHA}" \
    -v delivery_alpha="${DELIVERY_ALPHA}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_alpha';
SELECT
    delivery_state_code || '|'
    || delivery_attempt_count::text || '|'
    || last_failure_code || '|'
    || (available_at >= transaction_timestamp() + interval '1 second')::text || '|'
    || (available_at <= transaction_timestamp() + interval '3 seconds')::text
FROM outbox_delivery_record
WHERE outbox_delivery_record_id = :'delivery_alpha'::uuid;
SQL
)"
if [[ "${retry_state}" != "pending|1|remote_timeout|true|true" ]]; then
    echo "governed retry did not preserve bounded state and delay: ${retry_state}" >&2
    exit 1
fi

sleep 2.2
second_claim="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atq -v tenant_alpha="${TENANT_ALPHA}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_alpha';
SELECT delivery_attempt_count::text
FROM claim_outbox_delivery(
    :'tenant_alpha'::uuid,
    'payroll_gateway',
    'dispatcher_worker:policy-owner',
    300
);
SQL
)"
if [[ "${second_claim}" != "2" ]]; then
    echo "retry policy fixture did not reach second leased attempt: ${second_claim}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v tenant_alpha="${TENANT_ALPHA}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_alpha';
UPDATE outbox_retry_policy_record
SET recorded_to = transaction_timestamp()
WHERE tenant_record_id = :'tenant_alpha'::uuid
  AND delivery_target_code = 'payroll_gateway'
  AND recorded_to IS NULL;
SQL

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v tenant_alpha="${TENANT_ALPHA}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_alpha';
INSERT INTO outbox_retry_policy_record (
    tenant_record_id,
    outbox_retry_policy_record_id,
    delivery_target_code,
    policy_version,
    base_delay_seconds,
    maximum_delay_seconds,
    recorded_from
)
VALUES (
    :'tenant_alpha'::uuid,
    '00000000-0000-4000-8000-0000000001a2'::uuid,
    'payroll_gateway',
    2,
    4,
    16,
    transaction_timestamp()
);
SQL

set +e
backdated_close_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v tenant_alpha="${TENANT_ALPHA}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_alpha';
UPDATE outbox_retry_policy_record
SET recorded_to = recorded_from + interval '1 microsecond'
WHERE tenant_record_id = :'tenant_alpha'::uuid
  AND outbox_retry_policy_record_id = '00000000-0000-4000-8000-0000000001a2'::uuid;
SQL
} 2>&1)"
backdated_close_status=$?
set -e
if [[ ${backdated_close_status} -eq 0 || "${backdated_close_output}" != *"recorded_to must equal current transaction time"* ]]; then
    echo "retry policy accepted a forged historical recorded_to or failed for the wrong reason: ${backdated_close_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v tenant_alpha="${TENANT_ALPHA}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_alpha';
UPDATE outbox_retry_policy_record
SET recorded_to = transaction_timestamp()
WHERE tenant_record_id = :'tenant_alpha'::uuid
  AND outbox_retry_policy_record_id = '00000000-0000-4000-8000-0000000001a2'::uuid;
SQL

set +e
missing_policy_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v tenant_alpha="${TENANT_ALPHA}" \
    -v delivery_alpha="${DELIVERY_ALPHA}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_alpha';
SELECT *
FROM retry_outbox_delivery_with_policy(
    :'tenant_alpha'::uuid,
    :'delivery_alpha'::uuid,
    'dispatcher_worker:policy-owner',
    'remote_timeout'
);
SQL
} 2>&1)"
missing_policy_status=$?
set -e
if [[ ${missing_policy_status} -eq 0 || "${missing_policy_output}" != *"active outbox retry policy not found"* ]]; then
    echo "governed retry did not fail closed without active policy: ${missing_policy_output}" >&2
    exit 1
fi

set +e
overlap_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v tenant_alpha="${TENANT_ALPHA}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_alpha';
INSERT INTO outbox_retry_policy_record (
    tenant_record_id,
    outbox_retry_policy_record_id,
    delivery_target_code,
    policy_version,
    base_delay_seconds,
    maximum_delay_seconds,
    recorded_from
)
VALUES
    (:'tenant_alpha'::uuid, '00000000-0000-4000-8000-0000000001a2'::uuid,
     'payroll_gateway', 2, 4, 16, transaction_timestamp()),
    (:'tenant_alpha'::uuid, '00000000-0000-4000-8000-0000000001a3'::uuid,
     'payroll_gateway', 3, 8, 32, transaction_timestamp());
SQL
} 2>&1)"
overlap_status=$?
set -e
if [[ ${overlap_status} -eq 0 ]]; then
    echo "multiple active retry policies were accepted for one tenant/target" >&2
    exit 1
fi

printf '%s\n' "outbox retry policy PostgreSQL contract passed"
