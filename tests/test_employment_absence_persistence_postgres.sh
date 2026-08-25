#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

for migration in \
  database/migrations/0001_foundation_schema.sql \
  database/migrations/0002_sealed_evidence_digest.sql \
  database/migrations/0026_employment_absence_persistence.sql; do
  if [[ ! -f "${migration}" ]]; then
    echo "required employment-absence persistence migration is missing: ${migration}" >&2
    exit 1
  fi
  psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done

TENANT_ID="10000000-0000-7000-8000-000000000001"
OTHER_TENANT_ID="20000000-0000-7000-8000-000000000002"
PERSON_ID="10000000-0000-7000-8000-000000000011"
EMPLOYMENT_ID="10000000-0000-7000-8000-000000000021"
EMPLOYMENT_VERSION_ID="10000000-0000-7000-8000-000000000022"
ABSENCE_ID="10000000-0000-7000-8000-000000000031"
ABSENCE_VERSION_ID="10000000-0000-7000-8000-000000000032"
OTHER_ABSENCE_ID="10000000-0000-7000-8000-000000000041"
OTHER_ABSENCE_VERSION_ID="10000000-0000-7000-8000-000000000042"
ACTOR="actor:00000000-0000-4000-8000-000000000051"
AUDIT="audit_event:00000000-0000-4000-8000-000000000061"
OUTBOX="outbox_event:00000000-0000-4000-8000-000000000062"
SOURCE_DIGEST="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
APPLICATION_DIGEST="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

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
INSERT INTO person_record (tenant_record_id, person_record_id)
VALUES ('${TENANT_ID}', '${PERSON_ID}');
INSERT INTO employment_record (tenant_record_id, employment_record_id, person_record_id)
VALUES ('${TENANT_ID}', '${EMPLOYMENT_ID}', '${PERSON_ID}');
INSERT INTO employment_record_version (
  tenant_record_id, employment_record_version_id, employment_record_id,
  employment_status_code, effective_from, effective_to
) VALUES (
  '${TENANT_ID}', '${EMPLOYMENT_VERSION_ID}', '${EMPLOYMENT_ID}',
  'active', DATE '2026-01-01', DATE '2027-01-01'
);

INSERT INTO employment_absence_record (
  tenant_record_id, employment_absence_record_id, employment_record_id,
  person_record_id, created_by_actor_reference
) VALUES (
  '${TENANT_ID}', '${ABSENCE_ID}', '${EMPLOYMENT_ID}', '${PERSON_ID}', '${ACTOR}'
);

INSERT INTO employment_absence_version (
  tenant_record_id, employment_absence_version_id, employment_absence_record_id,
  absence_status_code, effective_from, effective_to, source_evidence_digest_sha256,
  audit_event_reference, outbox_event_reference, application_evidence_digest_sha256
) VALUES (
  '${TENANT_ID}', '${ABSENCE_VERSION_ID}', '${ABSENCE_ID}',
  'confirmed', DATE '2026-08-25', DATE '2026-08-27', '${SOURCE_DIGEST}',
  '${AUDIT}', '${OUTBOX}', '${APPLICATION_DIGEST}'
);
SQL

persisted="$(with_tenant "${TENANT_ID}" "${DATABASE_URL}" -Atqc "
SELECT absence_status_code || '|' || application_purpose_code || '|' ||
       application_reason_code || '|' || decision_authority_state
FROM employment_absence_version
WHERE employment_absence_version_id='${ABSENCE_VERSION_ID}'::uuid;
")"
if [[ "${persisted}" != "confirmed|employment_absence_record|operational_absence_fact|not_authorized_for_employment_decision" ]]; then
  echo "employment absence persisted unsafe or incomplete state: ${persisted}" >&2
  exit 1
fi

expect_failure \
  "absence version accepted caller-backdated system time" \
  "recorded_from must equal" \
  "INSERT INTO employment_absence_version (
     tenant_record_id, employment_absence_version_id, employment_absence_record_id,
     absence_status_code, effective_from, effective_to, source_evidence_digest_sha256,
     audit_event_reference, outbox_event_reference, application_evidence_digest_sha256,
     recorded_from
   ) VALUES (
     '${TENANT_ID}', '10000000-0000-7000-8000-000000000033', '${ABSENCE_ID}',
     'cancelled', DATE '2026-08-25', DATE '2026-08-27', '${SOURCE_DIGEST}',
     'audit_event:00000000-0000-4000-8000-000000000063',
     'outbox_event:00000000-0000-4000-8000-000000000064', '${APPLICATION_DIGEST}',
     TIMESTAMPTZ '2000-01-01 00:00:00+00'
   );"

with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO employment_absence_record (
  tenant_record_id, employment_absence_record_id, employment_record_id,
  person_record_id, created_by_actor_reference
) VALUES (
  '${TENANT_ID}', '${OTHER_ABSENCE_ID}', '${EMPLOYMENT_ID}', '${PERSON_ID}', '${ACTOR}'
);
SQL

expect_failure \
  "concurrent confirmed absence was accepted" \
  "confirmed absence already exists" \
  "INSERT INTO employment_absence_version (
     tenant_record_id, employment_absence_version_id, employment_absence_record_id,
     absence_status_code, effective_from, effective_to, source_evidence_digest_sha256,
     audit_event_reference, outbox_event_reference, application_evidence_digest_sha256
   ) VALUES (
     '${TENANT_ID}', '${OTHER_ABSENCE_VERSION_ID}', '${OTHER_ABSENCE_ID}',
     'confirmed', DATE '2026-08-26', DATE '2026-08-28', '${SOURCE_DIGEST}',
     'audit_event:00000000-0000-4000-8000-000000000065',
     'outbox_event:00000000-0000-4000-8000-000000000066', '${APPLICATION_DIGEST}'
   );"

expect_failure \
  "absence version accepted a non-staffable Employment interval" \
  "active or leave Employment coverage" \
  "INSERT INTO employment_absence_version (
     tenant_record_id, employment_absence_version_id, employment_absence_record_id,
     absence_status_code, effective_from, effective_to, source_evidence_digest_sha256,
     audit_event_reference, outbox_event_reference, application_evidence_digest_sha256
   ) VALUES (
     '${TENANT_ID}', '10000000-0000-7000-8000-000000000043', '${OTHER_ABSENCE_ID}',
     'cancelled', DATE '2027-02-01', DATE '2027-02-02', '${SOURCE_DIGEST}',
     'audit_event:00000000-0000-4000-8000-000000000067',
     'outbox_event:00000000-0000-4000-8000-000000000068', '${APPLICATION_DIGEST}'
   );"

expect_failure \
  "absence evidence was rewriteable" \
  "immutable" \
  "UPDATE employment_absence_version SET source_evidence_digest_sha256 =
   'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc'
   WHERE employment_absence_version_id='${ABSENCE_VERSION_ID}'::uuid;"

with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
UPDATE employment_absence_version
SET recorded_to = pg_catalog.transaction_timestamp()
WHERE employment_absence_version_id='${ABSENCE_VERSION_ID}'::uuid;"

with_tenant "${TENANT_ID}" "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "
INSERT INTO employment_absence_version (
  tenant_record_id, employment_absence_version_id, employment_absence_record_id,
  absence_status_code, effective_from, effective_to, source_evidence_digest_sha256,
  audit_event_reference, outbox_event_reference, application_evidence_digest_sha256
) VALUES (
  '${TENANT_ID}', '10000000-0000-7000-8000-000000000034', '${ABSENCE_ID}',
  'cancelled', DATE '2026-08-25', DATE '2026-08-27', '${SOURCE_DIGEST}',
  'audit_event:00000000-0000-4000-8000-000000000069',
  'outbox_event:00000000-0000-4000-8000-000000000070', '${APPLICATION_DIGEST}'
);"

expect_failure \
  "absence history was deletable" \
  "immutable" \
  "DELETE FROM employment_absence_version WHERE employment_absence_record_id='${ABSENCE_ID}'::uuid;"
expect_failure \
  "absence history could be truncated" \
  "cannot be truncated" \
  "TRUNCATE employment_absence_version;"

for forbidden_column in reason_text medical_detail family_detail statutory_detail free_form_note compensation_value rating_value; do
  count="$(psql "${DATABASE_URL}" -Atqc "
    SELECT count(*) FROM information_schema.columns
    WHERE table_schema='public'
      AND table_name IN ('employment_absence_record','employment_absence_version')
      AND column_name='${forbidden_column}';")"
  if [[ "${count}" != "0" ]]; then
    echo "absence persistence introduced prohibited sensitive column: ${forbidden_column}" >&2
    exit 1
  fi
done

rls_state="$(psql "${DATABASE_URL}" -Atqc "
SELECT string_agg(relname || ':' || relrowsecurity::text || ':' || relforcerowsecurity::text, ',' ORDER BY relname)
FROM pg_class
WHERE relname IN ('employment_absence_record','employment_absence_version');")"
if [[ "${rls_state}" != "employment_absence_record:true:true,employment_absence_version:true:true" ]]; then
  echo "employment absence RLS is not enabled and forced: ${rls_state}" >&2
  exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='absence_reader') THEN
    CREATE ROLE absence_reader NOSUPERUSER NOBYPASSRLS;
  END IF;
END $$;
GRANT SELECT ON employment_absence_record, employment_absence_version TO absence_reader;
SQL

visible="$(psql "${DATABASE_URL}" -Atqc "
BEGIN;
SET LOCAL ROLE absence_reader;
SET LOCAL orgmetra.tenant_record_id='${TENANT_ID}';
SELECT count(*) FROM employment_absence_record;
COMMIT;" | tail -n 1)"
if [[ "${visible}" != "2" ]]; then
  echo "tenant reader could not see own absence anchors: ${visible}" >&2
  exit 1
fi

hidden="$(psql "${DATABASE_URL}" -Atqc "
BEGIN;
SET LOCAL ROLE absence_reader;
SET LOCAL orgmetra.tenant_record_id='${OTHER_TENANT_ID}';
SELECT count(*) FROM employment_absence_record;
COMMIT;" | tail -n 1)"
if [[ "${hidden}" != "0" ]]; then
  echo "foreign tenant could see absence anchors: ${hidden}" >&2
  exit 1
fi

printf '%s\n' "employment absence persistence: PASS"
