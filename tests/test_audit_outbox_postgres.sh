#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0002_sealed_evidence_digest.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0003_transactional_audit_outbox.sql

TENANT_ID='10000000-0000-7000-8000-000000000001'
CANDIDATE_ID='00000000-0000-7000-8000-000000000101'
OUTBOX_ID='00000000-0000-7000-8000-000000000102'
EVENT_ID='00000000-0000-7000-8000-000000000103'

canonical_event='{"data":{"high_impact":false,"result_code":"recorded"},"datacontenttype":"application/json","id":"00000000-0000-7000-8000-000000000103","orgmetraactor":"keyverse_subject:01JACTOROPAQUE","orgmetraevidence":"candidate-create:v1","orgmetrapurpose":"talent_acquisition","orgmetrareason":"candidate_created","orgmetratenant":"10000000-0000-7000-8000-000000000001","source":"urn:orgmetra:people_core","specversion":"1.0","subject":"candidate_profile:01JTESTOPAQUE","time":"2026-08-17T02:30:00Z","type":"orgmetra.people.candidate.recorded"}'
event_digest="$(printf '%s' "${canonical_event}" | sha256sum | awk '{print $1}')"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('${TENANT_ID}', 'tenant_alpha');

BEGIN;
INSERT INTO candidate_profile (
    tenant_record_id, candidate_profile_id, application_status_code
) VALUES (
    '${TENANT_ID}', '${CANDIDATE_ID}', 'active'
);
INSERT INTO audit_outbox_record (
    tenant_record_id,
    audit_outbox_record_id,
    event_id,
    event_envelope_text,
    digest_algorithm_code,
    event_content_digest,
    recorded_at
) VALUES (
    '${TENANT_ID}',
    '${OUTBOX_ID}',
    '${EVENT_ID}',
    :'event_envelope',
    'sha256',
    :'event_digest',
    TIMESTAMPTZ '2026-08-17 02:30:01+00'
);
COMMIT;
SQL

persisted_pair="$(psql "${DATABASE_URL}" -Atqc "
SELECT
    (SELECT count(*) FROM candidate_profile
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND candidate_profile_id = '${CANDIDATE_ID}'::uuid)::text
    || ':' ||
    (SELECT count(*) FROM audit_outbox_record
      WHERE tenant_record_id = '${TENANT_ID}'::uuid
        AND event_id = '${EVENT_ID}'::uuid)::text;
")"
if [[ "${persisted_pair}" != "1:1" ]]; then
    echo "business write and audit outbox append did not commit together: ${persisted_pair}" >&2
    exit 1
fi

stored_digest="$(psql "${DATABASE_URL}" -Atqc "
SELECT event_content_digest
FROM audit_outbox_record
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND event_id = '${EVENT_ID}'::uuid;
")"
if [[ "${stored_digest}" != "${event_digest}" ]]; then
    echo "stored event digest differs from exact canonical envelope bytes" >&2
    exit 1
fi

ROLLBACK_CANDIDATE_ID='00000000-0000-7000-8000-000000000104'
ROLLBACK_OUTBOX_ID='00000000-0000-7000-8000-000000000105'
ROLLBACK_EVENT_ID='00000000-0000-7000-8000-000000000106'
rollback_event="${canonical_event//${EVENT_ID}/${ROLLBACK_EVENT_ID}}"

set +e
rollback_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v event_envelope="${rollback_event}" <<SQL
BEGIN;
INSERT INTO candidate_profile (
    tenant_record_id, candidate_profile_id, application_status_code
) VALUES (
    '${TENANT_ID}', '${ROLLBACK_CANDIDATE_ID}', 'active'
);
INSERT INTO audit_outbox_record (
    tenant_record_id,
    audit_outbox_record_id,
    event_id,
    event_envelope_text,
    digest_algorithm_code,
    event_content_digest
) VALUES (
    '${TENANT_ID}',
    '${ROLLBACK_OUTBOX_ID}',
    '${ROLLBACK_EVENT_ID}',
    :'event_envelope',
    'sha256',
    repeat('0', 64)
);
COMMIT;
SQL
} 2>&1)"
rollback_status=$?
set -e
if [[ ${rollback_status} -eq 0 ]]; then
    echo "transaction accepted an audit envelope with a forged digest" >&2
    exit 1
fi
if [[ "${rollback_output}" != *"audit outbox digest does not match exact envelope bytes"* ]]; then
    echo "forged digest failed for an unexpected reason: ${rollback_output}" >&2
    exit 1
fi

rolled_back_business_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM candidate_profile
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND candidate_profile_id = '${ROLLBACK_CANDIDATE_ID}'::uuid;
")"
if [[ "${rolled_back_business_count}" != "0" ]]; then
    echo "business mutation survived a failed same-transaction audit append" >&2
    exit 1
fi

set +e
update_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
UPDATE audit_outbox_record
SET event_content_digest = repeat('f', 64)
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND event_id = '${EVENT_ID}'::uuid;
SQL
} 2>&1)"
update_status=$?
set -e
if [[ ${update_status} -eq 0 ]]; then
    echo "append-only audit outbox record accepted an update" >&2
    exit 1
fi
if [[ "${update_output}" != *"append-only relation cannot be updated or deleted"* ]]; then
    echo "audit update failed for an unexpected reason: ${update_output}" >&2
    exit 1
fi

set +e
delete_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
DELETE FROM audit_outbox_record
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND event_id = '${EVENT_ID}'::uuid;
SQL
} 2>&1)"
delete_status=$?
set -e
if [[ ${delete_status} -eq 0 ]]; then
    echo "append-only audit outbox record accepted a delete" >&2
    exit 1
fi
if [[ "${delete_output}" != *"append-only relation cannot be updated or deleted"* ]]; then
    echo "audit delete failed for an unexpected reason: ${delete_output}" >&2
    exit 1
fi

MISMATCH_OUTBOX_ID='00000000-0000-7000-8000-000000000107'
MISMATCH_EVENT_ID='00000000-0000-7000-8000-000000000108'
mismatch_event="${canonical_event//${EVENT_ID}/${MISMATCH_EVENT_ID}}"
mismatch_event="${mismatch_event//${TENANT_ID}/20000000-0000-7000-8000-000000000001}"
mismatch_digest="$(printf '%s' "${mismatch_event}" | sha256sum | awk '{print $1}')"

set +e
mismatch_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v event_envelope="${mismatch_event}" -v event_digest="${mismatch_digest}" <<SQL
INSERT INTO audit_outbox_record (
    tenant_record_id, audit_outbox_record_id, event_id,
    event_envelope_text, digest_algorithm_code, event_content_digest
) VALUES (
    '${TENANT_ID}', '${MISMATCH_OUTBOX_ID}', '${MISMATCH_EVENT_ID}',
    :'event_envelope', 'sha256', :'event_digest'
);
SQL
} 2>&1)"
mismatch_status=$?
set -e
if [[ ${mismatch_status} -eq 0 ]]; then
    echo "audit outbox accepted an envelope for a different tenant" >&2
    exit 1
fi
if [[ "${mismatch_output}" != *"audit envelope tenant does not match owning tenant"* ]]; then
    echo "tenant mismatch failed for an unexpected reason: ${mismatch_output}" >&2
    exit 1
fi

HIGH_IMPACT_OUTBOX_ID='00000000-0000-7000-8000-000000000109'
HIGH_IMPACT_EVENT_ID='00000000-0000-7000-8000-000000000110'
high_impact_event="${canonical_event//${EVENT_ID}/${HIGH_IMPACT_EVENT_ID}}"
high_impact_event="${high_impact_event/\"high_impact\":false/\"high_impact\":true}"
high_impact_digest="$(printf '%s' "${high_impact_event}" | sha256sum | awk '{print $1}')"

set +e
high_impact_output="$({ psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v event_envelope="${high_impact_event}" -v event_digest="${high_impact_digest}" <<SQL
INSERT INTO audit_outbox_record (
    tenant_record_id, audit_outbox_record_id, event_id,
    event_envelope_text, digest_algorithm_code, event_content_digest
) VALUES (
    '${TENANT_ID}', '${HIGH_IMPACT_OUTBOX_ID}', '${HIGH_IMPACT_EVENT_ID}',
    :'event_envelope', 'sha256', :'event_digest'
);
SQL
} 2>&1)"
high_impact_status=$?
set -e
if [[ ${high_impact_status} -eq 0 ]]; then
    echo "high-impact audit envelope accepted without human confirmation" >&2
    exit 1
fi
if [[ "${high_impact_output}" != *"high-impact audit envelope requires accountable human confirmation"* ]]; then
    echo "missing confirmation failed for an unexpected reason: ${high_impact_output}" >&2
    exit 1
fi

rls_state="$(psql "${DATABASE_URL}" -Atqc "
SELECT relrowsecurity::text || ':' || relforcerowsecurity::text
FROM pg_class
WHERE oid = 'audit_outbox_record'::regclass;
")"
if [[ "${rls_state}" != "true:true" ]]; then
    echo "audit outbox relation does not force tenant RLS: ${rls_state}" >&2
    exit 1
fi

policy_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM pg_policies
WHERE schemaname = current_schema()
  AND tablename = 'audit_outbox_record'
  AND policyname = 'audit_outbox_scope_policy';
")"
if [[ "${policy_count}" != "1" ]]; then
    echo "audit outbox tenant scope policy is missing" >&2
    exit 1
fi
