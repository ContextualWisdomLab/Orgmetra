#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('10000000-0000-7000-8000-000000000001', 'tenant_alpha');
INSERT INTO person_record (tenant_record_id, person_record_id, recorded_from)
VALUES ('10000000-0000-7000-8000-000000000001', '00000000-0000-7000-8000-000000000101', TIMESTAMPTZ '2026-09-01 00:00:00+00');
INSERT INTO employment_record (tenant_record_id, employment_record_id, person_record_id, recorded_from)
VALUES ('10000000-0000-7000-8000-000000000001', '00000000-0000-7000-8000-000000000111', '00000000-0000-7000-8000-000000000101', TIMESTAMPTZ '2026-09-01 00:00:00+00');
INSERT INTO organization_unit (tenant_record_id, organization_unit_id, recorded_from)
VALUES ('10000000-0000-7000-8000-000000000001', '00000000-0000-7000-8000-000000000121', TIMESTAMPTZ '2026-09-01 00:00:00+00');
INSERT INTO job_profile (tenant_record_id, job_profile_id, recorded_from)
VALUES ('10000000-0000-7000-8000-000000000001', '00000000-0000-7000-8000-000000000131', TIMESTAMPTZ '2026-09-01 00:00:00+00');
INSERT INTO position_record (tenant_record_id, position_record_id, organization_unit_id, job_profile_id, recorded_from)
VALUES
  ('10000000-0000-7000-8000-000000000001', '00000000-0000-7000-8000-000000000141', '00000000-0000-7000-8000-000000000121', '00000000-0000-7000-8000-000000000131', TIMESTAMPTZ '2026-09-01 00:00:00+00'),
  ('10000000-0000-7000-8000-000000000001', '00000000-0000-7000-8000-000000000142', '00000000-0000-7000-8000-000000000121', '00000000-0000-7000-8000-000000000131', TIMESTAMPTZ '2026-09-01 00:00:00+00'),
  ('10000000-0000-7000-8000-000000000001', '00000000-0000-7000-8000-000000000143', '00000000-0000-7000-8000-000000000121', '00000000-0000-7000-8000-000000000131', TIMESTAMPTZ '2026-09-01 00:00:00+00');

-- This row predates the assignment-category contract and must survive without
-- inventing a primary/secondary meaning from allocation or row order.
INSERT INTO assignment_record (
    tenant_record_id, assignment_record_id, employment_record_id, person_record_id,
    position_record_id, allocation_ratio, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001', '00000000-0000-7000-8000-000000000151',
    '00000000-0000-7000-8000-000000000111', '00000000-0000-7000-8000-000000000101',
    '00000000-0000-7000-8000-000000000141', 0.5000, DATE '2026-09-01', TIMESTAMPTZ '2026-09-01 00:01:00+00'
);
SQL

# RED until the forward-only migration exists.
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0017_assignment_category_code.sql

legacy_category="$(psql "${DATABASE_URL}" -Atqc "SELECT assignment_category_code FROM assignment_record WHERE assignment_record_id='00000000-0000-7000-8000-000000000151';")"
test "${legacy_category}" = "legacy_unspecified"

# A pre-contract row is still legitimate system-time history. Closing its
# recorded interval must not force Orgmetra to invent a primary/secondary
# classification merely because PostgreSQL rechecks a NOT VALID constraint on
# UPDATE. This is RED against the current migration.
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "UPDATE assignment_record SET recorded_to=TIMESTAMPTZ '2026-09-01 00:02:00+00' WHERE assignment_record_id='00000000-0000-7000-8000-000000000151';"
legacy_recorded_to="$(psql "${DATABASE_URL}" -Atqc "SELECT recorded_to FROM assignment_record WHERE assignment_record_id='00000000-0000-7000-8000-000000000151';")"
test "${legacy_recorded_to}" = "2026-09-01 00:02:00+00"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO assignment_record (
    tenant_record_id, assignment_record_id, employment_record_id, person_record_id,
    position_record_id, allocation_ratio, assignment_category_code, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001', '00000000-0000-7000-8000-000000000152',
    '00000000-0000-7000-8000-000000000111', '00000000-0000-7000-8000-000000000101',
    '00000000-0000-7000-8000-000000000142', 0.2500, 'primary', DATE '2026-09-01', TIMESTAMPTZ '2026-09-01 00:02:00+00'
);
INSERT INTO assignment_record (
    tenant_record_id, assignment_record_id, employment_record_id, person_record_id,
    position_record_id, allocation_ratio, assignment_category_code, effective_from, recorded_from
) VALUES (
    '10000000-0000-7000-8000-000000000001', '00000000-0000-7000-8000-000000000153',
    '00000000-0000-7000-8000-000000000111', '00000000-0000-7000-8000-000000000101',
    '00000000-0000-7000-8000-000000000143', 0.2500, 'concurrent_secondary', DATE '2026-09-01', TIMESTAMPTZ '2026-09-01 00:02:00+00'
);
SQL

set +e
missing_output="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "INSERT INTO assignment_record (tenant_record_id, assignment_record_id, employment_record_id, person_record_id, position_record_id, allocation_ratio, effective_from, recorded_from) VALUES ('10000000-0000-7000-8000-000000000001','00000000-0000-7000-8000-000000000154','00000000-0000-7000-8000-000000000111','00000000-0000-7000-8000-000000000101','00000000-0000-7000-8000-000000000143',0.1000,DATE '2026-09-02',TIMESTAMPTZ '2026-09-02 00:00:00+00');" 2>&1)"
missing_status=$?
set -e
if [[ ${missing_status} -eq 0 || "${missing_output}" != *"not-null constraint"* ]]; then
  echo "new assignment without category did not fail closed: ${missing_output}" >&2
  exit 1
fi

# legacy_unspecified is a migration sentinel for pre-contract rows, not a legal
# value for a newly inserted assignment. The persistence boundary must enforce
# that distinction even if a caller bypasses the People command model.
set +e
legacy_write_output="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "INSERT INTO assignment_record (tenant_record_id, assignment_record_id, employment_record_id, person_record_id, position_record_id, allocation_ratio, assignment_category_code, effective_from, recorded_from) VALUES ('10000000-0000-7000-8000-000000000001','00000000-0000-7000-8000-000000000155','00000000-0000-7000-8000-000000000111','00000000-0000-7000-8000-000000000101','00000000-0000-7000-8000-000000000143',0.1000,'legacy_unspecified',DATE '2026-09-02',TIMESTAMPTZ '2026-09-02 00:01:00+00');" 2>&1)"
legacy_write_status=$?
set -e
if [[ ${legacy_write_status} -eq 0 || "${legacy_write_output}" != *"assignment_record_category_code_check"* ]]; then
  echo "new legacy_unspecified assignment did not fail closed: ${legacy_write_output}" >&2
  exit 1
fi

set +e
duplicate_output="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "INSERT INTO assignment_record (tenant_record_id, assignment_record_id, employment_record_id, person_record_id, position_record_id, allocation_ratio, assignment_category_code, effective_from, recorded_from) VALUES ('10000000-0000-7000-8000-000000000001','00000000-0000-7000-8000-000000000156','00000000-0000-7000-8000-000000000111','00000000-0000-7000-8000-000000000101','00000000-0000-7000-8000-000000000143',0.1000,'primary',DATE '2026-09-01',TIMESTAMPTZ '2026-09-01 00:03:00+00');" 2>&1)"
duplicate_status=$?
set -e
if [[ ${duplicate_status} -eq 0 || "${duplicate_output}" != *"assignment_record_primary_bitemporal_exclusion"* ]]; then
  echo "overlapping second primary did not fail closed: ${duplicate_output}" >&2
  exit 1
fi

echo "assignment category PostgreSQL contract passed"
