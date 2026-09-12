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
        echo "required document-record post-commit recovery migration is missing: ${migration}" >&2
        exit 1
    fi
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

TENANT_ID="30000000-0000-7000-8000-000000000003"
DOCUMENT_ID="00000000-0000-7000-8000-000000000231"
DOCUMENT_REFERENCE="document_record:00000000-0000-4000-8000-000000000231"
PERSON_REFERENCE="person_record:00000000-0000-4000-8000-000000000211"
EMPLOYMENT_REFERENCE="employment_record:00000000-0000-4000-8000-000000000221"
UPLOADER="actor:00000000-0000-4000-8000-000000000261"
PERSISTED_BY="actor:00000000-0000-4000-8000-000000000262"
ARTIFACT_REFERENCE="document_artifact:00000000-0000-4000-8000-000000000241"
ARTIFACT_DIGEST="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
SOURCE_DIGEST="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
RETENTION_REFERENCE="retention_policy:00000000-0000-4000-8000-000000000251"
RETENTION_DIGEST="cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
APPLICATION_DIGEST="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
AUDIT_REFERENCE="audit_event:00000000-0000-4000-8000-000000000271"
OUTBOX_REFERENCE="outbox_event:00000000-0000-4000-8000-000000000272"
IDEMPOTENCY_KEY="document-record-persist-00000000-0000-4000-8000-000000000201"
APPLICATION_NAME="orgmetra_document_idempotency_lost_response"

IFS='|' read -r RECEIVED_AT EVIDENCE_RECORDED_AT < <(psql "${DATABASE_URL}" -Atqc "
SELECT
    to_char((pg_catalog.transaction_timestamp() - interval '2 minutes') AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"'),
    to_char((pg_catalog.transaction_timestamp() - interval '1 minute') AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"');
")
export RECEIVED_AT EVIDENCE_RECORDED_AT

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('${TENANT_ID}', 'tenant_postcommit_recovery');
SQL

mapfile -t evidence_parts < <(python3 - "${TENANT_ID}" "${DOCUMENT_REFERENCE}" "${ARTIFACT_REFERENCE}" <<'PY'
import json
import os
import sys
from hashlib import sha256

tenant_id, document_reference, artifact_reference = sys.argv[1:]
payload = {
    "artifact_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
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
    "retention_policy_digest": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "retention_policy_reference": "retention_policy:00000000-0000-4000-8000-000000000251",
    "schema_version": "orgmetra.document_record_evidence.v1",
    "source_provenance_digest": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
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

PERSIST_SQL=$(cat <<SQL
SELECT
    document_record_id::text || '|' || document_record_reference || '|' ||
    audit_event_reference || '|' || outbox_event_reference || '|' ||
    semantic_command_digest_sha256 || '|' || receipt_digest_sha256 || '|' ||
    extract(epoch FROM recorded_at)::text
FROM public.persist_document_record_once(
    '${TENANT_ID}'::uuid,
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
)

RECOVERY_DIR="$(mktemp -d)"
CLIENT_ERROR="${RECOVERY_DIR}/lost-response-client.err"
client_pid=""
backend_pid=""

cleanup() {
    if [[ "${backend_pid}" =~ ^[0-9]+$ ]]; then
        psql "${DATABASE_URL}" -Atq -v ON_ERROR_STOP=1 \
            -c "SELECT pg_catalog.pg_terminate_backend(${backend_pid}) WHERE EXISTS (SELECT 1 FROM pg_catalog.pg_stat_activity WHERE pid = ${backend_pid});" \
            >/dev/null 2>&1 || true
    fi
    if [[ -n "${client_pid}" ]] && kill -0 "${client_pid}" 2>/dev/null; then
        kill "${client_pid}" 2>/dev/null || true
        wait "${client_pid}" 2>/dev/null || true
    fi
    rm -rf "${RECOVERY_DIR}"
}
trap cleanup EXIT

# One simple-query batch commits the authoritative write and then remains inside
# pg_sleep. The supervising recovery actor never receives the function result.
# Terminating the backend only after another session can observe the receipt
# proves that the durable first result exists while the original connection
# ultimately reports failure to its caller.
PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
PGAPPNAME="${APPLICATION_NAME}" \
psql "${DATABASE_URL}" -Atq -v ON_ERROR_STOP=1 \
    -v canonical_evidence="${CANONICAL_EVIDENCE}" \
    -c "BEGIN; ${PERSIST_SQL} COMMIT; SELECT pg_catalog.pg_sleep(30);" \
    >/dev/null 2>"${CLIENT_ERROR}" &
client_pid=$!

first_result_durable=false
recovery_deadline=$((SECONDS + 10))
while (( SECONDS < recovery_deadline )); do
    activity_row="$(psql "${DATABASE_URL}" -Atqc "
SELECT
    activity.pid::text || '|' || activity.state || '|' || COALESCE(activity.wait_event, '') || '|' ||
    (
        SELECT count(*)::text
        FROM public.document_record_persist_receipt AS receipt
        WHERE receipt.tenant_record_id = '${TENANT_ID}'::uuid
          AND receipt.idempotency_key = '${IDEMPOTENCY_KEY}'
    )
FROM pg_catalog.pg_stat_activity AS activity
WHERE activity.application_name = '${APPLICATION_NAME}';
" | head -n 1)"
    observed_pid=""
    observed_state=""
    observed_wait=""
    receipt_count=""
    if [[ -n "${activity_row}" ]]; then
        IFS='|' read -r observed_pid observed_state observed_wait receipt_count <<<"${activity_row}"
    fi
    if [[ "${observed_pid}" =~ ^[0-9]+$ && "${observed_state}" == "active" && "${observed_wait}" == "PgSleep" && "${receipt_count}" == "1" ]]; then
        backend_pid="${observed_pid}"
        first_result_durable=true
        break
    fi
    if ! kill -0 "${client_pid}" 2>/dev/null; then
        break
    fi
    sleep 0.05
done

if [[ "${first_result_durable}" != "true" ]]; then
    echo "post-commit recovery fixture never exposed a durable receipt while the original connection remained live" >&2
    cat "${CLIENT_ERROR}" >&2 || true
    exit 1
fi

terminate_result="$(psql "${DATABASE_URL}" -Atq -v ON_ERROR_STOP=1 \
    -c "SELECT pg_catalog.pg_terminate_backend(${backend_pid});")"
if [[ "${terminate_result}" != "t" ]]; then
    echo "could not terminate the committed original persistence connection: ${terminate_result}" >&2
    exit 1
fi
backend_pid=""

set +e
wait "${client_pid}"
client_status=$?
set -e
client_pid=""
if [[ ${client_status} -eq 0 ]]; then
    echo "original persistence client unexpectedly reported success after forced post-commit connection termination" >&2
    exit 1
fi

DURABLE_RESULT="$(psql "${DATABASE_URL}" -Atq -v ON_ERROR_STOP=1 -c "
SELECT
    persisted.document_record_id::text || '|' || persisted.document_record_reference || '|' ||
    persisted.audit_event_reference || '|' || persisted.outbox_event_reference || '|' ||
    receipt.semantic_command_digest_sha256 || '|' || receipt.receipt_digest_sha256 || '|' ||
    extract(epoch FROM persisted.recorded_at)::text
FROM public.document_record_persist_receipt AS receipt
JOIN public.document_record AS persisted
  ON persisted.tenant_record_id = receipt.tenant_record_id
 AND persisted.document_record_id = receipt.document_record_id
WHERE receipt.tenant_record_id = '${TENANT_ID}'::uuid
  AND receipt.idempotency_key = '${IDEMPOTENCY_KEY}';
")"
if [[ -z "${DURABLE_RESULT}" ]]; then
    echo "forced connection loss erased or hid the committed authoritative result" >&2
    exit 1
fi

RETRY_RESULT="$(PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
    psql "${DATABASE_URL}" -Atq -v ON_ERROR_STOP=1 \
    -v canonical_evidence="${CANONICAL_EVIDENCE}" -c "${PERSIST_SQL}")"
if [[ "${RETRY_RESULT}" != "${DURABLE_RESULT}" ]]; then
    echo "same-command retry did not recover the exact durable result after post-commit connection loss: durable=${DURABLE_RESULT} retry=${RETRY_RESULT}" >&2
    exit 1
fi

recovery_counts="$(psql "${DATABASE_URL}" -Atqc "
SELECT
    (SELECT count(*) FROM public.document_record WHERE tenant_record_id = '${TENANT_ID}'::uuid AND document_record_id = '${DOCUMENT_ID}'::uuid)::text
    || '|' ||
    (SELECT count(*) FROM public.document_record_persist_receipt WHERE tenant_record_id = '${TENANT_ID}'::uuid AND idempotency_key = '${IDEMPOTENCY_KEY}')::text;
")"
if [[ "${recovery_counts}" != "1|1" ]]; then
    echo "post-commit retry duplicated durable document or receipt state: ${recovery_counts}" >&2
    exit 1
fi

active_recovery_connections="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM pg_catalog.pg_stat_activity
WHERE application_name = '${APPLICATION_NAME}';
")"
if [[ "${active_recovery_connections}" != "0" ]]; then
    echo "post-commit recovery acceptance leaked PostgreSQL connections: ${active_recovery_connections}" >&2
    exit 1
fi
