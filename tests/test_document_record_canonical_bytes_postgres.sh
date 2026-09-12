#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

for migration in \
    database/migrations/0001_foundation_schema.sql \
    database/migrations/0002_sealed_evidence_digest.sql \
    database/migrations/0021_document_record_persistence.sql \
    database/migrations/0022_document_record_evidence_unique_keys.sql \
    database/migrations/0023_document_record_canonical_encoding.sql; do
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

TENANT_ID="10000000-0000-7000-8000-000000000201"
DOCUMENT_ID="00000000-0000-7000-8000-000000000231"
DOCUMENT_REFERENCE="document_record:00000000-0000-4000-8000-000000000231"
PERSON_REFERENCE="person_record:00000000-0000-4000-8000-000000000211"
EMPLOYMENT_REFERENCE="employment_record:00000000-0000-4000-8000-000000000221"
ARTIFACT_REFERENCE="document_artifact:00000000-0000-4000-8000-000000000241"
RETENTION_REFERENCE="retention_policy:00000000-0000-4000-8000-000000000251"
UPLOADER="actor:00000000-0000-4000-8000-000000000261"
PERSISTED_BY="actor:00000000-0000-4000-8000-000000000262"
AUDIT_REFERENCE="audit_event:00000000-0000-4000-8000-000000000271"
OUTBOX_REFERENCE="outbox_event:00000000-0000-4000-8000-000000000272"
ARTIFACT_DIGEST="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
SOURCE_DIGEST="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
RETENTION_DIGEST="cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
APPLICATION_DIGEST="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
IFS='|' read -r RECEIVED_AT EVIDENCE_RECORDED_AT < <(psql "${DATABASE_URL}" -Atqc "
SELECT
    to_char(
        (date_trunc('second', pg_catalog.transaction_timestamp() - interval '2 minutes')
            + interval '123456 microseconds') AT TIME ZONE 'UTC',
        'YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"'
    ),
    to_char(
        (date_trunc('second', pg_catalog.transaction_timestamp() - interval '1 minute')
            + interval '654321 microseconds') AT TIME ZONE 'UTC',
        'YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"'
    );
")

noncanonical_evidence="$(python3 - <<PY
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
# Semantically identical and unique-key JSON, but not the package's deterministic
# compact canonical encoding because insignificant separator whitespace is kept.
print(json.dumps(payload, sort_keys=True, ensure_ascii=True))
PY
)"
EVIDENCE_DIGEST="$(CANONICAL_EVIDENCE="${noncanonical_evidence}" python3 - <<'PY'
from hashlib import sha256
import os
print(sha256(os.environ["CANONICAL_EVIDENCE"].encode("utf-8")).hexdigest())
PY
)"

PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('${TENANT_ID}', 'tenant_canonical_bytes_regression');
SQL

set +e
output="$(PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v canonical_evidence="${noncanonical_evidence}" 2>&1 <<SQL
INSERT INTO document_record (
    tenant_record_id, document_record_id, document_record_reference,
    person_record_reference, employment_record_reference, uploader_actor_reference,
    persisted_by_actor_reference, document_category_code, artifact_reference,
    artifact_digest_sha256, source_provenance_digest_sha256,
    retention_policy_reference, retention_policy_digest_sha256,
    received_at, canonical_evidence_json, evidence_digest_sha256,
    audit_event_reference, outbox_event_reference, application_evidence_digest_sha256,
    application_purpose_code, application_reason_code
) VALUES (
    '${TENANT_ID}', '${DOCUMENT_ID}', '${DOCUMENT_REFERENCE}',
    '${PERSON_REFERENCE}', '${EMPLOYMENT_REFERENCE}', '${UPLOADER}', '${PERSISTED_BY}',
    'employment_contract', '${ARTIFACT_REFERENCE}', '${ARTIFACT_DIGEST}', '${SOURCE_DIGEST}',
    '${RETENTION_REFERENCE}', '${RETENTION_DIGEST}', TIMESTAMPTZ '${RECEIVED_AT}',
    :'canonical_evidence', '${EVIDENCE_DIGEST}', '${AUDIT_REFERENCE}', '${OUTBOX_REFERENCE}',
    '${APPLICATION_DIGEST}', 'document_record_persist', 'reviewed_document_metadata'
);
SQL
)"
status=$?
set -e

if [[ ${status} -eq 0 || "${output}" != *"deterministic v1 encoding"* ]]; then
    echo "document-record persistence accepted recomputed-digest noncanonical JSON bytes: ${output}" >&2
    exit 1
fi

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
CANONICAL_DIGEST="$(CANONICAL_EVIDENCE="${canonical_evidence}" python3 - <<'PY'
from hashlib import sha256
import os
print(sha256(os.environ["CANONICAL_EVIDENCE"].encode("utf-8")).hexdigest())
PY
)"

PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 \
    -v canonical_evidence="${canonical_evidence}" <<SQL
INSERT INTO document_record (
    tenant_record_id, document_record_id, document_record_reference,
    person_record_reference, employment_record_reference, uploader_actor_reference,
    persisted_by_actor_reference, document_category_code, artifact_reference,
    artifact_digest_sha256, source_provenance_digest_sha256,
    retention_policy_reference, retention_policy_digest_sha256,
    received_at, canonical_evidence_json, evidence_digest_sha256,
    audit_event_reference, outbox_event_reference, application_evidence_digest_sha256,
    application_purpose_code, application_reason_code
) VALUES (
    '${TENANT_ID}', '${DOCUMENT_ID}', '${DOCUMENT_REFERENCE}',
    '${PERSON_REFERENCE}', '${EMPLOYMENT_REFERENCE}', '${UPLOADER}', '${PERSISTED_BY}',
    'employment_contract', '${ARTIFACT_REFERENCE}', '${ARTIFACT_DIGEST}', '${SOURCE_DIGEST}',
    '${RETENTION_REFERENCE}', '${RETENTION_DIGEST}', TIMESTAMPTZ '${RECEIVED_AT}',
    :'canonical_evidence', '${CANONICAL_DIGEST}', '${AUDIT_REFERENCE}', '${OUTBOX_REFERENCE}',
    '${APPLICATION_DIGEST}', 'document_record_persist', 'reviewed_document_metadata'
);
SQL

persisted_count="$(PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM document_record
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND document_record_id = '${DOCUMENT_ID}'::uuid
  AND canonical_evidence_json = \$canonical\$${canonical_evidence}\$canonical\$
  AND evidence_digest_sha256 = '${CANONICAL_DIGEST}';
")"
if [[ "${persisted_count}" != "1" ]]; then
    echo "document-record persistence did not accept exactly one canonical v1 evidence row: ${persisted_count}" >&2
    exit 1
fi

echo "document-record deterministic canonical-byte contract passed"
