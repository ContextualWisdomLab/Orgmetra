#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0002_sealed_evidence_digest.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0003_audit_outbox_persistence.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0004_outbox_delivery_claim.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0005_outbox_delivery_finalization.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0006_outbox_delivery_dead_letter.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0007_outbox_retry_exhaustion.sql

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

# Retry exhaustion is a durable delivery policy, not a dispatcher-controlled
# function argument. A stale seven-argument function would let a worker choose
# 1 and immediately discard first-attempt work.
legacy_budget_signature="$(psql "${DATABASE_URL}" -Atq <<'SQL'
SELECT to_regprocedure(
    'dead_letter_outbox_delivery(uuid,uuid,uuid,text,text,text,integer)'
) IS NOT NULL;
SQL
)"
if [[ "${legacy_budget_signature}" != "f" ]]; then
    echo "dispatcher-controlled dead-letter budget signature is still callable" >&2
    exit 1
fi

first_claim="$(psql "${DATABASE_URL}" -Atq -v tenant_id="${TENANT_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
WITH claimed_delivery AS (
    SELECT *
    FROM claim_outbox_delivery(
        :'tenant_id'::uuid,
        'payroll_gateway',
        'dispatcher_worker:dead-letter-owner',
        300
    )
)
SELECT
    claimed_record.delivery_attempt_count::text || '|'
    || delivery_record.maximum_attempt_count::text || '|'
    || claimed_record.lease_owner_reference
FROM claimed_delivery AS claimed_record
JOIN outbox_delivery_record AS delivery_record
  ON delivery_record.outbox_delivery_record_id
     = claimed_record.outbox_delivery_record_id;
SQL
)"
if [[ "${first_claim}" != "1|5|dispatcher_worker:dead-letter-owner" ]]; then
    echo "dead-letter fixture did not expose the durable retry budget on first claim: ${first_claim}" >&2
    exit 1
fi

# Direct table DML cannot skip the governed terminal path even when it can
# otherwise satisfy the terminal row shape.
set +e
direct_dead_letter_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v tenant_id="${TENANT_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
UPDATE outbox_delivery_record
SET delivery_state_code = 'dead_lettered',
    lease_owner_reference = NULL,
    lease_expires_at = NULL,
    last_failure_code = 'direct_discard'
WHERE outbox_delivery_record_id = '00000000-0000-4000-8000-000000000091'::uuid;
SQL
} 2>&1)"
direct_dead_letter_status=$?
set -e
if [[ ${direct_dead_letter_status} -eq 0 || "${direct_dead_letter_output}" != *"dead-letter transition requires immutable escalation evidence and exhausted stored attempt budget"* ]]; then
    echo "direct DML bypassed governed dead-lettering or failed for the wrong reason: ${direct_dead_letter_output}" >&2
    exit 1
fi

# A live worker cannot discard work before the database-owned attempt budget has
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
    'incident_case:INC-2026-0001'
);
SQL
} 2>&1)"
premature_status=$?
set -e
if [[ ${premature_status} -eq 0 || "${premature_output}" != *"outbox delivery stored attempt budget is not exhausted"* ]]; then
    echo "delivery was dead-lettered before stored retry-budget exhaustion or failed for the wrong reason: ${premature_output}" >&2
    exit 1
fi

for expected_attempt in 2 3 4 5; do
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

    lease_duration_seconds=300
    if [[ ${expected_attempt} -eq 5 ]]; then
        lease_duration_seconds=5
    fi

    claimed_attempt="$(psql "${DATABASE_URL}" -Atq \
        -v tenant_id="${TENANT_ID}" \
        -v lease_duration_seconds="${lease_duration_seconds}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
WITH claimed_delivery AS (
    SELECT *
    FROM claim_outbox_delivery(
        :'tenant_id'::uuid,
        'payroll_gateway',
        'dispatcher_worker:dead-letter-owner',
        :'lease_duration_seconds'::integer
    )
)
SELECT
    claimed_record.delivery_attempt_count::text || '|'
    || delivery_record.maximum_attempt_count::text || '|'
    || claimed_record.lease_owner_reference
FROM claimed_delivery AS claimed_record
JOIN outbox_delivery_record AS delivery_record
  ON delivery_record.outbox_delivery_record_id
     = claimed_record.outbox_delivery_record_id;
SQL
)"
    if [[ "${claimed_attempt}" != "${expected_attempt}|5|dispatcher_worker:dead-letter-owner" ]]; then
        echo "dead-letter fixture did not reach durable attempt ${expected_attempt}: ${claimed_attempt}" >&2
        exit 1
    fi
done

# Once the database-owned attempt budget is exhausted, a dispatcher cannot put
# the row back into the pending queue and create an unbounded sixth attempt.
set +e
exhausted_retry_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v tenant_id="${TENANT_ID}" \
    -v delivery_id="${DELIVERY_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT retry_outbox_delivery(
    :'tenant_id'::uuid,
    :'delivery_id'::uuid,
    'dispatcher_worker:dead-letter-owner',
    'remote_timeout',
    1
);
SQL
} 2>&1)"
exhausted_retry_status=$?
set -e
if [[ ${exhausted_retry_status} -eq 0 || "${exhausted_retry_output}" != *"outbox delivery stored attempt budget is exhausted and requires terminal dead-lettering"* ]]; then
    echo "exhausted delivery re-entered retry or failed for the wrong reason: ${exhausted_retry_output}" >&2
    exit 1
fi

# A crashed final-attempt worker must not create attempt six after lease expiry.
# The exact recorded owner may still terminalize exhausted work so the queue
# cannot strand a permanently leased row when the final worker dies.
sleep 5.2
exhausted_reclaim="$(psql "${DATABASE_URL}" -Atq -v tenant_id="${TENANT_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT outbox_delivery_record_id::text
FROM claim_outbox_delivery(
    :'tenant_id'::uuid,
    'payroll_gateway',
    'dispatcher_worker:replacement-worker',
    300
);
SQL
)"
if [[ -n "${exhausted_reclaim}" ]]; then
    echo "expired exhausted delivery was reclaimed beyond its stored attempt budget: ${exhausted_reclaim}" >&2
    exit 1
fi

exhausted_state="$(psql "${DATABASE_URL}" -Atq -v tenant_id="${TENANT_ID}" -v delivery_id="${DELIVERY_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT
    delivery_state_code || '|'
    || delivery_attempt_count::text || '|'
    || maximum_attempt_count::text || '|'
    || lease_owner_reference || '|'
    || (lease_expires_at <= transaction_timestamp())::text
FROM outbox_delivery_record
WHERE outbox_delivery_record_id = :'delivery_id'::uuid;
SQL
)"
if [[ "${exhausted_state}" != "leased|5|5|dispatcher_worker:dead-letter-owner|true" ]]; then
    echo "exhausted final lease did not remain bounded and recoverable: ${exhausted_state}" >&2
    exit 1
fi

# Lease ownership remains a capability boundary even after the durable retry
# budget is exhausted, including an expired final lease.
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
    'incident_case:INC-2026-0001'
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
    'incident_case:INC-2026-0001'
);
SQL

dead_letter_state="$(psql "${DATABASE_URL}" -Atq -v tenant_id="${TENANT_ID}" -v delivery_id="${DELIVERY_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT
    delivery_state_code || '|'
    || delivery_attempt_count::text || '|'
    || maximum_attempt_count::text || '|'
    || (lease_owner_reference IS NULL)::text || '|'
    || (lease_expires_at IS NULL)::text || '|'
    || last_failure_code || '|'
    || (delivered_at IS NULL)::text
FROM outbox_delivery_record
WHERE outbox_delivery_record_id = :'delivery_id'::uuid;
SQL
)"
if [[ "${dead_letter_state}" != "dead_lettered|5|5|true|true|remote_contract_rejected|true" ]]; then
    echo "dead-letter transition did not preserve terminal failure state and stored budget: ${dead_letter_state}" >&2
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
if [[ "${escalation_state}" != "${ESCALATION_ID}|${DELIVERY_ID}|5|remote_contract_rejected|incident_case:INC-2026-0001|true" ]]; then
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

# Escalation evidence itself is append-only and its deferred binding proves it
# still describes the terminal queue row.
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

# An immutable escalation record cannot be fabricated for a delivery that has
# not reached terminal dead-letter state.
SECOND_EVENT_ID="00000000-0000-4000-8000-000000000082"
SECOND_DELIVERY_ID="00000000-0000-4000-8000-000000000092"
SECOND_ESCALATION_ID="00000000-0000-4000-8000-0000000000a2"
second_event="${canonical_event/00000000-0000-4000-8000-000000000081/${SECOND_EVENT_ID}}"
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v tenant_id="${TENANT_ID}" \
    -v event_id="${SECOND_EVENT_ID}" \
    -v delivery_id="${SECOND_DELIVERY_ID}" \
    -v payload="${second_event}" <<'SQL'
SELECT record_audit_outbox_event(
    :'tenant_id'::uuid,
    :'event_id'::uuid,
    :'delivery_id'::uuid,
    :'payload',
    encode(digest(convert_to(:'payload', 'UTF8'), 'sha256'), 'hex'),
    'payroll_gateway'
);
SQL
set +e
fabricated_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v tenant_id="${TENANT_ID}" \
    -v delivery_id="${SECOND_DELIVERY_ID}" \
    -v escalation_id="${SECOND_ESCALATION_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
INSERT INTO outbox_delivery_escalation_record (
    tenant_record_id,
    outbox_delivery_escalation_record_id,
    outbox_delivery_record_id,
    failure_code,
    escalation_reference,
    terminal_attempt_count
) VALUES (
    :'tenant_id'::uuid,
    :'escalation_id'::uuid,
    :'delivery_id'::uuid,
    'fabricated_failure',
    'incident_case:INC-2026-FAKE',
    1
);
SQL
} 2>&1)"
fabricated_status=$?
set -e
if [[ ${fabricated_status} -eq 0 || "${fabricated_output}" != *"outbox delivery escalation does not match terminal delivery state"* ]]; then
    echo "nonterminal escalation evidence was fabricated or failed for the wrong reason: ${fabricated_output}" >&2
    exit 1
fi

echo "PostgreSQL governed outbox dead-letter, bounded retry budget, exhausted-lease recovery, and immutable escalation contract passed"
