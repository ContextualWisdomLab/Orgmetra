#!/usr/bin/env bash
set -euo pipefail

: "${POSTGRES_ADMIN_URL:=postgresql://orgmetra:orgmetra@localhost:5432/postgres}"
: "${POSTGRES_CLIENT_CONTAINER:?POSTGRES_CLIENT_CONTAINER is required}"

SOURCE_DATABASE_NAME="orgmetra_recovery_source"
RESTORE_DATABASE_NAME="orgmetra_recovery_target"
SOURCE_DATABASE_URL="${POSTGRES_ADMIN_URL%/postgres}/${SOURCE_DATABASE_NAME}"
RESTORE_DATABASE_URL="${POSTGRES_ADMIN_URL%/postgres}/${RESTORE_DATABASE_NAME}"
DUMP_PATH="$(mktemp -t orgmetra-recovery-XXXXXX.dump)"
TENANT_ID="10000000-0000-7000-8000-000000000001"
PERSON_ID="00000000-0000-7000-8000-000000000101"
NAME_ID="00000000-0000-7000-8000-000000000102"
AUDIT_ID="00000000-0000-7000-8000-000000000103"
OUTBOX_ID="00000000-0000-7000-8000-000000000104"

cleanup() {
    rm -f "${DUMP_PATH}"
    psql "${POSTGRES_ADMIN_URL}" -v ON_ERROR_STOP=1 -c \
        "DROP DATABASE IF EXISTS ${RESTORE_DATABASE_NAME} WITH (FORCE);" >/dev/null || true
    psql "${POSTGRES_ADMIN_URL}" -v ON_ERROR_STOP=1 -c \
        "DROP DATABASE IF EXISTS ${SOURCE_DATABASE_NAME} WITH (FORCE);" >/dev/null || true
}
trap cleanup EXIT

psql "${POSTGRES_ADMIN_URL}" -v ON_ERROR_STOP=1 -c \
    "DROP DATABASE IF EXISTS ${RESTORE_DATABASE_NAME} WITH (FORCE);" >/dev/null
psql "${POSTGRES_ADMIN_URL}" -v ON_ERROR_STOP=1 -c \
    "DROP DATABASE IF EXISTS ${SOURCE_DATABASE_NAME} WITH (FORCE);" >/dev/null
psql "${POSTGRES_ADMIN_URL}" -v ON_ERROR_STOP=1 -c \
    "CREATE DATABASE ${SOURCE_DATABASE_NAME};" >/dev/null

for migration in \
    database/migrations/0001_foundation_schema.sql \
    database/migrations/0002_sealed_evidence_digest.sql \
    database/migrations/0003_audit_outbox_persistence.sql \
    database/migrations/0004_outbox_delivery_claim.sql \
    database/migrations/0005_outbox_delivery_finalization.sql \
    database/migrations/0006_outbox_delivery_dead_letter.sql \
    database/migrations/0007_outbox_retry_exhaustion.sql \
    database/migrations/0008_audit_outbox_review_hardening.sql \
    database/migrations/0009_candidate_worker_conversion_governance.sql; do
    psql "${SOURCE_DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}" >/dev/null
done

canonical_event='{"data":{"high_impact":false,"result_code":"rehearsal_seeded"},"datacontenttype":"application/json","id":"00000000-0000-7000-8000-000000000103","orgmetraactor":"operator_subject:restore_rehearsal","orgmetraevidence":"recovery_rehearsal:v1","orgmetrapurpose":"business_continuity","orgmetrareason":"restore_rehearsal","orgmetratenant":"10000000-0000-7000-8000-000000000001","source":"urn:orgmetra:recovery_evidence","specversion":"1.0","subject":"person_record:00000000-0000-7000-8000-000000000101","time":"2026-08-18T00:00:00Z","type":"orgmetra.recovery.restore_rehearsed"}'

PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
psql "${SOURCE_DATABASE_URL}" -v ON_ERROR_STOP=1 -v canonical_event="${canonical_event}" <<'SQL' >/dev/null
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('10000000-0000-7000-8000-000000000001', 'recovery_rehearsal_tenant');

INSERT INTO person_record (
    tenant_record_id,
    person_record_id,
    recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000101',
    TIMESTAMPTZ '2026-08-17 23:59:00+00'
);

INSERT INTO person_name_record (
    tenant_record_id,
    person_name_record_id,
    person_record_id,
    display_name,
    effective_from,
    recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001',
    '00000000-0000-7000-8000-000000000102',
    '00000000-0000-7000-8000-000000000101',
    'Recovery Rehearsal Worker',
    DATE '2026-08-18',
    TIMESTAMPTZ '2026-08-18 00:00:00+00'
);

SELECT record_audit_outbox_event(
    '10000000-0000-7000-8000-000000000001'::uuid,
    '00000000-0000-7000-8000-000000000103'::uuid,
    '00000000-0000-7000-8000-000000000104'::uuid,
    :'canonical_event',
    encode(digest(convert_to(:'canonical_event', 'UTF8'), 'sha256'), 'hex'),
    'recovery_event_sink'
);
SQL

docker exec "${POSTGRES_CLIENT_CONTAINER}" \
    pg_dump --format=custom "${SOURCE_DATABASE_URL}" > "${DUMP_PATH}"
psql "${POSTGRES_ADMIN_URL}" -v ON_ERROR_STOP=1 -c \
    "CREATE DATABASE ${RESTORE_DATABASE_NAME};" >/dev/null
docker exec -i "${POSTGRES_CLIENT_CONTAINER}" \
    pg_restore --exit-on-error --dbname="${RESTORE_DATABASE_URL}" < "${DUMP_PATH}" >/dev/null

bitemporal_count="$(PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
    psql "${RESTORE_DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM person_name_record
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND person_record_id = '${PERSON_ID}'::uuid
  AND display_name = 'Recovery Rehearsal Worker'
  AND effective_from <= DATE '2026-08-18'
  AND (effective_to IS NULL OR effective_to > DATE '2026-08-18')
  AND recorded_from <= TIMESTAMPTZ '2026-08-18 00:01:00+00'
  AND (recorded_to IS NULL OR recorded_to > TIMESTAMPTZ '2026-08-18 00:01:00+00');
")"
if [[ "${bitemporal_count}" != "1" ]]; then
    echo "bitemporal person name did not survive restore" >&2
    exit 1
fi

digest_count="$(PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
    psql "${RESTORE_DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM audit_event_record
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND audit_event_record_id = '${AUDIT_ID}'::uuid
  AND digest_algorithm_code = 'sha256'
  AND encode(digest(convert_to(canonical_event_json, 'UTF8'), 'sha256'), 'hex') = event_envelope_digest;
")"
if [[ "${digest_count}" != "1" ]]; then
    echo "audit digest did not survive restore" >&2
    exit 1
fi

binding_count="$(PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
    psql "${RESTORE_DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM outbox_delivery_record AS delivery_record
JOIN audit_event_record AS audit_record
  ON audit_record.tenant_record_id = delivery_record.tenant_record_id
 AND audit_record.audit_event_record_id = delivery_record.audit_event_record_id
WHERE delivery_record.tenant_record_id = '${TENANT_ID}'::uuid
  AND delivery_record.outbox_delivery_record_id = '${OUTBOX_ID}'::uuid
  AND delivery_record.audit_event_record_id = '${AUDIT_ID}'::uuid
  AND delivery_record.delivery_state_code = 'pending';
")"
if [[ "${binding_count}" != "1" ]]; then
    echo "audit/outbox binding did not survive restore" >&2
    exit 1
fi

set +e
mutable_output="$(PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
    psql "${RESTORE_DATABASE_URL}" -v ON_ERROR_STOP=1 -c \
    "UPDATE audit_event_record SET recorded_at = recorded_at + INTERVAL '1 second' WHERE audit_event_record_id = '${AUDIT_ID}'::uuid;" 2>&1)"
mutable_status=$?
set -e
if [[ ${mutable_status} -eq 0 ]]; then
    echo "restored audit event was mutable" >&2
    exit 1
fi
if [[ "${mutable_output}" != *"audit event records are append-only"* ]]; then
    echo "restored audit mutation failed for an unexpected reason: ${mutable_output}" >&2
    exit 1
fi

set +e
truncate_output="$(PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
    psql "${RESTORE_DATABASE_URL}" -v ON_ERROR_STOP=1 -c \
    "TRUNCATE TABLE audit_event_record;" 2>&1)"
truncate_status=$?
set -e
if [[ ${truncate_status} -eq 0 ]]; then
    echo "restored audit history was truncatable" >&2
    exit 1
fi
if [[ "${truncate_output}" != *"audit event records cannot be truncated"* ]]; then
    echo "restored audit TRUNCATE failed for an unexpected reason: ${truncate_output}" >&2
    exit 1
fi

recovery_owner_count="$(psql "${RESTORE_DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM pg_proc AS function_record
JOIN pg_namespace AS namespace_record
  ON namespace_record.oid = function_record.pronamespace
WHERE namespace_record.nspname = 'public'
  AND function_record.proname = 'operator_dead_letter_expired_outbox_delivery'
  AND pg_get_userbyid(function_record.proowner) = 'orgmetra_outbox_recovery_owner'
  AND function_record.prosecdef;
")"
if [[ "${recovery_owner_count}" != "1" ]]; then
    echo "privileged recovery function ownership did not survive restore" >&2
    exit 1
fi

printf '%s\n' "PostgreSQL restore rehearsal passed for exact restored database ${RESTORE_DATABASE_NAME}."
