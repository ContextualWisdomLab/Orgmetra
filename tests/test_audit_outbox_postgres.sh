#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0002_sealed_evidence_digest.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0003_audit_outbox_persistence.sql

canonical_event='{"data":{"high_impact":true,"result_code":"recorded"},"datacontenttype":"application/json","id":"00000000-0000-4000-8000-000000000041","orgmetraactor":"keyverse_subject:01JACTOROPAQUE","orgmetraconfirmation":"confirmation:01JCONFIRMOPAQUE","orgmetraevidence":"employment-offer:v3","orgmetrapurpose":"workforce_administration","orgmetrareason":"hire_completion","orgmetratenant":"10000000-0000-7000-8000-000000000001","source":"urn:orgmetra:people_core","specversion":"1.0","subject":"assignment_record:01JTESTOPAQUE","time":"2026-08-17T01:30:00Z","type":"orgmetra.people.assignment.recorded"}'
canonical_digest='a44386b624f932e320b1f94c4ff56df93fac1b0e27906124f8058a6846dad9a1'

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('10000000-0000-7000-8000-000000000001', 'tenant_alpha');
SQL

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v canonical_event="${canonical_event}" \
    -v canonical_digest="${canonical_digest}" <<'SQL'
SELECT record_audit_outbox_event(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-4000-8000-000000000041'::uuid,
    '00000000-0000-4000-8000-000000000051'::uuid,
    :'canonical_event',
    :'canonical_digest',
    'integration_hub'
);
SQL

audit_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM audit_event_record
WHERE tenant_record_id = '10000000-0000-7000-8000-000000000001'::uuid
  AND audit_event_record_id = '00000000-0000-4000-8000-000000000041'::uuid;
")"
outbox_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM outbox_delivery_record
WHERE tenant_record_id = '10000000-0000-7000-8000-000000000001'::uuid
  AND outbox_delivery_record_id = '00000000-0000-4000-8000-000000000051'::uuid
  AND delivery_state_code = 'pending'
  AND delivery_attempt_count = 0;
")"
if [[ "${audit_count}" != "1" || "${outbox_count}" != "1" ]]; then
    echo "transactional audit/outbox insert did not persist exactly one immutable event and pending delivery" >&2
    exit 1
fi

verified_digest="$(psql "${DATABASE_URL}" -Atqc "
SELECT encode(digest(convert_to(canonical_event_json, 'UTF8'), 'sha256'), 'hex') = event_envelope_digest
FROM audit_event_record
WHERE audit_event_record_id = '00000000-0000-4000-8000-000000000041'::uuid;
")"
if [[ "${verified_digest}" != "t" ]]; then
    echo "database did not verify the exact canonical event bytes against the stored digest" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
CREATE ROLE orgmetra_audit_reader NOLOGIN NOBYPASSRLS;
GRANT USAGE ON SCHEMA public TO orgmetra_audit_reader;
GRANT SELECT ON audit_event_record, outbox_delivery_record TO orgmetra_audit_reader;
SET ROLE orgmetra_audit_reader;

DO $$
DECLARE
    audit_visible bigint;
    outbox_visible bigint;
BEGIN
    SELECT count(*) INTO audit_visible FROM audit_event_record;
    SELECT count(*) INTO outbox_visible FROM outbox_delivery_record;
    IF audit_visible <> 0 OR outbox_visible <> 0 THEN
        RAISE EXCEPTION 'missing tenant context exposed audit/outbox rows';
    END IF;
END;
$$;

SET orgmetra.tenant_record_id = '10000000-0000-7000-8000-000000000001';
DO $$
DECLARE
    audit_visible bigint;
    outbox_visible bigint;
BEGIN
    SELECT count(*) INTO audit_visible FROM audit_event_record;
    SELECT count(*) INTO outbox_visible FROM outbox_delivery_record;
    IF audit_visible <> 1 OR outbox_visible <> 1 THEN
        RAISE EXCEPTION 'tenant alpha did not see exactly one audit and one outbox row';
    END IF;
END;
$$;

SET orgmetra.tenant_record_id = '20000000-0000-7000-8000-000000000001';
DO $$
DECLARE
    audit_visible bigint;
    outbox_visible bigint;
BEGIN
    SELECT count(*) INTO audit_visible FROM audit_event_record;
    SELECT count(*) INTO outbox_visible FROM outbox_delivery_record;
    IF audit_visible <> 0 OR outbox_visible <> 0 THEN
        RAISE EXCEPTION 'foreign tenant context exposed tenant-alpha audit/outbox rows';
    END IF;
END;
$$;
RESET ROLE;
SQL

set +e
tampered_digest_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v canonical_event="${canonical_event}" <<'SQL'
SELECT record_audit_outbox_event(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-4000-8000-000000000042'::uuid,
    '00000000-0000-4000-8000-000000000052'::uuid,
    replace(:'canonical_event', '000000000041', '000000000042'),
    repeat('0', 64),
    'integration_hub'
);
SQL
} 2>&1)"
tampered_digest_status=$?
set -e
if [[ ${tampered_digest_status} -eq 0 || "${tampered_digest_output}" != *"audit event envelope failed database validation"* ]]; then
    echo "digest-tampered event was not rejected at the durable audit boundary: ${tampered_digest_output}" >&2
    exit 1
fi

set +e
pii_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v canonical_event="${canonical_event}" <<'SQL'
WITH unsafe_payload AS (
    SELECT jsonb_set(
        replace(:'canonical_event', '000000000041', '000000000043')::jsonb,
        '{employee_name}',
        to_jsonb('Ada Lovelace'::text),
        true
    )::text AS payload
)
SELECT record_audit_outbox_event(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-4000-8000-000000000043'::uuid,
    '00000000-0000-4000-8000-000000000053'::uuid,
    payload,
    encode(digest(convert_to(payload, 'UTF8'), 'sha256'), 'hex'),
    'integration_hub'
)
FROM unsafe_payload;
SQL
} 2>&1)"
pii_status=$?
set -e
if [[ ${pii_status} -eq 0 || "${pii_output}" != *"audit event envelope failed database validation"* ]]; then
    echo "PII-bearing extra event field escaped the allowlisted audit envelope: ${pii_output}" >&2
    exit 1
fi

set +e
missing_confirmation_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v canonical_event="${canonical_event}" <<'SQL'
WITH unsafe_payload AS (
    SELECT (replace(:'canonical_event', '000000000041', '000000000044')::jsonb - 'orgmetraconfirmation')::text AS payload
)
SELECT record_audit_outbox_event(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-4000-8000-000000000044'::uuid,
    '00000000-0000-4000-8000-000000000054'::uuid,
    payload,
    encode(digest(convert_to(payload, 'UTF8'), 'sha256'), 'hex'),
    'integration_hub'
)
FROM unsafe_payload;
SQL
} 2>&1)"
missing_confirmation_status=$?
set -e
if [[ ${missing_confirmation_status} -eq 0 || "${missing_confirmation_output}" != *"audit event envelope failed database validation"* ]]; then
    echo "high-impact event without accountable confirmation escaped persistence validation: ${missing_confirmation_output}" >&2
    exit 1
fi

set +e
immutable_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE audit_event_record
SET event_envelope_digest = repeat('f', 64)
WHERE audit_event_record_id = '00000000-0000-4000-8000-000000000041'::uuid;
SQL
} 2>&1)"
immutable_status=$?
set -e
if [[ ${immutable_status} -eq 0 || "${immutable_output}" != *"audit event records are append-only"* ]]; then
    echo "immutable audit evidence accepted an update or failed for the wrong reason: ${immutable_output}" >&2
    exit 1
fi

set +e
immutable_delete_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
DELETE FROM audit_event_record
WHERE audit_event_record_id = '00000000-0000-4000-8000-000000000041'::uuid;
SQL
} 2>&1)"
immutable_delete_status=$?
set -e
if [[ ${immutable_delete_status} -eq 0 || "${immutable_delete_output}" != *"audit event records are append-only"* ]]; then
    echo "immutable audit evidence accepted a delete or failed for the wrong reason: ${immutable_delete_output}" >&2
    exit 1
fi

set +e
invalid_transition_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE outbox_delivery_record
SET delivery_state_code = 'delivered',
    delivered_at = now()
WHERE outbox_delivery_record_id = '00000000-0000-4000-8000-000000000051'::uuid;
SQL
} 2>&1)"
invalid_transition_status=$?
set -e
if [[ ${invalid_transition_status} -eq 0 || "${invalid_transition_output}" != *"outbox delivery must transition pending -> leased before completion"* ]]; then
    echo "outbox bypassed its lease transition: ${invalid_transition_output}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE outbox_delivery_record
SET delivery_state_code = 'leased',
    delivery_attempt_count = delivery_attempt_count + 1,
    lease_owner_reference = 'dispatcher_worker:01JLEASEOWNER',
    lease_expires_at = now() + interval '5 minutes'
WHERE outbox_delivery_record_id = '00000000-0000-4000-8000-000000000051'::uuid;

UPDATE outbox_delivery_record
SET delivery_state_code = 'delivered',
    lease_owner_reference = NULL,
    lease_expires_at = NULL,
    delivered_at = now(),
    last_failure_code = NULL
WHERE outbox_delivery_record_id = '00000000-0000-4000-8000-000000000051'::uuid;
SQL

delivered_state="$(psql "${DATABASE_URL}" -Atqc "
SELECT delivery_state_code || ':' || delivery_attempt_count::text || ':' || (delivered_at IS NOT NULL)::text
FROM outbox_delivery_record
WHERE outbox_delivery_record_id = '00000000-0000-4000-8000-000000000051'::uuid;
")"
if [[ "${delivered_state}" != "delivered:1:true" ]]; then
    echo "valid leased delivery did not reach an accountable terminal state: ${delivered_state}" >&2
    exit 1
fi

set +e
delivered_mutation_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE outbox_delivery_record
SET last_failure_code = 'late_mutation'
WHERE outbox_delivery_record_id = '00000000-0000-4000-8000-000000000051'::uuid;
SQL
} 2>&1)"
delivered_mutation_status=$?
set -e
if [[ ${delivered_mutation_status} -eq 0 || "${delivered_mutation_output}" != *"delivered outbox records are immutable"* ]]; then
    echo "terminal delivery state accepted later mutation: ${delivered_mutation_output}" >&2
    exit 1
fi

set +e
atomicity_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -v canonical_event="${canonical_event}" <<'SQL'
WITH next_payload AS (
    SELECT replace(:'canonical_event', '000000000041', '000000000045') AS payload
)
SELECT record_audit_outbox_event(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-4000-8000-000000000045'::uuid,
    '00000000-0000-4000-8000-000000000051'::uuid,
    payload,
    encode(digest(convert_to(payload, 'UTF8'), 'sha256'), 'hex'),
    'integration_hub'
)
FROM next_payload;
SQL
} 2>&1)"
atomicity_status=$?
set -e
if [[ ${atomicity_status} -eq 0 ]]; then
    echo "duplicate outbox identity unexpectedly succeeded" >&2
    exit 1
fi
rolled_back_audit_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM audit_event_record
WHERE audit_event_record_id = '00000000-0000-4000-8000-000000000045'::uuid;
")"
if [[ "${rolled_back_audit_count}" != "0" ]]; then
    echo "failed outbox insert left orphaned audit evidence instead of rolling back atomically" >&2
    exit 1
fi

assert_reserved_uuid_rejected() {
    local case_name="$1"
    local event_id="$2"
    local delivery_id="$3"
    local expected_label="$4"
    local payload
    local output
    local status

    payload="${canonical_event/00000000-0000-4000-8000-000000000041/${event_id}}"

    set +e
    output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
        -v event_id="${event_id}" \
        -v delivery_id="${delivery_id}" \
        -v payload="${payload}" <<'SQL'
SELECT record_audit_outbox_event(
    '10000000-0000-7000-8000-000000000001'::uuid,
    :'event_id'::uuid,
    :'delivery_id'::uuid,
    :'payload',
    encode(digest(convert_to(:'payload', 'UTF8'), 'sha256'), 'hex'),
    'integration_hub'
);
SQL
    } 2>&1)"
    status=$?
    set -e

    if [[ ${status} -eq 0 || "${output}" != *"audit/outbox identity uses reserved UUID sentinel"* ]]; then
        echo "${expected_label} escaped ${case_name} identity validation or failed for the wrong reason: ${output}" >&2
        exit 1
    fi
}

assert_reserved_uuid_rejected \
    "audit-event" \
    "00000000-0000-0000-0000-000000000000" \
    "00000000-0000-4000-8000-000000000061" \
    "RFC 9562 Nil UUID"
assert_reserved_uuid_rejected \
    "audit-event" \
    "ffffffff-ffff-ffff-ffff-ffffffffffff" \
    "00000000-0000-4000-8000-000000000062" \
    "RFC 9562 Max UUID"
assert_reserved_uuid_rejected \
    "outbox-delivery" \
    "00000000-0000-4000-8000-000000000063" \
    "00000000-0000-0000-0000-000000000000" \
    "RFC 9562 Nil UUID"
assert_reserved_uuid_rejected \
    "outbox-delivery" \
    "00000000-0000-4000-8000-000000000064" \
    "ffffffff-ffff-ffff-ffff-ffffffffffff" \
    "RFC 9562 Max UUID"

echo "PostgreSQL immutable audit/outbox persistence contract passed"
