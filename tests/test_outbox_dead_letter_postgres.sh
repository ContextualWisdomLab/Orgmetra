#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0002_sealed_evidence_digest.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0003_audit_outbox_persistence.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0004_outbox_delivery_claim.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0005_outbox_delivery_finalization.sql
if [[ -f database/migrations/0006_outbox_delivery_dead_letter.sql ]]; then
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0006_outbox_delivery_dead_letter.sql
fi

TENANT_ID="10000000-0000-7000-8000-000000000001"
EVENT_ID="00000000-0000-4000-8000-000000000081"
DELIVERY_ID="00000000-0000-4000-8000-000000000091"
ESCALATION_ID="00000000-0000-4000-8000-0000000000a1"
canonical_event='{"data":{"high_impact":false,"result_code":"recorded"},"datacontenttype":"application/json","id":"00000000-0000-4000-8000-000000000081","orgmetraactor":"keyverse_subject:01JACTOROPAQUE","orgmetraevidence":"employment-offer:v3","orgmetrapurpose":"workforce_administration","orgmetrareason":"hire_completion","orgmetratenant":"10000000-0000-7000-8000-000000000001","source":"urn:orgmetra:people_core","specversion":"1.0","subject":"assignment_record:01JTESTOPAQUE","time":"2026-08-17T03:00:00Z","type":"orgmetra.people.assignment.recorded"}'

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v tenant_id="${TENANT_ID}" \
    -v event_id="${EVENT_ID}" \
    -v delivery_id="${DELIVERY_ID}" \
    -v payload="${canonical_event}" <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES (:'tenant_id'::uuid, 'tenant_alpha');

SELECT record_audit_outbox_event(
    :'tenant_id'::uuid,
    :'event_id'::uuid,
    :'delivery_id'::uuid,
    :'payload',
    encode(digest(convert_to(:'payload', 'UTF8'), 'sha256'), 'hex'),
    'payroll_gateway'
);
SQL

first_claim="$(psql "${DATABASE_URL}" -Atq -v tenant_id="${TENANT_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT delivery_attempt_count::text || '|' || lease_owner_reference
FROM claim_outbox_delivery(
    :'tenant_id'::uuid,
    'payroll_gateway',
    'dispatcher_worker:dead-letter-owner',
    300
);
SQL
)"
if [[ "${first_claim}" != "1|dispatcher_worker:dead-letter-owner" ]]; then
    echo "dead-letter fixture was not leased on its first attempt: ${first_claim}" >&2
    exit 1
fi

# A live worker cannot discard work before the configured attempt budget has
# actually been consumed.
set +e
premature_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v tenant_id="${TENANT_ID}" \
    -v delivery_id="${DELIVERY_ID}" \
    -v escalation_id="${ESCALATION_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT dead_letter_outbox_delivery(
    :'tenant_id'::uuid,
    :'delivery_id'::uuid,
    :'escalation_id'::uuid,
    'dispatcher_worker:dead-letter-owner',
    'remote_contract_rejected',
    'incident_case:INC-2026-0001',
    2
);
SQL
} 2>&1)"
premature_status=$?
set -e
if [[ ${premature_status} -eq 0 || "${premature_output}" != *"outbox delivery attempt budget is not exhausted"* ]]; then
    echo "delivery was dead-lettered before retry budget exhaustion or failed for the wrong reason: ${premature_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v tenant_id="${TENANT_ID}" -v delivery_id="${DELIVERY_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT retry_outbox_delivery(
    :'tenant_id'::uuid,
    :'delivery_id'::uuid,
    'dispatcher_worker:dead-letter-owner',
    'remote_timeout',
    1
);
SQL
sleep 1.2

second_claim="$(psql "${DATABASE_URL}" -Atq -v tenant_id="${TENANT_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT delivery_attempt_count::text || '|' || lease_owner_reference
FROM claim_outbox_delivery(
    :'tenant_id'::uuid,
    'payroll_gateway',
    'dispatcher_worker:dead-letter-owner',
    300
);
SQL
)"
if [[ "${second_claim}" != "2|dispatcher_worker:dead-letter-owner" ]]; then
    echo "dead-letter fixture did not reach its second owned attempt: ${second_claim}" >&2
    exit 1
fi

# Lease ownership remains a capability boundary even after the retry budget is
# exhausted.
set +e
foreign_owner_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v tenant_id="${TENANT_ID}" \
    -v delivery_id="${DELIVERY_ID}" \
    -v escalation_id="${ESCALATION_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT dead_letter_outbox_delivery(
    :'tenant_id'::uuid,
    :'delivery_id'::uuid,
    :'escalation_id'::uuid,
    'dispatcher_worker:foreign-worker',
    'remote_contract_rejected',
    'incident_case:INC-2026-0001',
    2
);
SQL
} 2>&1)"
foreign_owner_status=$?
set -e
if [[ ${foreign_owner_status} -eq 0 || "${foreign_owner_output}" != *"outbox lease is not owned by caller"* ]]; then
    echo "foreign worker dead-lettered another worker's lease or failed for the wrong reason: ${foreign_owner_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v tenant_id="${TENANT_ID}" \
    -v delivery_id="${DELIVERY_ID}" \
    -v escalation_id="${ESCALATION_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT dead_letter_outbox_delivery(
    :'tenant_id'::uuid,
    :'delivery_id'::uuid,
    :'escalation_id'::uuid,
    'dispatcher_worker:dead-letter-owner',
    'remote_contract_rejected',
    'incident_case:INC-2026-0001',
    2
);
SQL

dead_letter_state="$(psql "${DATABASE_URL}" -Atq -v tenant_id="${TENANT_ID}" -v delivery_id="${DELIVERY_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT
    delivery_state_code || '|'
    || delivery_attempt_count::text || '|'
    || (lease_owner_reference IS NULL)::text || '|'
    || (lease_expires_at IS NULL)::text || '|'
    || last_failure_code || '|'
    || (delivered_at IS NULL)::text
FROM outbox_delivery_record
WHERE outbox_delivery_record_id = :'delivery_id'::uuid;
SQL
)"
if [[ "${dead_letter_state}" != "dead_lettered|2|true|true|remote_contract_rejected|true" ]]; then
    echo "dead-letter transition did not preserve terminal failure state: ${dead_letter_state}" >&2
    exit 1
fi

escalation_state="$(psql "${DATABASE_URL}" -Atq \
    -v tenant_id="${TENANT_ID}" \
    -v delivery_id="${DELIVERY_ID}" \
    -v escalation_id="${ESCALATION_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT
    outbox_delivery_escalation_record_id::text || '|'
    || outbox_delivery_record_id::text || '|'
    || terminal_attempt_count::text || '|'
    || failure_code || '|'
    || escalation_reference || '|'
    || (recorded_at IS NOT NULL)::text
FROM outbox_delivery_escalation_record
WHERE outbox_delivery_record_id = :'delivery_id'::uuid;
SQL
)"
if [[ "${escalation_state}" != "${ESCALATION_ID}|${DELIVERY_ID}|2|remote_contract_rejected|incident_case:INC-2026-0001|true" ]]; then
    echo "immutable escalation evidence was not recorded correctly: ${escalation_state}" >&2
    exit 1
fi

# Dead-lettered work is terminal: normal dispatch cannot reclaim it.
terminal_claim="$(psql "${DATABASE_URL}" -Atq -v tenant_id="${TENANT_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT outbox_delivery_record_id::text
FROM claim_outbox_delivery(
    :'tenant_id'::uuid,
    'payroll_gateway',
    'dispatcher_worker:next-worker',
    300
);
SQL
)"
if [[ -n "${terminal_claim}" ]]; then
    echo "dead-lettered delivery re-entered normal dispatch: ${terminal_claim}" >&2
    exit 1
fi

# Escalation evidence itself is append-only and therefore suitable for
# acquisition/SOC-2 evidence trails without claiming certification.
set +e
mutation_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v tenant_id="${TENANT_ID}" \
    -v escalation_id="${ESCALATION_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
UPDATE outbox_delivery_escalation_record
SET failure_code = 'tampered_failure'
WHERE outbox_delivery_escalation_record_id = :'escalation_id'::uuid;
SQL
} 2>&1)"
mutation_status=$?
set -e
if [[ ${mutation_status} -eq 0 || "${mutation_output}" != *"outbox delivery escalation records are append-only"* ]]; then
    echo "dead-letter escalation evidence was mutable or failed for the wrong reason: ${mutation_output}" >&2
    exit 1
fi

echo "PostgreSQL outbox dead-letter and immutable escalation contract passed"
