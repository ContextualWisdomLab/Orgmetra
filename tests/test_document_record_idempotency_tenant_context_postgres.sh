#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

for migration in \
    database/migrations/0001_foundation_schema.sql \
    database/migrations/0002_sealed_evidence_digest.sql \
    database/migrations/0021_document_record_persistence.sql \
    database/migrations/0022_document_record_evidence_unique_keys.sql \
    database/migrations/0023_document_record_canonical_encoding.sql \
    database/migrations/0024_document_record_idempotent_persistence.sql; do
    if [[ ! -f "${migration}" ]]; then
        echo "required document-record tenant-context migration is missing: ${migration}" >&2
        exit 1
    fi
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

SESSION_TENANT_ID="10000000-0000-7000-8000-000000000001"
REQUESTED_TENANT_ID="20000000-0000-7000-8000-000000000002"
DOCUMENT_ID="00000000-0000-7000-8000-000000000231"
DOCUMENT_REFERENCE="document_record:00000000-0000-4000-8000-000000000231"
PERSON_REFERENCE="person_record:00000000-0000-4000-8000-000000000211"
EMPLOYMENT_REFERENCE="employment_record:00000000-0000-4000-8000-000000000221"
UPLOADER="actor:00000000-0000-4000-8000-000000000261"
PERSISTED_BY="actor:00000000-0000-4000-8000-000000000262"
ARTIFACT_REFERENCE="document_artifact:00000000-0000-4000-8000-000000000241"
RETENTION_REFERENCE="retention_policy:00000000-0000-4000-8000-000000000251"
AUDIT_REFERENCE="audit_event:00000000-0000-4000-8000-000000000271"
OUTBOX_REFERENCE="outbox_event:00000000-0000-4000-8000-000000000272"
IDEMPOTENCY_KEY="document-record-persist-00000000-0000-4000-8000-000000000201"
ARTIFACT_DIGEST="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
SOURCE_DIGEST="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
RETENTION_DIGEST="cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
APPLICATION_DIGEST="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"

IFS='|' read -r RECEIVED_AT EVIDENCE_RECORDED_AT < <(psql "${DATABASE_URL}" -Atqc "
SELECT
    to_char((pg_catalog.transaction_timestamp() - interval '2 minutes') AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"'),
    to_char((pg_catalog.transaction_timestamp() - interval '1 minute') AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"');
")
export RECEIVED_AT EVIDENCE_RECORDED_AT

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES
    ('${SESSION_TENANT_ID}', 'tenant_alpha'),
    ('${REQUESTED_TENANT_ID}', 'tenant_beta');
SQL

mapfile -t evidence_parts < <(
    python3 - "${REQUESTED_TENANT_ID}" "${DOCUMENT_REFERENCE}" "${ARTIFACT_REFERENCE}" <<'PY'
import json
import os
import sys
from hashlib import sha256

tenant_id, document_reference, artifact_reference = sys.argv[1:]
payload = {
    "artifact_digest": "a" * 64,
    "artifact_reference": artifact_reference,
    "classification_code": "restricted_hr",
    "content_storage_state": "artifact_reference_only",
    "decision_authority_state": "not_authorized_for_employment_decision",
    "document_category_code": "employment_contract",
    "document_record_reference": document_reference,
    "employment_record_reference": "employment_record:00000000-0000-4000-8000-000000000221",
    "person_record_reference": "person_record:00000000-0000-4000-8000-000000000211",
    "received_at": os.environ["RECEIVED_AT"],
    "recorded_at": os.environ["EVIDENCE_RECORDED_AT"],
    "retention_policy_digest": "c" * 64,
    "retention_policy_reference": "retention_policy:00000000-0000-4000-8000-000000000251",
    "schema_version": "orgmetra.document_record_evidence.v1",
    "source_provenance_digest": "b" * 64,
    "tenant_record_id": tenant_id,
    "uploader_actor_reference": "actor:00000000-0000-4000-8000-000000000261",
}
canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
print(canonical)
print(sha256(canonical.encode("utf-8")).hexdigest())
PY
)
CANONICAL_EVIDENCE="${evidence_parts[0]}"
EVIDENCE_DIGEST="${evidence_parts[1]}"

set +e
cross_tenant_output="$(
    PGOPTIONS="-c orgmetra.tenant_record_id=${SESSION_TENANT_ID}" \
    psql "${DATABASE_URL}" -Atq -v ON_ERROR_STOP=1 \
        -v canonical_evidence="${CANONICAL_EVIDENCE}" 2>&1 <<SQL
SELECT *
FROM public.persist_document_record_once(
    '${REQUESTED_TENANT_ID}'::uuid,
    '${IDEMPOTENCY_KEY}',
    '${DOCUMENT_ID}'::uuid,
    '${DOCUMENT_REFERENCE}',
    '${PERSON_REFERENCE}',
    '${EMPLOYMENT_REFERENCE}',
    '${UPLOADER}',
    '${PERSISTED_BY}',
    'employment_contract',
    '${ARTIFACT_REFERENCE}',
    '${ARTIFACT_DIGEST}',
    '${SOURCE_DIGEST}',
    '${RETENTION_REFERENCE}',
    '${RETENTION_DIGEST}',
    TIMESTAMPTZ '${RECEIVED_AT}',
    :'canonical_evidence',
    '${EVIDENCE_DIGEST}',
    '${AUDIT_REFERENCE}',
    '${OUTBOX_REFERENCE}',
    '${APPLICATION_DIGEST}'
);
SQL
)"
cross_tenant_status=$?
set -e

if [[ ${cross_tenant_status} -eq 0 || "${cross_tenant_output}" != *"document persistence tenant context does not match requested tenant"* ]]; then
    echo "document persistence did not fail closed at the tenant boundary: ${cross_tenant_output}" >&2
    exit 1
fi

cross_tenant_rows="$(psql "${DATABASE_URL}" -Atqc "
SELECT
    (SELECT count(*) FROM document_record
     WHERE tenant_record_id = '${REQUESTED_TENANT_ID}'::uuid
       AND document_record_id = '${DOCUMENT_ID}'::uuid)::text
    || '|' ||
    (SELECT count(*) FROM document_record_persist_receipt
     WHERE tenant_record_id = '${REQUESTED_TENANT_ID}'::uuid
       AND idempotency_key = '${IDEMPOTENCY_KEY}')::text;
")"
if [[ "${cross_tenant_rows}" != "0|0" ]]; then
    echo "cross-tenant persistence left durable document or receipt state: ${cross_tenant_rows}" >&2
    exit 1
fi

echo "document-record idempotency tenant-context contract passed"
