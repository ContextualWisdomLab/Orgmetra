#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

for migration in database/migrations/000{1..8}_*.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

TENANT_ID="10000000-0000-7000-8000-000000000001"
EVENT_ID="00000000-0000-4000-8000-0000000000b1"
INITIAL_DELIVERY_ID="00000000-0000-4000-8000-0000000000b2"
EXHAUSTED_DELIVERY_ID="00000000-0000-4000-8000-0000000000b3"
ESCALATION_ID="00000000-0000-4000-8000-0000000000b4"
canonical_event='{"data":{"high_impact":false,"result_code":"recorded"},"datacontenttype":"application/json","id":"00000000-0000-4000-8000-0000000000b1","orgmetraactor":"keyverse_subject:01JACTOROPAQUE","orgmetraevidence":"employment-offer:v3","orgmetrapurpose":"workforce_administration","orgmetrareason":"hire_completion","orgmetratenant":"10000000-0000-7000-8000-000000000001","source":"urn:orgmetra:people_core","specversion":"1.0","subject":"assignment_record:01JTESTOPAQUE","time":"2026-08-17T03:00:00Z","type":"orgmetra.people.assignment.recorded"}'

# Immutable evidence and mutable delivery state must both reject TRUNCATE. The
# audit probe uses CASCADE so the database reaches the statement trigger rather
# than stopping first at the outbox foreign-key dependency. The transaction is
# intentionally left uncommitted so a vulnerable implementation cannot destroy
# later fixtures during the RED run.
set +e
audit_truncate_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;
TRUNCATE public.audit_event_record CASCADE;
SQL
} 2>&1)"
audit_truncate_status=$?
set -e
if [[ ${audit_truncate_status} -eq 0 || "${audit_truncate_output}" != *"append-only"* ]]; then
    echo "audit evidence TRUNCATE was not rejected by the append-only boundary: ${audit_truncate_output}" >&2
    exit 1
fi

set +e
outbox_truncate_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;
TRUNCATE public.outbox_delivery_record;
SQL
} 2>&1)"
outbox_truncate_status=$?
set -e
if [[ ${outbox_truncate_status} -eq 0 || "${outbox_truncate_output}" != *"cannot be truncated"* ]]; then
    echo "outbox TRUNCATE was not rejected by the governed state boundary: ${outbox_truncate_output}" >&2
    exit 1
fi

# Boundary functions must resolve project objects through a trusted fixed path,
# not the caller's search_path. This is checked on representative read/write
# boundaries plus the immutable envelope validator.
search_path_contract="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atq <<'SQL'
SELECT count(*)
FROM pg_catalog.pg_proc AS procedure_record
WHERE procedure_record.oid IN (
    'public.validate_audit_event_envelope(text,uuid,uuid,text)'::regprocedure,
    'public.record_audit_outbox_event(uuid,uuid,uuid,text,text,text)'::regprocedure,
    'public.claim_outbox_delivery(uuid,text,text,integer)'::regprocedure,
    'public.retry_outbox_delivery(uuid,uuid,text,text,integer)'::regprocedure,
    'public.dead_letter_outbox_delivery(uuid,uuid,uuid,text,text,text)'::regprocedure
)
AND procedure_record.proconfig @> ARRAY['search_path=pg_catalog, public, pg_temp']::text[];
SQL
)"
if [[ "${search_path_contract}" != "5" ]]; then
    echo "not every audit/outbox boundary pins the trusted search_path: ${search_path_contract}/5" >&2
    exit 1
fi

hardening_definition="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atq <<'SQL'
SELECT pg_catalog.pg_get_functiondef(
    'public.validate_audit_event_envelope(text,uuid,uuid,text)'::regprocedure
);
SQL
)"
for required_fragment in 'event_keys IS NULL' 'IS DISTINCT FROM ARRAY' 'COLLATE "C"' 'make_date'; do
    if [[ "${hardening_definition}" != *"${required_fragment}"* ]]; then
        echo "immutable envelope validator is missing hardening fragment ${required_fragment}" >&2
        exit 1
    fi
done
if [[ "${hardening_definition}" == *"::timestamptz"* ]]; then
    echo "immutable envelope validator still depends on session-sensitive timestamptz input" >&2
    exit 1
fi

index_name="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atq <<'SQL'
SELECT pg_catalog.to_regclass('public.outbox_delivery_due_work_index')::text;
SQL
)"
if [[ "${index_name}" != "outbox_delivery_due_work_index" ]]; then
    echo "dispatcher due-work partial index is missing: ${index_name}" >&2
    exit 1
fi

# Build an exhausted one-attempt lease. The normal worker-owner path remains
# intact, but an expired final lease must also have a governed operator recovery
# path when the original worker identity is permanently lost.
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v tenant_id="${TENANT_ID}" \
    -v event_id="${EVENT_ID}" \
    -v initial_delivery_id="${INITIAL_DELIVERY_ID}" \
    -v exhausted_delivery_id="${EXHAUSTED_DELIVERY_ID}" \
    -v payload="${canonical_event}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
INSERT INTO public.tenant_record (tenant_record_id, tenant_reference)
VALUES (:'tenant_id'::uuid, 'tenant_hardening');

SELECT public.record_audit_outbox_event(
    :'tenant_id'::uuid,
    :'event_id'::uuid,
    :'initial_delivery_id'::uuid,
    :'payload',
    pg_catalog.encode(public.digest(pg_catalog.convert_to(:'payload', 'UTF8'), 'sha256'), 'hex'),
    'payroll_gateway'
);

INSERT INTO public.outbox_delivery_record (
    tenant_record_id,
    outbox_delivery_record_id,
    audit_event_record_id,
    delivery_target_code,
    maximum_attempt_count
) VALUES (
    :'tenant_id'::uuid,
    :'exhausted_delivery_id'::uuid,
    :'event_id'::uuid,
    'review_gateway',
    1
);

SELECT *
FROM public.claim_outbox_delivery(
    :'tenant_id'::uuid,
    'review_gateway',
    'dispatcher_worker:lost-final-owner',
    1
);
SQL

sleep 1.2

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v tenant_id="${TENANT_ID}" \
    -v delivery_id="${EXHAUSTED_DELIVERY_ID}" \
    -v escalation_id="${ESCALATION_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT public.operator_dead_letter_expired_outbox_delivery(
    :'tenant_id'::uuid,
    :'delivery_id'::uuid,
    :'escalation_id'::uuid,
    'operations_actor:queue-recovery-01',
    'lease_owner_lost'
);
SQL

recovered_state="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atq \
    -v tenant_id="${TENANT_ID}" \
    -v delivery_id="${EXHAUSTED_DELIVERY_ID}" \
    -v escalation_id="${ESCALATION_ID}" <<'SQL'
SET orgmetra.tenant_record_id = :'tenant_id';
SELECT
    delivery_record.delivery_state_code || '|'
    || delivery_record.delivery_attempt_count::text || '|'
    || delivery_record.maximum_attempt_count::text || '|'
    || escalation_record.failure_code || '|'
    || escalation_record.escalation_reference
FROM public.outbox_delivery_record AS delivery_record
JOIN public.outbox_delivery_escalation_record AS escalation_record
  ON escalation_record.tenant_record_id = delivery_record.tenant_record_id
 AND escalation_record.outbox_delivery_record_id = delivery_record.outbox_delivery_record_id
WHERE delivery_record.tenant_record_id = :'tenant_id'::uuid
  AND delivery_record.outbox_delivery_record_id = :'delivery_id'::uuid
  AND escalation_record.outbox_delivery_escalation_record_id = :'escalation_id'::uuid;
SQL
)"
if [[ "${recovered_state}" != "dead_lettered|1|1|lease_owner_lost|operations_actor:queue-recovery-01" ]]; then
    echo "operator recovery did not terminalize the expired exhausted lease with immutable evidence: ${recovered_state}" >&2
    exit 1
fi

echo "audit/outbox review hardening contract passed"