#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

for migration in \
    database/migrations/0001_foundation_schema.sql \
    database/migrations/0002_sealed_evidence_digest.sql \
    database/migrations/0021_document_record_persistence.sql; do
    if [[ ! -f "${migration}" ]]; then
        echo "required document-record persistence migration is missing: ${migration}" >&2
        exit 1
    fi
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

TENANT_ID="10000000-0000-7000-8000-000000000001"
OTHER_TENANT_ID="20000000-0000-7000-8000-000000000002"
DOCUMENT_ID="00000000-0000-7000-8000-000000000031"
DOCUMENT_REFERENCE="document_record:00000000-0000-4000-8000-000000000031"
PERSON_REFERENCE="person_record:00000000-0000-4000-8000-000000000011"
EMPLOYMENT_REFERENCE="employment_record:00000000-0000-4000-8000-000000000021"
ARTIFACT_REFERENCE="document_artifact:00000000-0000-4000-8000-000000000041"
RETENTION_REFERENCE="retention_policy:00000000-0000-4000-8000-000000000051"
UPLOADER="actor:00000000-0000-4000-8000-000000000061"
PERSISTED_BY="actor:00000000-0000-4000-8000-000000000062"
AUDIT_REFERENCE="audit_event:00000000-0000-4000-8000-000000000071"
OUTBOX_REFERENCE="outbox_event:00000000-0000-4000-8000-000000000072"
ARTIFACT_DIGEST="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
SOURCE_DIGEST="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
RETENTION_DIGEST="cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
APPLICATION_DIGEST="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
RECEIVED_AT="2026-08-24T05:55:00Z"
EVIDENCE_RECORDED_AT="2026-08-24T05:58:00Z"

canonical_evidence="$(python3 - <<PY
import json
payload = {
    "artifact_digest": "${ARTIFACT_DIGEST}",
    "artifact_reference": "${ARTIFACT_REFERENCE}",
    "classification_code": "restricted_hr",
    "content_storage_state": "artifact_reference_only",
    "decision_authority_state": "not_authorized_for_employment_decision",
    "document_category_code": "employment_contract",
    "document_record_reference": "${DOCUMENT_REFERENCE}",
    "employment_record_reference": "${EMPLOYMENT_REFERENCE}",
    "person_record_reference": "${PERSON_REFERENCE}",
    "received_at": "${RECEIVED_AT}",
    "recorded_at": "${EVIDENCE_RECORDED_AT}",
    "retention_policy_digest": "${RETENTION_DIGEST}",
    "retention_policy_reference": "${RETENTION_REFERENCE}",
    "schema_version": "orgmetra.document_record_evidence.v1",
    "source_provenance_digest": "${SOURCE_DIGEST}",
    "tenant_record_id": "${TENANT_ID}",
    "uploader_actor_reference": "${UPLOADER}",
}
print(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
PY
)"
EVIDENCE_DIGEST="$(CANONICAL_EVIDENCE="${canonical_evidence}" python3 - <<'PY'
from hashlib import sha256
import os
print(sha256(os.environ["CANONICAL_EVIDENCE"].encode("utf-8")).hexdigest())
PY
)"

with_tenant() {
    local tenant="$1"
    shift
    PGOPTIONS="-c orgmetra.tenant_record_id=${tenant}" command psql "$@"
}

expect_failure() {
    local label="$1"
    local needle="$2"
    local sql="$3"
    local output status
    set +e
    output="$({ with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "${sql}"; } 2>&1)"
    status=$?
    set -e
    if [[ ${status} -eq 0 || "${output}" != *"${needle}"* ]]; then
        echo "${label}: ${output}" >&2
        exit 1
    fi
}

with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('${TENANT_ID}', 'tenant_alpha'), ('${OTHER_TENANT_ID}', 'tenant_beta');
SQL

columns="tenant_record_id, document_record_id, document_record_reference,
person_record_reference, employment_record_reference, uploader_actor_reference,
persisted_by_actor_reference, document_category_code, artifact_reference,
artifact_digest_sha256, source_provenance_digest_sha256,
retention_policy_reference, retention_policy_digest_sha256,
received_at, canonical_evidence_json, evidence_digest_sha256,
audit_event_reference, outbox_event_reference, application_evidence_digest_sha256,
application_purpose_code, application_reason_code"

with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v canonical_evidence="${canonical_evidence}" <<SQL
INSERT INTO document_record (${columns}) VALUES (
    '${TENANT_ID}', '${DOCUMENT_ID}', '${DOCUMENT_REFERENCE}',
    '${PERSON_REFERENCE}', '${EMPLOYMENT_REFERENCE}', '${UPLOADER}', '${PERSISTED_BY}',
    'employment_contract', '${ARTIFACT_REFERENCE}', '${ARTIFACT_DIGEST}',
    '${SOURCE_DIGEST}', '${RETENTION_REFERENCE}', '${RETENTION_DIGEST}',
    TIMESTAMPTZ '${RECEIVED_AT}', :'canonical_evidence', '${EVIDENCE_DIGEST}',
    '${AUDIT_REFERENCE}', '${OUTBOX_REFERENCE}', '${APPLICATION_DIGEST}',
    'document_record_persist', 'reviewed_document_metadata'
);
SQL

persisted="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "
SELECT document_category_code || '|' || classification_code || '|' ||
       content_storage_state || '|' || decision_authority_state
FROM document_record
WHERE document_record_id = '${DOCUMENT_ID}'::uuid;
")"
if [[ "${persisted}" != "employment_contract|restricted_hr|artifact_reference_only|not_authorized_for_employment_decision" ]]; then
    echo "document metadata persisted unsafe or incomplete state: ${persisted}" >&2
    exit 1
fi

expect_failure \
    "document record accepted caller-backdated system time" \
    "transaction timestamp" \
    "INSERT INTO document_record (${columns}, recorded_at) VALUES (
        '${TENANT_ID}', '00000000-0000-7000-8000-000000000032',
        'document_record:00000000-0000-4000-8000-000000000032',
        '${PERSON_REFERENCE}', '${EMPLOYMENT_REFERENCE}', '${UPLOADER}', '${PERSISTED_BY}',
        'policy_acknowledgement',
        'document_artifact:00000000-0000-4000-8000-000000000042',
        '${ARTIFACT_DIGEST}', '${SOURCE_DIGEST}', '${RETENTION_REFERENCE}',
        '${RETENTION_DIGEST}', TIMESTAMPTZ '${RECEIVED_AT}', '{}',
        '${EVIDENCE_DIGEST}',
        'audit_event:00000000-0000-4000-8000-000000000081',
        'outbox_event:00000000-0000-4000-8000-000000000082',
        '${APPLICATION_DIGEST}', 'document_record_persist', 'reviewed_document_metadata',
        TIMESTAMPTZ '2000-01-01 00:00:00+00'
     );"

expect_failure \
    "document record accepted future received_at" \
    "received_at cannot be later" \
    "INSERT INTO document_record (${columns}) VALUES (
        '${TENANT_ID}', '00000000-0000-7000-8000-000000000033',
        'document_record:00000000-0000-4000-8000-000000000033',
        '${PERSON_REFERENCE}', '${EMPLOYMENT_REFERENCE}', '${UPLOADER}', '${PERSISTED_BY}',
        'qualification_document',
        'document_artifact:00000000-0000-4000-8000-000000000043',
        '${ARTIFACT_DIGEST}', '${SOURCE_DIGEST}', '${RETENTION_REFERENCE}',
        '${RETENTION_DIGEST}', pg_catalog.transaction_timestamp() + interval '1 hour', '{}',
        '${EVIDENCE_DIGEST}',
        'audit_event:00000000-0000-4000-8000-000000000083',
        'outbox_event:00000000-0000-4000-8000-000000000084',
        '${APPLICATION_DIGEST}', 'document_record_persist', 'reviewed_document_metadata'
     );"

expect_failure \
    "document record accepted an unreviewed application reason" \
    "application_reason_code" \
    "INSERT INTO document_record (${columns}) VALUES (
        '${TENANT_ID}', '00000000-0000-7000-8000-000000000034',
        'document_record:00000000-0000-4000-8000-000000000034',
        '${PERSON_REFERENCE}', '${EMPLOYMENT_REFERENCE}', '${UPLOADER}', '${PERSISTED_BY}',
        'qualification_document',
        'document_artifact:00000000-0000-4000-8000-000000000044',
        '${ARTIFACT_DIGEST}', '${SOURCE_DIGEST}', '${RETENTION_REFERENCE}',
        '${RETENTION_DIGEST}', TIMESTAMPTZ '${RECEIVED_AT}', '{}',
        '${EVIDENCE_DIGEST}',
        'audit_event:00000000-0000-4000-8000-000000000085',
        'outbox_event:00000000-0000-4000-8000-000000000086',
        '${APPLICATION_DIGEST}', 'document_record_persist', 'unrelated_change'
     );"

expect_failure \
    "document record accepted a non-opaque Person reference" \
    "person_record_reference" \
    "INSERT INTO document_record (${columns}) VALUES (
        '${TENANT_ID}', '00000000-0000-7000-8000-000000000035',
        'document_record:00000000-0000-4000-8000-000000000035',
        'person_record:employee@example.com', '${EMPLOYMENT_REFERENCE}', '${UPLOADER}', '${PERSISTED_BY}',
        'qualification_document',
        'document_artifact:00000000-0000-4000-8000-000000000045',
        '${ARTIFACT_DIGEST}', '${SOURCE_DIGEST}', '${RETENTION_REFERENCE}',
        '${RETENTION_DIGEST}', TIMESTAMPTZ '${RECEIVED_AT}', '{}',
        '${EVIDENCE_DIGEST}',
        'audit_event:00000000-0000-4000-8000-000000000087',
        'outbox_event:00000000-0000-4000-8000-000000000088',
        '${APPLICATION_DIGEST}', 'document_record_persist', 'reviewed_document_metadata'
     );"

mismatch_reference="document_record:00000000-0000-4000-8000-000000000036"
mismatch_artifact="document_artifact:00000000-0000-4000-8000-000000000046"
mismatch_evidence="$(python3 - <<PY
import json
payload = {
    "artifact_digest": "${ARTIFACT_DIGEST}",
    "artifact_reference": "${mismatch_artifact}",
    "classification_code": "restricted_hr",
    "content_storage_state": "artifact_reference_only",
    "decision_authority_state": "not_authorized_for_employment_decision",
    "document_category_code": "employment_contract",
    "document_record_reference": "${mismatch_reference}",
    "employment_record_reference": "${EMPLOYMENT_REFERENCE}",
    "person_record_reference": "${PERSON_REFERENCE}",
    "received_at": "${RECEIVED_AT}",
    "recorded_at": "${EVIDENCE_RECORDED_AT}",
    "retention_policy_digest": "${RETENTION_DIGEST}",
    "retention_policy_reference": "${RETENTION_REFERENCE}",
    "schema_version": "orgmetra.document_record_evidence.v1",
    "source_provenance_digest": "${SOURCE_DIGEST}",
    "tenant_record_id": "${TENANT_ID}",
    "uploader_actor_reference": "${UPLOADER}",
}
print(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
PY
)"
set +e
mismatch_output="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v mismatch_evidence="${mismatch_evidence}" 2>&1 <<SQL
INSERT INTO document_record (${columns}) VALUES (
    '${TENANT_ID}', '00000000-0000-7000-8000-000000000036', '${mismatch_reference}',
    '${PERSON_REFERENCE}', '${EMPLOYMENT_REFERENCE}', '${UPLOADER}', '${PERSISTED_BY}',
    'employment_contract', '${mismatch_artifact}', '${ARTIFACT_DIGEST}', '${SOURCE_DIGEST}',
    '${RETENTION_REFERENCE}', '${RETENTION_DIGEST}', TIMESTAMPTZ '${RECEIVED_AT}',
    :'mismatch_evidence', '${EVIDENCE_DIGEST}',
    'audit_event:00000000-0000-4000-8000-000000000089',
    'outbox_event:00000000-0000-4000-8000-000000000090',
    '${APPLICATION_DIGEST}', 'document_record_persist', 'reviewed_document_metadata'
);
SQL
)"
mismatch_status=$?
set -e
if [[ ${mismatch_status} -eq 0 || "${mismatch_output}" != *"canonical evidence digest"* ]]; then
    echo "document record accepted a digest from a different evidence packet: ${mismatch_output}" >&2
    exit 1
fi

expect_failure \
    "document metadata was rewriteable" \
    "immutable" \
    "UPDATE document_record SET document_category_code = 'qualification_document'
     WHERE document_record_id = '${DOCUMENT_ID}'::uuid;"
expect_failure \
    "document metadata was deletable" \
    "immutable" \
    "DELETE FROM document_record WHERE document_record_id = '${DOCUMENT_ID}'::uuid;"
expect_failure \
    "document metadata could be truncated" \
    "cannot be truncated" \
    "TRUNCATE document_record;"

for forbidden_column in document_bytes document_title free_form_notes compensation_value rating_value credential_value; do
    count="$(psql "${DATABASE_URL}" -Atqc "
        SELECT count(*) FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'document_record'
          AND column_name = '${forbidden_column}';")"
    if [[ "${count}" != "0" ]]; then
        echo "document persistence introduced prohibited value-bearing column: ${forbidden_column}" >&2
        exit 1
    fi
done

foreign_app_fk_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM pg_constraint AS constraint_record
JOIN pg_class AS relation ON relation.oid = constraint_record.conrelid
JOIN pg_class AS target_relation ON target_relation.oid = constraint_record.confrelid
WHERE relation.relname = 'document_record'
  AND constraint_record.contype = 'f'
  AND target_relation.relname IN (
      'person_record', 'employment_record', 'audit_event_record', 'outbox_delivery_record'
  );")"
if [[ "${foreign_app_fk_count}" != "0" ]]; then
    echo "document persistence introduced a direct cross-service application-table dependency" >&2
    exit 1
fi

rls_state="$(psql "${DATABASE_URL}" -Atqc "
SELECT relrowsecurity::text || '|' || relforcerowsecurity::text
FROM pg_class WHERE oid = 'document_record'::regclass;")"
if [[ "${rls_state}" != "true|true" ]]; then
    echo "document-record RLS is not enabled and forced: ${rls_state}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'orgmetra_document_reader') THEN
        CREATE ROLE orgmetra_document_reader LOGIN PASSWORD 'orgmetra_document_reader' NOSUPERUSER NOBYPASSRLS;
    END IF;
END
$$;
GRANT CONNECT ON DATABASE orgmetra TO orgmetra_document_reader;
GRANT USAGE ON SCHEMA public TO orgmetra_document_reader;
GRANT SELECT ON document_record TO orgmetra_document_reader;
SQL

alpha_count="$(PGPASSWORD=orgmetra_document_reader PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
    psql -h localhost -U orgmetra_document_reader -d orgmetra -Atqc 'SELECT count(*) FROM document_record;')"
beta_count="$(PGPASSWORD=orgmetra_document_reader PGOPTIONS="-c orgmetra.tenant_record_id=${OTHER_TENANT_ID}" \
    psql -h localhost -U orgmetra_document_reader -d orgmetra -Atqc 'SELECT count(*) FROM document_record;')"
missing_count="$(PGPASSWORD=orgmetra_document_reader \
    psql -h localhost -U orgmetra_document_reader -d orgmetra -Atqc 'SELECT count(*) FROM document_record;')"
if [[ "${alpha_count}" != "1" || "${beta_count}" != "0" || "${missing_count}" != "0" ]]; then
    echo "document-record RLS isolation failed: alpha=${alpha_count} beta=${beta_count} missing=${missing_count}" >&2
    exit 1
fi

echo "document-record persistence contract passed"
