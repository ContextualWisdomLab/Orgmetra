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
        echo "required document-record idempotency migration is missing: ${migration}" >&2
        exit 1
    fi
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

TENANT_ID="10000000-0000-7000-8000-000000000001"
OTHER_TENANT_ID="20000000-0000-7000-8000-000000000002"
PERSON_REFERENCE="person_record:00000000-0000-4000-8000-000000000011"
EMPLOYMENT_REFERENCE="employment_record:00000000-0000-4000-8000-000000000021"
UPLOADER="actor:00000000-0000-4000-8000-000000000061"
PERSISTED_BY="actor:00000000-0000-4000-8000-000000000062"
RETENTION_REFERENCE="retention_policy:00000000-0000-4000-8000-000000000051"
ARTIFACT_DIGEST="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
SOURCE_DIGEST="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
RETENTION_DIGEST="cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
APPLICATION_DIGEST="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
CONFLICTING_APPLICATION_DIGEST="ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
IDEMPOTENCY_KEY="document-record-persist-00000000-0000-4000-8000-000000000101"
CONCURRENT_KEY="document-record-persist-00000000-0000-4000-8000-000000000102"

IFS='|' read -r RECEIVED_AT EVIDENCE_RECORDED_AT < <(psql "${DATABASE_URL}" -Atqc "
SELECT
    to_char((pg_catalog.transaction_timestamp() - interval '2 minutes') AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"'),
    to_char((pg_catalog.transaction_timestamp() - interval '1 minute') AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"');
")

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('${TENANT_ID}', 'tenant_alpha'), ('${OTHER_TENANT_ID}', 'tenant_beta');
SQL

with_tenant() {
    local tenant="$1"
    shift
    PGOPTIONS="-c orgmetra.tenant_record_id=${tenant} ${PGOPTIONS:-}" command psql "$@"
}

build_evidence() {
    local document_reference="$1"
    local artifact_reference="$2"
    python3 - "$TENANT_ID" "$document_reference" "$artifact_reference" <<'PY'
import json
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
    "employment_record_reference": "employment_record:00000000-0000-4000-8000-000000000021",
    "person_record_reference": "person_record:00000000-0000-4000-8000-000000000011",
    "received_at": __import__("os").environ["RECEIVED_AT"],
    "recorded_at": __import__("os").environ["EVIDENCE_RECORDED_AT"],
    "retention_policy_digest": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "retention_policy_reference": "retention_policy:00000000-0000-4000-8000-000000000051",
    "schema_version": "orgmetra.document_record_evidence.v1",
    "source_provenance_digest": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "tenant_record_id": tenant_id,
    "uploader_actor_reference": "actor:00000000-0000-4000-8000-000000000061",
}
canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
print(canonical)
print(sha256(canonical.encode("utf-8")).hexdigest())
PY
}
export RECEIVED_AT EVIDENCE_RECORDED_AT

persist_sql() {
    local key="$1"
    local document_id="$2"
    local document_reference="$3"
    local artifact_reference="$4"
    local audit_reference="$5"
    local outbox_reference="$6"
    local application_digest="$7"
    local canonical_evidence="$8"
    local evidence_digest="$9"
    cat <<SQL
SELECT
    document_record_id::text || '|' || document_record_reference || '|' ||
    audit_event_reference || '|' || outbox_event_reference || '|' ||
    semantic_command_digest_sha256 || '|' || receipt_digest_sha256
FROM public.persist_document_record_once(
    '${TENANT_ID}'::uuid,
    '${key}',
    '${document_id}'::uuid,
    '${document_reference}',
    '${PERSON_REFERENCE}',
    '${EMPLOYMENT_REFERENCE}',
    '${UPLOADER}',
    '${PERSISTED_BY}',
    'employment_contract',
    '${artifact_reference}',
    '${ARTIFACT_DIGEST}',
    '${SOURCE_DIGEST}',
    '${RETENTION_REFERENCE}',
    '${RETENTION_DIGEST}',
    TIMESTAMPTZ '${RECEIVED_AT}',
    :'canonical_evidence',
    '${evidence_digest}',
    '${audit_reference}',
    '${outbox_reference}',
    '${application_digest}'
);
SQL
}

DOCUMENT_ID="00000000-0000-7000-8000-000000000131"
DOCUMENT_REFERENCE="document_record:00000000-0000-4000-8000-000000000131"
ARTIFACT_REFERENCE="document_artifact:00000000-0000-4000-8000-000000000141"
AUDIT_REFERENCE="audit_event:00000000-0000-4000-8000-000000000171"
OUTBOX_REFERENCE="outbox_event:00000000-0000-4000-8000-000000000172"
mapfile -t evidence_parts < <(build_evidence "${DOCUMENT_REFERENCE}" "${ARTIFACT_REFERENCE}")
CANONICAL_EVIDENCE="${evidence_parts[0]}"
EVIDENCE_DIGEST="${evidence_parts[1]}"
SQL_TEXT="$(persist_sql "${IDEMPOTENCY_KEY}" "${DOCUMENT_ID}" "${DOCUMENT_REFERENCE}" "${ARTIFACT_REFERENCE}" "${AUDIT_REFERENCE}" "${OUTBOX_REFERENCE}" "${APPLICATION_DIGEST}" "${CANONICAL_EVIDENCE}" "${EVIDENCE_DIGEST}")"

first_result="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atq -v ON_ERROR_STOP=1 -v canonical_evidence="${CANONICAL_EVIDENCE}" -c "SET TIME ZONE 'UTC'; ${SQL_TEXT}")"
retry_result="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atq -v ON_ERROR_STOP=1 -v canonical_evidence="${CANONICAL_EVIDENCE}" -c "SET TIME ZONE 'Asia/Seoul'; ${SQL_TEXT}")"
if [[ "${first_result}" != "${retry_result}" ]]; then
    echo "same semantic retry changed across session time zones instead of returning the original receipt" >&2
    exit 1
fi

counts="$(psql "${DATABASE_URL}" -Atqc "
SELECT
    (SELECT count(*) FROM document_record WHERE tenant_record_id = '${TENANT_ID}'::uuid AND document_record_id = '${DOCUMENT_ID}'::uuid)::text
    || '|' ||
    (SELECT count(*) FROM document_record_persist_receipt WHERE tenant_record_id = '${TENANT_ID}'::uuid AND idempotency_key = '${IDEMPOTENCY_KEY}')::text;
")"
if [[ "${counts}" != "1|1" ]]; then
    echo "same semantic retry duplicated durable document or receipt state: ${counts}" >&2
    exit 1
fi

set +e
conflict_output="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atq -v ON_ERROR_STOP=1 -v canonical_evidence="${CANONICAL_EVIDENCE}" \
    -c "$(persist_sql "${IDEMPOTENCY_KEY}" "${DOCUMENT_ID}" "${DOCUMENT_REFERENCE}" "${ARTIFACT_REFERENCE}" "${AUDIT_REFERENCE}" "${OUTBOX_REFERENCE}" "${CONFLICTING_APPLICATION_DIGEST}" "${CANONICAL_EVIDENCE}" "${EVIDENCE_DIGEST}")" 2>&1)"
conflict_status=$?
set -e
if [[ ${conflict_status} -eq 0 || "${conflict_output}" != *"idempotency key is bound to a different document persistence command"* ]]; then
    echo "same idempotency key accepted a different semantic command: ${conflict_output}" >&2
    exit 1
fi

CONCURRENT_DOCUMENT_ID="00000000-0000-7000-8000-000000000132"
CONCURRENT_DOCUMENT_REFERENCE="document_record:00000000-0000-4000-8000-000000000132"
CONCURRENT_ARTIFACT_REFERENCE="document_artifact:00000000-0000-4000-8000-000000000142"
CONCURRENT_AUDIT_REFERENCE="audit_event:00000000-0000-4000-8000-000000000173"
CONCURRENT_OUTBOX_REFERENCE="outbox_event:00000000-0000-4000-8000-000000000174"
mapfile -t concurrent_evidence_parts < <(build_evidence "${CONCURRENT_DOCUMENT_REFERENCE}" "${CONCURRENT_ARTIFACT_REFERENCE}")
CONCURRENT_EVIDENCE="${concurrent_evidence_parts[0]}"
CONCURRENT_EVIDENCE_DIGEST="${concurrent_evidence_parts[1]}"
CONCURRENT_SQL="$(persist_sql "${CONCURRENT_KEY}" "${CONCURRENT_DOCUMENT_ID}" "${CONCURRENT_DOCUMENT_REFERENCE}" "${CONCURRENT_ARTIFACT_REFERENCE}" "${CONCURRENT_AUDIT_REFERENCE}" "${CONCURRENT_OUTBOX_REFERENCE}" "${APPLICATION_DIGEST}" "${CONCURRENT_EVIDENCE}" "${CONCURRENT_EVIDENCE_DIGEST}")"
FIRST_INPUT="$(mktemp -u)"
FIRST_OUTPUT="$(mktemp)"
SECOND_OUTPUT="$(mktemp)"
mkfifo "${FIRST_INPUT}"
first_client_pid=""
second_client_pid=""
cleanup() {
    exec 3>&- 2>/dev/null || true
    if [[ -n "${second_client_pid}" ]] && kill -0 "${second_client_pid}" 2>/dev/null; then
        kill "${second_client_pid}" 2>/dev/null || true
    fi
    if [[ -n "${first_client_pid}" ]] && kill -0 "${first_client_pid}" 2>/dev/null; then
        kill "${first_client_pid}" 2>/dev/null || true
    fi
    rm -f "${FIRST_INPUT}" "${FIRST_OUTPUT}" "${SECOND_OUTPUT}"
}
trap cleanup EXIT

PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID} ${PGOPTIONS:-}" \
PGAPPNAME=orgmetra_document_idempotency_first \
psql "${DATABASE_URL}" -Atq -v ON_ERROR_STOP=1 \
    -v canonical_evidence="${CONCURRENT_EVIDENCE}" <"${FIRST_INPUT}" >"${FIRST_OUTPUT}" 2>&1 &
first_client_pid=$!
exec 3>"${FIRST_INPUT}"
printf 'BEGIN;\nSELECT '\''FIRST_BACKEND|''' || pg_backend_pid()::text;\n%s\nSELECT '\''FIRST_LOCK_HELD''';\n' "${CONCURRENT_SQL}" >&3

first_ready=false
first_deadline=$((SECONDS + 10))
while (( SECONDS < first_deadline )); do
    if grep -q '^FIRST_LOCK_HELD$' "${FIRST_OUTPUT}"; then
        first_ready=true
        break
    fi
    if ! kill -0 "${first_client_pid}" 2>/dev/null; then
        break
    fi
    sleep 0.05
done
if [[ "${first_ready}" != "true" ]]; then
    echo "first concurrent session did not reach the held transaction boundary" >&2
    cat "${FIRST_OUTPUT}" >&2
    exit 1
fi
FIRST_BACKEND_PID="$(sed -n 's/^FIRST_BACKEND|//p' "${FIRST_OUTPUT}" | head -n 1)"
if [[ ! "${FIRST_BACKEND_PID}" =~ ^[0-9]+$ ]]; then
    echo "could not capture first PostgreSQL backend pid: ${FIRST_BACKEND_PID}" >&2
    exit 1
fi

PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID} ${PGOPTIONS:-}" \
PGAPPNAME=orgmetra_document_idempotency_second \
psql "${DATABASE_URL}" -Atq -v ON_ERROR_STOP=1 \
    -v canonical_evidence="${CONCURRENT_EVIDENCE}" -c "${CONCURRENT_SQL}" >"${SECOND_OUTPUT}" 2>&1 &
second_client_pid=$!

advisory_wait_observed=false
second_deadline=$((SECONDS + 10))
while (( SECONDS < second_deadline )); do
    advisory_wait_count="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*)
FROM pg_catalog.pg_stat_activity AS activity
JOIN pg_catalog.pg_locks AS lock_state
  ON lock_state.pid = activity.pid
WHERE activity.application_name = 'orgmetra_document_idempotency_second'
  AND lock_state.locktype = 'advisory'
  AND NOT lock_state.granted
  AND ${FIRST_BACKEND_PID} = ANY(pg_catalog.pg_blocking_pids(activity.pid));
")"
    if [[ "${advisory_wait_count}" == "1" ]]; then
        advisory_wait_observed=true
        break
    fi
    if ! kill -0 "${second_client_pid}" 2>/dev/null; then
        break
    fi
    sleep 0.05
done
if [[ "${advisory_wait_observed}" != "true" ]]; then
    echo "second concurrent session did not demonstrably wait on the first session's advisory lock" >&2
    cat "${SECOND_OUTPUT}" >&2
    exit 1
fi

printf 'COMMIT;\n\\q\n' >&3
exec 3>&-
wait "${first_client_pid}"
first_client_pid=""
wait "${second_client_pid}"
second_client_pid=""
first_concurrent_result="$(grep -F 'document_record:' "${FIRST_OUTPUT}" | head -n 1)"
second_concurrent_result="$(grep -F 'document_record:' "${SECOND_OUTPUT}" | head -n 1)"
if [[ -z "${first_concurrent_result}" || "${first_concurrent_result}" != "${second_concurrent_result}" ]]; then
    echo "concurrent same-semantic attempts did not converge: first=${first_concurrent_result} second=${second_concurrent_result}" >&2
    exit 1
fi

concurrent_counts="$(psql "${DATABASE_URL}" -Atqc "
SELECT
    (SELECT count(*) FROM document_record WHERE tenant_record_id = '${TENANT_ID}'::uuid AND document_record_id = '${CONCURRENT_DOCUMENT_ID}'::uuid)::text
    || '|' ||
    (SELECT count(*) FROM document_record_persist_receipt WHERE tenant_record_id = '${TENANT_ID}'::uuid AND idempotency_key = '${CONCURRENT_KEY}')::text;
")"
if [[ "${concurrent_counts}" != "1|1" ]]; then
    echo "concurrent retry duplicated durable state: ${concurrent_counts}" >&2
    exit 1
fi

active_test_connections="$(psql "${DATABASE_URL}" -Atqc "
SELECT count(*) FROM pg_stat_activity
WHERE application_name IN ('orgmetra_document_idempotency_first', 'orgmetra_document_idempotency_second');
")"
if [[ "${active_test_connections}" != "0" ]]; then
    echo "idempotency acceptance leaked PostgreSQL connections: ${active_test_connections}" >&2
    exit 1
fi

rls_state="$(psql "${DATABASE_URL}" -Atqc "
SELECT relrowsecurity::text || '|' || relforcerowsecurity::text
FROM pg_class WHERE oid = 'document_record_persist_receipt'::regclass;
")"
if [[ "${rls_state}" != "true|true" ]]; then
    echo "document-record idempotency receipt is not FORCE-RLS protected: ${rls_state}" >&2
    exit 1
fi

PROBE_ROLE="orgmetra_document_receipt_probe"
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
CREATE ROLE ${PROBE_ROLE}
    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT USAGE ON SCHEMA public TO ${PROBE_ROLE};
GRANT SELECT, UPDATE ON TABLE public.document_record_persist_receipt TO ${PROBE_ROLE};
SQL

same_tenant_receipts="$(psql "${DATABASE_URL}" -Atq -v ON_ERROR_STOP=1 <<SQL
SET ROLE ${PROBE_ROLE};
SET orgmetra.tenant_record_id = '${TENANT_ID}';
SELECT count(*) FROM public.document_record_persist_receipt;
SQL
)"
if [[ "${same_tenant_receipts}" != "2" ]]; then
    echo "NOBYPASSRLS receipt probe could not read its own tenant rows: ${same_tenant_receipts}" >&2
    exit 1
fi

other_tenant_receipts="$(psql "${DATABASE_URL}" -Atq -v ON_ERROR_STOP=1 <<SQL
SET ROLE ${PROBE_ROLE};
SET orgmetra.tenant_record_id = '${OTHER_TENANT_ID}';
SELECT count(*) FROM public.document_record_persist_receipt;
SQL
)"
if [[ "${other_tenant_receipts}" != "0" ]]; then
    echo "NOBYPASSRLS receipt probe could read another tenant's rows: ${other_tenant_receipts}" >&2
    exit 1
fi

cross_tenant_update="$(psql "${DATABASE_URL}" -Atq -v ON_ERROR_STOP=1 <<SQL
SET ROLE ${PROBE_ROLE};
SET orgmetra.tenant_record_id = '${OTHER_TENANT_ID}';
UPDATE public.document_record_persist_receipt
SET semantic_command_digest_sha256 = '${CONFLICTING_APPLICATION_DIGEST}'
WHERE tenant_record_id = '${TENANT_ID}'::uuid
RETURNING 1;
SQL
)"
if [[ -n "${cross_tenant_update}" ]]; then
    echo "NOBYPASSRLS receipt probe could update another tenant's row: ${cross_tenant_update}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
DROP OWNED BY ${PROBE_ROLE};
DROP ROLE ${PROBE_ROLE};
SQL

set +e
mutation_output="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
UPDATE document_record_persist_receipt
SET semantic_command_digest_sha256 = '${CONFLICTING_APPLICATION_DIGEST}'
WHERE tenant_record_id = '${TENANT_ID}'::uuid AND idempotency_key = '${IDEMPOTENCY_KEY}';" 2>&1)"
mutation_status=$?
set -e
if [[ ${mutation_status} -eq 0 || "${mutation_output}" != *"append-only"* ]]; then
    echo "document-record idempotency receipt was mutable: ${mutation_output}" >&2
    exit 1
fi
