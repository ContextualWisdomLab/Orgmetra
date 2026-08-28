#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0002_sealed_evidence_digest.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0040_employment_employing_organization.sql

index_definition="$(psql "${DATABASE_URL}" -Atqc "SELECT indexdef FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'employment_employing_organization_record' AND indexname = 'employment_employing_organization_unit_lookup_index';")"
[[ -n "${index_definition}" ]] || {
  echo "missing employment_employing_organization_unit_lookup_index" >&2
  exit 1
}
[[ "${index_definition}" == *"(tenant_record_id, employing_organization_unit_id)"* ]] || {
  echo "employment_employing_organization_unit_lookup_index does not cover tenant_record_id and employing_organization_unit_id: ${index_definition}" >&2
  exit 1
}

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;
INSERT INTO tenant_record (tenant_record_id, tenant_reference) VALUES
 ('10000000-0000-7000-8000-000000000001','tenant_alpha'),
 ('20000000-0000-7000-8000-000000000001','tenant_beta');
INSERT INTO person_record (tenant_record_id, person_record_id) VALUES
 ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000010'),
 ('20000000-0000-7000-8000-000000000001','20000000-0000-7000-8000-000000000010');
INSERT INTO employment_record (tenant_record_id, employment_record_id, person_record_id) VALUES
 ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000020','10000000-0000-7000-8000-000000000010'),
 ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000022','10000000-0000-7000-8000-000000000010'),
 ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000026','10000000-0000-7000-8000-000000000010'),
 ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000028','10000000-0000-7000-8000-000000000010'),
 ('20000000-0000-7000-8000-000000000001','20000000-0000-7000-8000-000000000020','20000000-0000-7000-8000-000000000010');
INSERT INTO employment_record_version (
 tenant_record_id, employment_record_version_id, employment_record_id,
 employment_status_code, employment_concurrency_code, effective_from, recorded_from
) VALUES
 ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000021','10000000-0000-7000-8000-000000000020','active','exclusive',DATE '2026-01-01',TIMESTAMPTZ '2026-01-02 00:00:00+00'),
 ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000023','10000000-0000-7000-8000-000000000022','active','concurrent',DATE '2026-01-01',TIMESTAMPTZ '2026-01-02 00:00:00+00'),
 ('20000000-0000-7000-8000-000000000001','20000000-0000-7000-8000-000000000021','20000000-0000-7000-8000-000000000020','active','exclusive',DATE '2026-01-01',TIMESTAMPTZ '2026-01-02 00:00:00+00');
INSERT INTO organization_unit (tenant_record_id, organization_unit_id) VALUES
 ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000030'),
 ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000031'),
 ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000032'),
 ('20000000-0000-7000-8000-000000000001','20000000-0000-7000-8000-000000000030');
INSERT INTO organization_unit_version (
 tenant_record_id, organization_unit_version_id, organization_unit_id,
 unit_name, organization_type_code, effective_from, recorded_from
) VALUES
 ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000040','10000000-0000-7000-8000-000000000030','Alpha Legal Employer','legal_entity',DATE '2025-01-01',TIMESTAMPTZ '2026-01-02 00:00:00+00'),
 ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000041','10000000-0000-7000-8000-000000000031','Alpha Second Employer','legal_entity',DATE '2025-01-01',TIMESTAMPTZ '2026-01-02 00:00:00+00'),
 ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000042','10000000-0000-7000-8000-000000000032','People Department','department',DATE '2025-01-01',TIMESTAMPTZ '2026-01-02 00:00:00+00'),
 ('20000000-0000-7000-8000-000000000001','20000000-0000-7000-8000-000000000040','20000000-0000-7000-8000-000000000030','Beta Legal Employer','legal_entity',DATE '2025-01-01',TIMESTAMPTZ '2026-01-02 00:00:00+00');
INSERT INTO employment_employing_organization_record (
 tenant_record_id, employment_employing_organization_record_id,
 employment_record_id, employing_organization_unit_id, effective_from, recorded_from
) VALUES
 ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000050',
  '10000000-0000-7000-8000-000000000020','10000000-0000-7000-8000-000000000030',
  DATE '2026-01-01',TIMESTAMPTZ '2026-01-02 00:00:00+00'),
 ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000051',
  '10000000-0000-7000-8000-000000000022','10000000-0000-7000-8000-000000000031',
  DATE '2026-01-01',TIMESTAMPTZ '2026-01-02 00:00:00+00'),
 ('20000000-0000-7000-8000-000000000001','20000000-0000-7000-8000-000000000050',
  '20000000-0000-7000-8000-000000000020','20000000-0000-7000-8000-000000000030',
  DATE '2026-01-01',TIMESTAMPTZ '2026-01-02 00:00:00+00');
COMMIT;
SQL

count="$(psql "${DATABASE_URL}" -Atqc "SELECT count(*) FROM employment_employing_organization_record WHERE tenant_record_id='10000000-0000-7000-8000-000000000001'::uuid AND employment_record_id='10000000-0000-7000-8000-000000000020'::uuid AND daterange(effective_from,effective_to,'[)') @> DATE '2026-08-28' AND tstzrange(recorded_from,recorded_to,'[)') @> TIMESTAMPTZ '2026-08-28 00:00:00+00';")"
[[ "$count" == 1 ]] || { echo "expected one employer at one business/system coordinate, got $count" >&2; exit 1; }

expect_failure() {
 local expected="$1"; shift
 set +e
 local output
 output="$({ "$@"; } 2>&1)"
 local status=$?
 set -e
 [[ $status -ne 0 && "$output" == *"$expected"* ]] || { echo "expected failure '$expected', got: $output" >&2; exit 1; }
}

expect_failure employment_employing_organization_bitemporal_exclusion psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "INSERT INTO employment_employing_organization_record (tenant_record_id,employment_employing_organization_record_id,employment_record_id,employing_organization_unit_id,effective_from,recorded_from) VALUES ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000058','10000000-0000-7000-8000-000000000020','10000000-0000-7000-8000-000000000031',DATE '2026-06-01',TIMESTAMPTZ '2026-01-04 00:00:00+00');"
expect_failure "employing organization must be a legal_entity" psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "INSERT INTO employment_employing_organization_record (tenant_record_id,employment_employing_organization_record_id,employment_record_id,employing_organization_unit_id,effective_from,effective_to,recorded_from) VALUES ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000059','10000000-0000-7000-8000-000000000020','10000000-0000-7000-8000-000000000032',DATE '2026-01-01',DATE '2026-06-01',TIMESTAMPTZ '2026-01-03 00:00:00+00');"
expect_failure "employing organization interval must be covered by active or leave Employment truth" psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "INSERT INTO employment_employing_organization_record (tenant_record_id,employment_employing_organization_record_id,employment_record_id,employing_organization_unit_id,effective_from,effective_to,recorded_from) VALUES ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000055','10000000-0000-7000-8000-000000000020','10000000-0000-7000-8000-000000000030',DATE '2025-01-01',DATE '2025-06-01',TIMESTAMPTZ '2026-01-03 00:00:00+00');"
# Separate Employment anchors prevent the cardinality exclusion from masking the tenant FK boundary.
expect_failure employment_employing_organization_unit_tenant_fk psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "INSERT INTO employment_employing_organization_record (tenant_record_id,employment_employing_organization_record_id,employment_record_id,employing_organization_unit_id,effective_from,recorded_from) VALUES ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000053','10000000-0000-7000-8000-000000000026','20000000-0000-7000-8000-000000000030',DATE '2026-01-01',TIMESTAMPTZ '2026-01-03 00:00:00+00');"
expect_failure "exactly one legal employer" psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "BEGIN; INSERT INTO employment_record_version (tenant_record_id,employment_record_version_id,employment_record_id,employment_status_code,effective_from,recorded_from) VALUES ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000027','10000000-0000-7000-8000-000000000026','active',DATE '2026-01-01',TIMESTAMPTZ '2026-01-03 00:00:00+00'); COMMIT;"
expect_failure "exactly one legal employer" psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "BEGIN; INSERT INTO employment_record_version (tenant_record_id,employment_record_version_id,employment_record_id,employment_status_code,effective_from,effective_to,recorded_from) VALUES ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000029','10000000-0000-7000-8000-000000000028','active',DATE '2026-01-01',DATE '2026-12-31',TIMESTAMPTZ '2026-01-03 00:00:00+00'); INSERT INTO employment_employing_organization_record (tenant_record_id,employment_employing_organization_record_id,employment_record_id,employing_organization_unit_id,effective_from,effective_to,recorded_from) VALUES ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000060','10000000-0000-7000-8000-000000000028','10000000-0000-7000-8000-000000000030',DATE '2026-01-01',DATE '2026-06-01',TIMESTAMPTZ '2026-01-03 00:00:00+00'), ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000061','10000000-0000-7000-8000-000000000028','10000000-0000-7000-8000-000000000030',DATE '2026-07-01',DATE '2026-12-31',TIMESTAMPTZ '2026-01-03 00:00:00+00'); COMMIT;"
expect_failure "bitemporal correction may only close an open recorded interval" psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "UPDATE employment_employing_organization_record SET employing_organization_unit_id='10000000-0000-7000-8000-000000000031' WHERE employment_employing_organization_record_id='10000000-0000-7000-8000-000000000050';"
expect_failure "employment employing-organization history cannot be truncated" psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "TRUNCATE employment_employing_organization_record;"

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;
UPDATE employment_employing_organization_record SET recorded_to=TIMESTAMPTZ '2026-09-01 00:00:00+00' WHERE employment_employing_organization_record_id='10000000-0000-7000-8000-000000000050';
INSERT INTO employment_employing_organization_record (tenant_record_id,employment_employing_organization_record_id,employment_record_id,employing_organization_unit_id,effective_from,recorded_from) VALUES ('10000000-0000-7000-8000-000000000001','10000000-0000-7000-8000-000000000054','10000000-0000-7000-8000-000000000020','10000000-0000-7000-8000-000000000031',DATE '2026-01-01',TIMESTAMPTZ '2026-09-01 00:00:00+00');
COMMIT;
CREATE ROLE orgmetra_employer_reader NOSUPERUSER NOBYPASSRLS;
GRANT SELECT ON employment_employing_organization_record TO orgmetra_employer_reader;
SET ROLE orgmetra_employer_reader;
SELECT set_config('orgmetra.tenant_record_id','10000000-0000-7000-8000-000000000001',false);
DO $$ BEGIN
 IF (SELECT count(*) FROM employment_employing_organization_record WHERE employment_record_id='10000000-0000-7000-8000-000000000020'::uuid AND tstzrange(recorded_from, recorded_to, '[)') @> TIMESTAMPTZ '2026-09-01 00:00:00+00') <> 1 THEN
   RAISE EXCEPTION 'tenant alpha should see exactly one employer fact at the selected system-time coordinate';
 END IF;
 IF (SELECT count(*) FROM employment_employing_organization_record WHERE employment_record_id='20000000-0000-7000-8000-000000000020'::uuid) <> 0 THEN
   RAISE EXCEPTION 'tenant alpha must not see tenant beta employer facts';
 END IF;
END $$;
SELECT set_config('orgmetra.tenant_record_id','20000000-0000-7000-8000-000000000001',false);
DO $$ BEGIN
 IF (SELECT count(*) FROM employment_employing_organization_record WHERE employment_record_id='20000000-0000-7000-8000-000000000020'::uuid AND tstzrange(recorded_from, recorded_to, '[)') @> TIMESTAMPTZ '2026-09-01 00:00:00+00') <> 1 THEN
   RAISE EXCEPTION 'tenant beta should see exactly one employer fact at the selected system-time coordinate';
 END IF;
 IF (SELECT count(*) FROM employment_employing_organization_record WHERE employment_record_id='10000000-0000-7000-8000-000000000020'::uuid) <> 0 THEN
   RAISE EXCEPTION 'tenant beta must not see tenant alpha employer facts';
 END IF;
END $$;
RESET ROLE;
SQL

echo "Employment employing-organization PostgreSQL contract passed"
