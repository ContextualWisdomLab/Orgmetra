#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"

TENANT_ID="10000000-0000-7000-8000-000000000001"
JOB_ID="00000000-0000-7000-8000-0000000000a1"
CRITERION_ID="00000000-0000-7000-8000-0000000000b1"
STUDY_ID="00000000-0000-7000-8000-0000000000c1"

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f database/migrations/0001_foundation_schema.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f services/workforce-validation-api/database/migrations/0001_owner_schema.sql

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<SQL
INSERT INTO tenant_record (tenant_record_id, tenant_reference)
VALUES ('${TENANT_ID}', 'tenant_alpha');
INSERT INTO job_profile (tenant_record_id, job_profile_id)
VALUES ('${TENANT_ID}', '${JOB_ID}');
INSERT INTO criterion_blueprint (
    tenant_record_id,
    criterion_blueprint_id,
    job_profile_id,
    criterion_type_code,
    criterion_version_code,
    effective_from
) VALUES (
    '${TENANT_ID}',
    '${CRITERION_ID}',
    '${JOB_ID}',
    'job_performance',
    'criterion-v1',
    DATE '2026-07-01'
);
INSERT INTO validity_study (
    tenant_record_id,
    validity_study_id,
    criterion_blueprint_id,
    study_status_code,
    recorded_from
) VALUES (
    '${TENANT_ID}',
    '${STUDY_ID}',
    '${CRITERION_ID}',
    'active',
    TIMESTAMPTZ '2026-07-01 00:00:00+00'
);
SQL

legacy_oid="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "SELECT 'public.validity_study'::regclass::oid;")"
legacy_fk_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*) FROM pg_constraint WHERE contype = 'f' AND confrelid = ${legacy_oid};
")"
if [[ "${legacy_fk_count}" != "3" ]]; then
    echo "unexpected foundation FK dependency count before adoption: ${legacy_fk_count}" >&2
    exit 1
fi

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f services/workforce-validation-api/database/migrations/0002_registry_adoption.sql

if [[ "$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "SELECT to_regclass('public.validity_study') IS NULL;")" != "t" ]]; then
    echo "legacy public.validity_study relation still exists after owner adoption" >&2
    exit 1
fi

owner_oid="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "SELECT 'workforce_validation.validity_study'::regclass::oid;")"
if [[ "${owner_oid}" != "${legacy_oid}" ]]; then
    echo "registry adoption copied/recreated the table instead of preserving relation identity" >&2
    exit 1
fi

owner_name="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT pg_get_userbyid(relowner)
FROM pg_class
WHERE oid = ${owner_oid};
")"
if [[ "${owner_name}" != "workforce_validation_role" ]]; then
    echo "registry table has unexpected owner: ${owner_name}" >&2
    exit 1
fi

owner_fk_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*) FROM pg_constraint WHERE contype = 'f' AND confrelid = ${owner_oid};
")"
if [[ "${owner_fk_count}" != "${legacy_fk_count}" ]]; then
    echo "registry adoption broke existing FK dependencies: before=${legacy_fk_count} after=${owner_fk_count}" >&2
    exit 1
fi

rls_flags="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT relrowsecurity, relforcerowsecurity
FROM pg_class
WHERE oid = ${owner_oid};
")"
if [[ "${rls_flags}" != "t|t" ]]; then
    echo "registry adoption did not preserve forced tenant RLS: ${rls_flags}" >&2
    exit 1
fi

bitemporal_trigger="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT count(*)
FROM pg_trigger
WHERE tgrelid = ${owner_oid}
  AND tgname = 'validity_study_bitemporal_guard'
  AND NOT tgisinternal;
")"
if [[ "${bitemporal_trigger}" != "1" ]]; then
    echo "registry adoption lost the bitemporal mutation guard" >&2
    exit 1
fi

runtime_flags="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolinherit, rolreplication, rolbypassrls
FROM pg_roles
WHERE rolname = 'workforce_validation_runtime_role';
")"
if [[ "${runtime_flags}" != "f|f|f|f|f|f|f" ]]; then
    echo "workforce_validation_runtime_role flags are not deny-default: ${runtime_flags}" >&2
    exit 1
fi

runtime_privileges="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SELECT
  has_schema_privilege('workforce_validation_runtime_role', 'workforce_validation', 'USAGE'),
  has_schema_privilege('workforce_validation_runtime_role', 'workforce_validation', 'CREATE'),
  has_table_privilege('workforce_validation_runtime_role', 'workforce_validation.validity_study', 'SELECT'),
  has_table_privilege('workforce_validation_runtime_role', 'workforce_validation.validity_study', 'INSERT'),
  has_table_privilege('workforce_validation_runtime_role', 'workforce_validation.validity_study', 'UPDATE'),
  has_table_privilege('workforce_validation_runtime_role', 'workforce_validation.validity_study', 'DELETE'),
  has_table_privilege('workforce_validation_runtime_role', 'workforce_validation.validity_study', 'TRUNCATE');
")"
if [[ "${runtime_privileges}" != "t|f|t|f|f|f|f" ]]; then
    echo "runtime role privileges are not least-privilege read-only: ${runtime_privileges}" >&2
    exit 1
fi

missing_tenant_count="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SET ROLE workforce_validation_runtime_role;
SELECT count(*) FROM workforce_validation.validity_study;
RESET ROLE;
")"
if [[ "${missing_tenant_count}" != "0" ]]; then
    echo "runtime read returned rows without tenant context: ${missing_tenant_count}" >&2
    exit 1
fi

tenant_read="$(psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -Atqc "
SET orgmetra.tenant_record_id = '${TENANT_ID}';
SET ROLE workforce_validation_runtime_role;
SELECT validity_study_id::text FROM workforce_validation.validity_study;
RESET ROLE;
RESET orgmetra.tenant_record_id;
")"
if [[ "${tenant_read}" != "${STUDY_ID}" ]]; then
    echo "runtime role did not read the tenant-scoped owner registry: ${tenant_read}" >&2
    exit 1
fi
