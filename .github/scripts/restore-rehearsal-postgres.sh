#!/usr/bin/env bash
set -euo pipefail

: "${POSTGRES_SOURCE_ADMIN_URL:=postgresql://orgmetra:orgmetra@localhost:5432/postgres}"
: "${POSTGRES_RESTORE_ADMIN_URL:=postgresql://orgmetra:orgmetra@localhost:5433/postgres}"
: "${POSTGRES_SOURCE_CONTAINER:?POSTGRES_SOURCE_CONTAINER is required}"
: "${POSTGRES_RESTORE_CONTAINER:?POSTGRES_RESTORE_CONTAINER is required}"

if [[ "${POSTGRES_SOURCE_ADMIN_URL}" == "${POSTGRES_RESTORE_ADMIN_URL}" \
   || "${POSTGRES_SOURCE_CONTAINER}" == "${POSTGRES_RESTORE_CONTAINER}" ]]; then
    echo "source and restore PostgreSQL endpoints must differ" >&2
    exit 1
fi

require_disposable_role_cleanup() {
    if [[ "${RECOVERY_REHEARSAL_ALLOW_ROLE_DROP:-}" != "1" ]]; then
        echo "recovery rehearsal role cleanup requires RECOVERY_REHEARSAL_ALLOW_ROLE_DROP=1" >&2
        return 1
    fi
}

replace_database_name() {
    local administrator_url="$1"
    local database_name="$2"
    python3 - "${administrator_url}" "${database_name}" <<'PY'
import sys
from urllib.parse import urlsplit, urlunsplit

administrator_url, database_name = sys.argv[1], sys.argv[2]
parts = urlsplit(administrator_url)
if parts.scheme not in {"postgres", "postgresql"}:
    print("administrator URL must use the postgres or postgresql scheme", file=sys.stderr)
    raise SystemExit(2)
if not parts.netloc:
    print("administrator URL must include a PostgreSQL network location", file=sys.stderr)
    raise SystemExit(2)
if parts.fragment:
    print("administrator URL must not contain a fragment", file=sys.stderr)
    raise SystemExit(2)
print(urlunsplit((parts.scheme, parts.netloc, f"/{database_name}", parts.query, "")))
PY
}

require_disposable_role_cleanup

SOURCE_DATABASE_NAME="orgmetra_recovery_source"
RESTORE_DATABASE_NAME="orgmetra_recovery_target"
SOURCE_DATABASE_URL="$(replace_database_name "${POSTGRES_SOURCE_ADMIN_URL}" "${SOURCE_DATABASE_NAME}")"
RESTORE_DATABASE_URL="$(replace_database_name "${POSTGRES_RESTORE_ADMIN_URL}" "${RESTORE_DATABASE_NAME}")"
DUMP_PATH="$(mktemp -t orgmetra-recovery-XXXXXX.dump)"
TENANT_ID="10000000-0000-7000-8000-000000000001"
PERSON_ID="00000000-0000-7000-8000-000000000101"
NAME_ID="00000000-0000-7000-8000-000000000102"
AUDIT_ID="00000000-0000-7000-8000-000000000103"
OUTBOX_ID="00000000-0000-7000-8000-000000000104"

cluster_system_identifier_from_url() {
    local administrator_url="$1"
    psql "${administrator_url}" -v ON_ERROR_STOP=1 -Atqc \
        "SELECT (pg_control_system()).system_identifier;"
}

cluster_system_identifier_from_container() {
    local container_name="$1"
    docker exec "${container_name}" \
        psql -U orgmetra -d postgres -v ON_ERROR_STOP=1 -Atqc \
        "SELECT (pg_control_system()).system_identifier;"
}

verify_rehearsal_cluster_identity() {
    local source_url_identifier
    local source_container_identifier
    local restore_url_identifier
    local restore_container_identifier

    source_url_identifier="$(cluster_system_identifier_from_url "${POSTGRES_SOURCE_ADMIN_URL}")"
    source_container_identifier="$(cluster_system_identifier_from_container "${POSTGRES_SOURCE_CONTAINER}")"
    restore_url_identifier="$(cluster_system_identifier_from_url "${POSTGRES_RESTORE_ADMIN_URL}")"
    restore_container_identifier="$(cluster_system_identifier_from_container "${POSTGRES_RESTORE_CONTAINER}")"

    if [[ -z "${source_url_identifier}" \
       || "${source_url_identifier}" != "${source_container_identifier}" ]]; then
        echo "source administrator URL does not target POSTGRES_SOURCE_CONTAINER" >&2
        return 1
    fi
    if [[ -z "${restore_url_identifier}" \
       || "${restore_url_identifier}" != "${restore_container_identifier}" ]]; then
        echo "restore administrator URL does not target POSTGRES_RESTORE_CONTAINER" >&2
        return 1
    fi
    if [[ "${source_url_identifier}" == "${restore_url_identifier}" ]]; then
        echo "source and restore PostgreSQL clusters must differ" >&2
        return 1
    fi
}

drop_recovery_roles() {
    local admin_url="$1"
    require_disposable_role_cleanup
    psql "${admin_url}" -v ON_ERROR_STOP=1 <<'SQL' >/dev/null
DROP ROLE IF EXISTS orgmetra_outbox_operator;
DROP ROLE IF EXISTS orgmetra_outbox_recovery_owner;
SQL
}

cleanup() {
    rm -f "${DUMP_PATH}"
    psql "${POSTGRES_RESTORE_ADMIN_URL}" -v ON_ERROR_STOP=1 -c \
        "DROP DATABASE IF EXISTS ${RESTORE_DATABASE_NAME} WITH (FORCE);" >/dev/null || true
    drop_recovery_roles "${POSTGRES_RESTORE_ADMIN_URL}" || true
    psql "${POSTGRES_SOURCE_ADMIN_URL}" -v ON_ERROR_STOP=1 -c \
        "DROP DATABASE IF EXISTS ${SOURCE_DATABASE_NAME} WITH (FORCE);" >/dev/null || true
    drop_recovery_roles "${POSTGRES_SOURCE_ADMIN_URL}" || true
}

# Verify the administrator URLs are bound to the intended disposable service
# containers before installing a cleanup trap or executing any destructive DDL.
verify_rehearsal_cluster_identity
trap cleanup EXIT

psql "${POSTGRES_SOURCE_ADMIN_URL}" -v ON_ERROR_STOP=1 -c \
    "DROP DATABASE IF EXISTS ${SOURCE_DATABASE_NAME} WITH (FORCE);" >/dev/null
drop_recovery_roles "${POSTGRES_SOURCE_ADMIN_URL}"
psql "${POSTGRES_SOURCE_ADMIN_URL}" -v ON_ERROR_STOP=1 -c \
    "CREATE DATABASE ${SOURCE_DATABASE_NAME};" >/dev/null

psql "${POSTGRES_RESTORE_ADMIN_URL}" -v ON_ERROR_STOP=1 -c \
    "DROP DATABASE IF EXISTS ${RESTORE_DATABASE_NAME} WITH (FORCE);" >/dev/null
drop_recovery_roles "${POSTGRES_RESTORE_ADMIN_URL}"

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

docker exec "${POSTGRES_SOURCE_CONTAINER}" \
    pg_dump -U orgmetra -d "${SOURCE_DATABASE_NAME}" --format=custom > "${DUMP_PATH}"
if [[ ! -s "${DUMP_PATH}" ]]; then
    echo "source dump is empty" >&2
    exit 1
fi
docker exec -i "${POSTGRES_SOURCE_CONTAINER}" \
    pg_restore -U orgmetra --list < "${DUMP_PATH}" >/dev/null

# pg_dump is database-scoped and intentionally does not include cluster-global
# roles. A clean replacement cluster must recreate the two least-privilege
# recovery principals before restoring database object ownership and ACLs.
psql "${POSTGRES_RESTORE_ADMIN_URL}" -v ON_ERROR_STOP=1 <<'SQL' >/dev/null
CREATE ROLE orgmetra_outbox_recovery_owner
    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE orgmetra_outbox_operator
    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
SQL
psql "${POSTGRES_RESTORE_ADMIN_URL}" -v ON_ERROR_STOP=1 -c \
    "CREATE DATABASE ${RESTORE_DATABASE_NAME};" >/dev/null
docker exec -i "${POSTGRES_RESTORE_CONTAINER}" \
    pg_restore -U orgmetra --exit-on-error --dbname="${RESTORE_DATABASE_NAME}" \
    < "${DUMP_PATH}" >/dev/null

bitemporal_count="$(PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
    psql "${RESTORE_DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM person_name_record
WHERE tenant_record_id = '${TENANT_ID}'::uuid
  AND person_name_record_id = '${NAME_ID}'::uuid
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
    "TRUNCATE TABLE audit_event_record CASCADE;" 2>&1)"
truncate_status=$?
set -e
if [[ ${truncate_status} -eq 0 ]]; then
    echo "restored audit history was truncatable" >&2
    exit 1
fi
if [[ "${truncate_output}" != *"audit event records are append-only"* ]]; then
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

recovery_acl_count="$(psql "${RESTORE_DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM pg_roles AS owner_role
CROSS JOIN pg_roles AS operator_role
WHERE owner_role.rolname = 'orgmetra_outbox_recovery_owner'
  AND operator_role.rolname = 'orgmetra_outbox_operator'
  AND NOT owner_role.rolcanlogin
  AND NOT owner_role.rolsuper
  AND NOT owner_role.rolcreatedb
  AND NOT owner_role.rolcreaterole
  AND NOT owner_role.rolreplication
  AND NOT owner_role.rolbypassrls
  AND NOT operator_role.rolcanlogin
  AND NOT operator_role.rolsuper
  AND NOT operator_role.rolcreatedb
  AND NOT operator_role.rolcreaterole
  AND NOT operator_role.rolreplication
  AND NOT operator_role.rolbypassrls
  AND has_schema_privilege('orgmetra_outbox_recovery_owner', 'public', 'USAGE')
  AND NOT has_schema_privilege('orgmetra_outbox_recovery_owner', 'public', 'CREATE')
  AND has_schema_privilege('orgmetra_outbox_operator', 'public', 'USAGE')
  AND NOT has_schema_privilege('orgmetra_outbox_operator', 'public', 'CREATE')
  AND has_function_privilege(
        'orgmetra_outbox_operator',
        'public.operator_dead_letter_expired_outbox_delivery(uuid,uuid,uuid,text,text)',
        'EXECUTE'
      )
  AND NOT has_table_privilege('orgmetra_outbox_operator', 'public.outbox_delivery_record', 'SELECT')
  AND NOT has_table_privilege('orgmetra_outbox_operator', 'public.outbox_delivery_record', 'INSERT')
  AND NOT has_table_privilege('orgmetra_outbox_operator', 'public.outbox_delivery_record', 'UPDATE')
  AND NOT has_table_privilege('orgmetra_outbox_operator', 'public.outbox_delivery_record', 'DELETE')
  AND NOT has_table_privilege('orgmetra_outbox_operator', 'public.outbox_delivery_escalation_record', 'SELECT')
  AND NOT has_table_privilege('orgmetra_outbox_operator', 'public.outbox_delivery_escalation_record', 'INSERT')
  AND NOT has_table_privilege('orgmetra_outbox_operator', 'public.outbox_delivery_escalation_record', 'UPDATE')
  AND NOT has_table_privilege('orgmetra_outbox_operator', 'public.outbox_delivery_escalation_record', 'DELETE')
  AND has_table_privilege('orgmetra_outbox_recovery_owner', 'public.outbox_delivery_record', 'SELECT')
  AND NOT has_table_privilege('orgmetra_outbox_recovery_owner', 'public.outbox_delivery_record', 'UPDATE')
  AND NOT has_table_privilege('orgmetra_outbox_recovery_owner', 'public.outbox_delivery_record', 'DELETE')
  AND has_column_privilege(
        'orgmetra_outbox_recovery_owner',
        'public.outbox_delivery_record',
        'delivery_state_code',
        'UPDATE'
      )
  AND has_column_privilege(
        'orgmetra_outbox_recovery_owner',
        'public.outbox_delivery_record',
        'lease_owner_reference',
        'UPDATE'
      )
  AND has_column_privilege(
        'orgmetra_outbox_recovery_owner',
        'public.outbox_delivery_record',
        'lease_expires_at',
        'UPDATE'
      )
  AND has_column_privilege(
        'orgmetra_outbox_recovery_owner',
        'public.outbox_delivery_record',
        'last_failure_code',
        'UPDATE'
      )
  AND NOT EXISTS (
      SELECT 1
      FROM pg_attribute AS attribute
      WHERE attribute.attrelid = 'public.outbox_delivery_record'::regclass
        AND attribute.attnum > 0
        AND NOT attribute.attisdropped
        AND attribute.attname NOT IN (
            'delivery_state_code',
            'lease_owner_reference',
            'lease_expires_at',
            'last_failure_code'
        )
        AND has_column_privilege(
            'orgmetra_outbox_recovery_owner',
            'public.outbox_delivery_record',
            attribute.attname,
            'UPDATE'
        )
  )
  AND has_table_privilege(
        'orgmetra_outbox_recovery_owner',
        'public.outbox_delivery_escalation_record',
        'SELECT'
      )
  AND has_table_privilege(
        'orgmetra_outbox_recovery_owner',
        'public.outbox_delivery_escalation_record',
        'INSERT'
      )
  AND NOT has_table_privilege(
        'orgmetra_outbox_recovery_owner',
        'public.outbox_delivery_escalation_record',
        'UPDATE'
      )
  AND NOT has_table_privilege(
        'orgmetra_outbox_recovery_owner',
        'public.outbox_delivery_escalation_record',
        'DELETE'
      );
")"
if [[ "${recovery_acl_count}" != "1" ]]; then
    echo "least-privilege recovery ACLs did not survive restore" >&2
    exit 1
fi

printf '%s\n' "PostgreSQL restore rehearsal passed for exact restored database ${RESTORE_DATABASE_NAME} on a separate PostgreSQL cluster."
