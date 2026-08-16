#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0002_sealed_evidence_digest.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0003_audit_outbox_persistence.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0004_outbox_delivery_claim.sql

TENANT_ID="10000000-0000-7000-8000-000000000001"
canonical_event='{"data":{"high_impact":false,"result_code":"recorded"},"datacontenttype":"application/json","id":"00000000-0000-4000-8000-000000000061","orgmetraactor":"keyverse_subject:01JACTOROPAQUE","orgmetraevidence":"employment-offer:v3","orgmetrapurpose":"workforce_administration","orgmetrareason":"hire_completion","orgmetratenant":"10000000-0000-7000-8000-000000000001","source":"urn:orgmetra:people_core","specversion":"1.0","subject":"assignment_record:01JTESTOPAQUE","time":"2026-08-17T02:30:00Z","type":"orgmetra.people.assignment.recorded"}'

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v tenant_id="${TENANT_ID}" <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES (:'tenant_id'::uuid, 'tenant_alpha');
SQL

seed_delivery() {
    local event_id="$1"
    local delivery_id="$2"
    local delivery_target="$3"
    local payload

    payload="${canonical_event/00000000-0000-4000-8000-000000000061/${event_id}}"
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
        -v tenant_id="${TENANT_ID}" \
        -v event_id="${event_id}" \
        -v delivery_id="${delivery_id}" \
        -v delivery_target="${delivery_target}" \
        -v payload="${payload}" <<'SQL'
SELECT record_audit_outbox_event(
    :'tenant_id'::uuid,
    :'event_id'::uuid,
    :'delivery_id'::uuid,
    :'payload',
    encode(digest(convert_to(:'payload', 'UTF8'), 'sha256'), 'hex'),
    :'delivery_target'
);
SQL
}

seed_delivery \
    "00000000-0000-4000-8000-000000000061" \
    "00000000-0000-4000-8000-000000000071" \
    "integration_hub"
sleep 0.05
seed_delivery \
    "00000000-0000-4000-8000-000000000062" \
    "00000000-0000-4000-8000-000000000072" \
    "integration_hub"

# RED regression: a lease that is already expired is not an actionable claim and
# must never enter the durable leased state, even through a direct table write.
set +e
past_lease_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v tenant_id="${TENANT_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
UPDATE outbox_delivery_record
SET delivery_state_code = 'leased',
    delivery_attempt_count = delivery_attempt_count + 1,
    lease_owner_reference = 'dispatcher_worker:past-lease',
    lease_expires_at = transaction_timestamp() - interval '1 second'
WHERE outbox_delivery_record_id = '00000000-0000-4000-8000-000000000071'::uuid;
SQL
} 2>&1)"
past_lease_status=$?
set -e
if [[ ${past_lease_status} -eq 0 || "${past_lease_output}" != *"lease expiry must be in the future"* ]]; then
    echo "already-expired lease was accepted or failed for the wrong reason: ${past_lease_output}" >&2
    exit 1
fi

first_claim="$(psql "${DATABASE_URL}" -Atq \
    -v tenant_id="${TENANT_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT
    outbox_delivery_record_id::text
    || '|' || delivery_attempt_count::text
    || '|' || lease_owner_reference
    || '|' || (lease_expires_at > transaction_timestamp())::text
    || '|' || delivery_target_code
FROM claim_outbox_delivery(
    :'tenant_id'::uuid,
    'integration_hub',
    'dispatcher_worker:worker-a',
    300
);
SQL
)"
if [[ "${first_claim}" != "00000000-0000-4000-8000-000000000071|1|dispatcher_worker:worker-a|true|integration_hub" ]]; then
    echo "earliest eligible delivery was not claimed with an accountable future lease: ${first_claim}" >&2
    exit 1
fi

second_claim="$(psql "${DATABASE_URL}" -Atq \
    -v tenant_id="${TENANT_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT
    outbox_delivery_record_id::text
    || '|' || delivery_attempt_count::text
    || '|' || lease_owner_reference
    || '|' || (lease_expires_at > transaction_timestamp())::text
FROM claim_outbox_delivery(
    :'tenant_id'::uuid,
    'integration_hub',
    'dispatcher_worker:worker-b',
    300
);
SQL
)"
if [[ "${second_claim}" != "00000000-0000-4000-8000-000000000072|1|dispatcher_worker:worker-b|true" ]]; then
    echo "second dispatcher did not claim the next eligible delivery: ${second_claim}" >&2
    exit 1
fi

empty_claim="$(psql "${DATABASE_URL}" -Atq \
    -v tenant_id="${TENANT_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT outbox_delivery_record_id::text
FROM claim_outbox_delivery(
    :'tenant_id'::uuid,
    'integration_hub',
    'dispatcher_worker:worker-c',
    300
);
SQL
)"
if [[ -n "${empty_claim}" ]]; then
    echo "dispatcher reclaimed a live lease instead of returning no work: ${empty_claim}" >&2
    exit 1
fi

# A crashed dispatcher must not strand a leased row forever. Claim a dedicated
# delivery with a one-second lease, allow it to expire, and require the next
# dispatcher to atomically reclaim the same row with a new attempt and explicit
# lease-expiry failure evidence. The current implementation selects pending rows
# only, so this is the regression that must turn RED before the recovery repair.
seed_delivery \
    "00000000-0000-4000-8000-000000000063" \
    "00000000-0000-4000-8000-000000000073" \
    "recovery_channel"

recovery_first_claim="$(psql "${DATABASE_URL}" -Atq \
    -v tenant_id="${TENANT_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT
    outbox_delivery_record_id::text
    || '|' || delivery_attempt_count::text
    || '|' || lease_owner_reference
FROM claim_outbox_delivery(
    :'tenant_id'::uuid,
    'recovery_channel',
    'dispatcher_worker:recovery-a',
    1
);
SQL
)"
if [[ "${recovery_first_claim}" != "00000000-0000-4000-8000-000000000073|1|dispatcher_worker:recovery-a" ]]; then
    echo "recovery fixture was not leased by the first dispatcher: ${recovery_first_claim}" >&2
    exit 1
fi

sleep 1.2

recovered_claim="$(psql "${DATABASE_URL}" -Atq \
    -v tenant_id="${TENANT_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT
    outbox_delivery_record_id::text
    || '|' || delivery_attempt_count::text
    || '|' || lease_owner_reference
    || '|' || (lease_expires_at > transaction_timestamp())::text
FROM claim_outbox_delivery(
    :'tenant_id'::uuid,
    'recovery_channel',
    'dispatcher_worker:recovery-b',
    300
);
SQL
)"
if [[ "${recovered_claim}" != "00000000-0000-4000-8000-000000000073|2|dispatcher_worker:recovery-b|true" ]]; then
    echo "expired dispatcher lease was not safely reclaimed: ${recovered_claim}" >&2
    exit 1
fi

recovery_failure_code="$(psql "${DATABASE_URL}" -Atq \
    -v tenant_id="${TENANT_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT last_failure_code
FROM outbox_delivery_record
WHERE outbox_delivery_record_id = '00000000-0000-4000-8000-000000000073'::uuid;
SQL
)"
if [[ "${recovery_failure_code}" != "lease_expired" ]]; then
    echo "expired lease takeover did not preserve explicit recovery evidence: ${recovery_failure_code}" >&2
    exit 1
fi

# A caller cannot use a tenant identifier parameter to escape its active tenant
# context, even when its database role otherwise has broad table privileges.
set +e
foreign_tenant_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v tenant_id="${TENANT_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT *
FROM claim_outbox_delivery(
    '20000000-0000-7000-8000-000000000001'::uuid,
    'integration_hub',
    'dispatcher_worker:worker-a',
    300
);
SQL
} 2>&1)"
foreign_tenant_status=$?
set -e
if [[ ${foreign_tenant_status} -eq 0 || "${foreign_tenant_output}" != *"outbox claim tenant context does not match requested tenant"* ]]; then
    echo "foreign-tenant claim was accepted or failed for the wrong reason: ${foreign_tenant_output}" >&2
    exit 1
fi

set +e
invalid_owner_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v tenant_id="${TENANT_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT *
FROM claim_outbox_delivery(
    :'tenant_id'::uuid,
    'integration_hub',
    'worker A',
    300
);
SQL
} 2>&1)"
invalid_owner_status=$?
set -e
if [[ ${invalid_owner_status} -eq 0 || "${invalid_owner_output}" != *"lease owner must be a namespaced opaque reference"* ]]; then
    echo "nonopaque lease owner was accepted or failed for the wrong reason: ${invalid_owner_output}" >&2
    exit 1
fi

set +e
invalid_duration_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v tenant_id="${TENANT_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT *
FROM claim_outbox_delivery(
    :'tenant_id'::uuid,
    'integration_hub',
    'dispatcher_worker:worker-a',
    0
);
SQL
} 2>&1)"
invalid_duration_status=$?
set -e
if [[ ${invalid_duration_status} -eq 0 || "${invalid_duration_output}" != *"lease duration must be between 1 and 3600 seconds"* ]]; then
    echo "invalid lease duration was accepted or failed for the wrong reason: ${invalid_duration_output}" >&2
    exit 1
fi

echo "PostgreSQL atomic outbox claim and expired-lease recovery contract passed"
